# -*- coding: utf-8 -*-
from fastapi import FastAPI, Depends, HTTPException, Query
from typing import List
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
import models
import schemas
from database import SessionLocal, engine
import os
from engine import process_workflow
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from postgrest import SyncPostgrestClient
from supabase_auth import SyncGoTrueClient

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
SUPABASE_DB_URL = os.environ.get("SUPABASE_DB_URL", "")

# Fallback intelligent
if not SUPABASE_URL and "@db." in SUPABASE_DB_URL:
    try:
        project_id = SUPABASE_DB_URL.split("@db.")[1].split(".")[0]
        SUPABASE_URL = f"https://{project_id}.supabase.co"
    except: pass

print(f"[DEBUG BACKEND] URL chargée: {SUPABASE_URL}")

if not SUPABASE_KEY:
    print("[CRITICAL] SUPABASE_KEY manquante dans le .env !")

auth_client = SyncGoTrueClient(
    url=f"{SUPABASE_URL}/auth/v1", 
    headers={"apiKey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
) if SUPABASE_URL and SUPABASE_KEY else None

db_client = SyncPostgrestClient(
    f"{SUPABASE_URL}/rest/v1", 
    headers={"apiKey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
) if SUPABASE_URL and SUPABASE_KEY else None

security = HTTPBearer()

def get_user_from_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token: str = credentials.credentials
    if not auth_client:
        raise HTTPException(status_code=500, detail="Supabase client not configured")
    try:
        user_response = auth_client.get_user(token)
        if not user_response or not getattr(user_response, "user", None):
            raise HTTPException(status_code=401, detail="Unauthorized")
        return getattr(user_response, "user", None)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Unauthorized")

# Création des tables au démarrage
models.Base.metadata.create_all(bind=engine)
print("[SGBD] Connexion à Supabase établie et schéma synchronisé")

# Initialisation des classifications par défaut
def init_data():
    db = SessionLocal()
    try:
        if db.query(models.TaskClassification).count() == 0:
            db.add(models.TaskClassification(name="Incidents"))
            db.add(models.TaskClassification(name="Demandes"))
            db.commit()
    finally:
        db.close()

init_data()

app = FastAPI(
    title="LiteFlow Pro API",
    dependencies=[Depends(get_user_from_token)]
)

# Dépendance DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------------------------------------------------------------
# ROUTES DES TÂCHES (TICKETS)
# -----------------------------------------------------------------------------

@app.get("/tasks/", response_model=List[schemas.Task])
def read_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    tasks = db.query(models.Task).options(joinedload(models.Task.classification)).offset(skip).limit(limit).all()
    for t in tasks:
        t.classification_name = t.classification.name if t.classification else None
    return tasks

@app.post("/tasks/")
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
    db_task = models.Task(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Déclenchement automatique du workflow après création
    process_workflow(db_task.id, db)
    
    return db_task

@app.put("/tasks/{task_id}")
def update_task(
    task_id: int, 
    task_update: schemas.TaskUpdate, 
    skip_workflow: bool = False, 
    is_admin: bool = False,
    db: Session = Depends(get_db)
):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    old_status = db_task.status
    update_data = task_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_task, key, value)

    # --- LOGIQUE DE PROPAGATION "TERMINÉ" (SOLID) ---
    if db_task.status == "Terminé" and old_status != "Terminé":
        import datetime
        db_task.closed_at = datetime.datetime.utcnow()
        children = db.query(models.Task).filter(models.Task.parent_id == task_id).all()
        for child in children:
            child.status = "Terminé"
            child.closed_at = db_task.closed_at
            # Log de propagation
            log = models.AuditLog(message=f"[SYSTEME] Clôture auto (Parent #{task_id} terminé) pour l'enfant #{child.id}")
            db.add(log)
    elif db_task.status != "Terminé" and old_status == "Terminé":
        db_task.closed_at = None

    db.commit()
    db.refresh(db_task)

    return db_task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        return {"message": "Success (idempotent)"}
    
    db.delete(db_task)
    db.commit()
    return {"message": "Task deleted"}

# -----------------------------------------------------------------------------
# ROUTES DE FONDATION (GROUPES)
# -----------------------------------------------------------------------------

@app.get("/groups/", response_model=List[schemas.SupportGroup])
def read_groups(db: Session = Depends(get_db)):
    return db.query(models.SupportGroup).options(joinedload(models.SupportGroup.classifications)).order_by(models.SupportGroup.name).all()

@app.post("/groups/", response_model=schemas.SupportGroup)
def create_group(group: schemas.GroupCreate, db: Session = Depends(get_db)):
    if not group.classification_ids:
        raise HTTPException(status_code=400, detail="Un groupe doit avoir au moins une nature")
    
    db_group = models.SupportGroup(name=group.name)
    
    # Attachement immédiat des classifications
    classifs = db.query(models.TaskClassification).filter(models.TaskClassification.id.in_(group.classification_ids)).all()
    if len(classifs) != len(group.classification_ids):
        raise HTTPException(status_code=400, detail="Certaines classifications sont invalides")
        
    db_group.classifications = classifs
    db.add(db_group)
    try:
        db.commit()
    except:
        db.rollback()
        raise HTTPException(status_code=400, detail="Group already exists or invalid data")
    
    db.refresh(db_group)
    return db_group

@app.put("/groups/{group_id}", response_model=schemas.SupportGroup)
def update_group(group_id: int, group_update: schemas.GroupUpdate, db: Session = Depends(get_db)):
    db_group = db.query(models.SupportGroup).filter(models.SupportGroup.id == group_id).first()
    if not db_group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if group_update.name is not None:
        db_group.name = group_update.name
    
    if group_update.classification_ids is not None:
        if not group_update.classification_ids:
            raise HTTPException(status_code=400, detail="Un groupe doit posséder au moins une nature.")
            
        classifs = db.query(models.TaskClassification).filter(models.TaskClassification.id.in_(group_update.classification_ids)).all()
        if len(classifs) != len(group_update.classification_ids):
            raise HTTPException(status_code=400, detail="Certaines classifications sont invalides")
        db_group.classifications = classifs
    
    db.commit()
    db.refresh(db_group)
    return db_group

@app.delete("/groups/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db)):
    db_group = db.query(models.SupportGroup).filter(models.SupportGroup.id == group_id).first()
    if db_group:
        db.delete(db_group)
        db.commit()
    return {"message": "Group deleted"}

# -----------------------------------------------------------------------------
# ROUTES DES CLASSIFICATIONS
# -----------------------------------------------------------------------------

@app.get("/classifications/")
def read_classifications(db: Session = Depends(get_db)):
    return db.query(models.TaskClassification).all()

@app.post("/classifications/")
def create_classification(classif: schemas.ClassificationCreate, db: Session = Depends(get_db)):
    db_classif = models.TaskClassification(**classif.model_dump())
    db.add(db_classif)
    db.commit()
    db.refresh(db_classif)
    return db_classif

@app.put("/classifications/{classif_id}")
def update_classification(classif_id: int, classif_update: schemas.ClassificationUpdate, db: Session = Depends(get_db)):
    db_classif = db.query(models.TaskClassification).filter(models.TaskClassification.id == classif_id).first()
    if not db_classif:
        raise HTTPException(status_code=404, detail="Classification not found")
    
    if classif_update.name is not None:
        # Check for duplicate names
        dup = db.query(models.TaskClassification).filter(
            models.TaskClassification.name == classif_update.name,
            models.TaskClassification.id != classif_id
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail="Ce nom de nature existe déjà.")
        
        db_classif.name = classif_update.name
    
    db.commit()
    db.refresh(db_classif)
    print(f"[API] Nature ID {classif_id} renommée en {db_classif.name}")
    return db_classif

@app.delete("/classifications/{classif_id}")
def delete_classification(classif_id: int, db: Session = Depends(get_db)):
    db_classif = db.query(models.TaskClassification).filter(models.TaskClassification.id == classif_id).first()
    if not db_classif:
        return {"message": "Success (idempotent)"}
    
    # Check for linked tasks
    linked_tasks = db.query(models.Task).filter(models.Task.classification_id == classif_id).count()
    if linked_tasks > 0:
        raise HTTPException(
            status_code=400, 
            detail="Incapable de supprimer : des tickets sont encore liés à cette nature."
        )
    
    db.delete(db_classif)
    db.commit()
    return {"message": "Classification deleted"}

# -----------------------------------------------------------------------------
# ROUTES DES ASSETS (CMDB)
# -----------------------------------------------------------------------------

@app.get("/assets/", response_model=list[schemas.Asset])
def read_assets(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Asset).offset(skip).limit(limit).all()

@app.post("/assets/", response_model=schemas.Asset)
def create_asset(asset: schemas.AssetCreate, db: Session = Depends(get_db)):
    db_asset = models.Asset(**asset.model_dump())
    db.add(db_asset)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Serial number already exists")
    db.refresh(db_asset)
    return db_asset

@app.delete("/assets/{asset_id}")
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    db_asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
    if not db_asset:
        return {"message": "Success (idempotent)"}
    db.delete(db_asset)
    db.commit()
    return {"message": "Asset deleted"}

# -----------------------------------------------------------------------------
# ROUTES ADMIN & MAINTENANCE (INDISPENSABLES POUR L'ONGLET ADMIN TOOLS)
# -----------------------------------------------------------------------------

@app.get("/audit/logs")
def get_logs(limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.AuditLog).order_by(models.AuditLog.id.desc()).limit(limit).all()

@app.post("/audit/logs")
def create_manual_log(log: schemas.AuditLogCreate, db: Session = Depends(get_db)):
    """Permet à l'interface d'enregistrer des actions manuelles (ex: suppression)."""
    import models
    db_log = models.AuditLog(message=log.message)
    db.add(db_log)
    db.commit()
    return {"status": "ok"}

# -----------------------------------------------------------------------------
# ROUTES DES UTILISATEURS
# -----------------------------------------------------------------------------

def generate_user_code(db: Session):
    last_user = db.query(models.User).order_by(models.User.user_code.desc()).first()
    if not last_user:
        return "A001"
    
    code = last_user.user_code
    letter = code[0]
    try:
        num = int(code[1:])
    except:
        num = 0
    
    if num >= 999:
        new_letter = chr(ord(letter) + 1) if letter != 'Z' else 'A'
        new_num = 1
    else:
        new_letter = letter
        new_num = num + 1
        
    return f"{new_letter}{new_num:03d}"

@app.get("/users/", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.User).options(
        joinedload(models.User.groups),
        joinedload(models.User.location)
    ).offset(skip).limit(limit).all()

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = models.User(
        user_code=generate_user_code(db),
        first_name=user.first_name,
        last_name=user.last_name,
        location_id=user.location_id
    )
    if user.group_ids:
        groups = db.query(models.SupportGroup).filter(models.SupportGroup.id.in_(user.group_ids)).all()
        db_user.groups = groups
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).options(
        joinedload(models.User.groups),
        joinedload(models.User.location)
    ).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.put("/users/{user_id}", response_model=schemas.User)
def update_user(user_id: int, user_update: schemas.UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_update.model_dump(exclude_unset=True)
    if "group_ids" in update_data:
        group_ids = update_data.pop("group_ids")
        groups = db.query(models.SupportGroup).filter(models.SupportGroup.id.in_(group_ids)).all()
        db_user.groups = groups
    
    if "location_id" in update_data:
        db_user.location_id = update_data.pop("location_id")
    
    for key, value in update_data.items():
        setattr(db_user, key, value)
        
    db.commit()
    db.refresh(db_user)
    return db_user

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return {"status": "ok"}

@app.get("/backup")
def get_backup():
    import os
    from fastapi.responses import FileResponse
    if os.path.exists("workflow.db"):
        return FileResponse("workflow.db", filename="liteflow_backup.db")
    raise HTTPException(status_code=404)

# -----------------------------------------------------------------------------
# ROUTES DES LOCALISATIONS
# -----------------------------------------------------------------------------

@app.get("/locations/", response_model=List[schemas.Location])
def read_locations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Location).options(joinedload(models.Location.users)).offset(skip).limit(limit).all()

@app.post("/locations/", response_model=schemas.Location)
def create_location(location: schemas.LocationCreate, db: Session = Depends(get_db)):
    db_loc = models.Location(**location.model_dump())
    db.add(db_loc)
    try:
        db.commit()
    except:
        db.rollback()
        raise HTTPException(status_code=400, detail="Location name already exists")
    db.refresh(db_loc)
    return db_loc

@app.put("/locations/{location_id}", response_model=schemas.Location)
def update_location(location_id: int, loc_update: schemas.LocationUpdate, db: Session = Depends(get_db)):
    db_loc = db.query(models.Location).filter(models.Location.id == location_id).first()
    if not db_loc:
        raise HTTPException(status_code=404, detail="Location not found")
    
    update_data = loc_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_loc, key, value)
    
    try:
        db.commit()
    except:
        db.rollback()
        raise HTTPException(status_code=400, detail="Name already exists or invalid data")
        
    db.refresh(db_loc)
    return db_loc

@app.delete("/locations/{location_id}")
def delete_location(location_id: int, db: Session = Depends(get_db)):
    db_loc = db.query(models.Location).filter(models.Location.id == location_id).first()
    if not db_loc:
        return {"status": "ok (idempotent)"}
        
    # Detach users from this location before deleting it
    for user in db_loc.users:
        user.location_id = None
        
    db.delete(db_loc)
    db.commit()
    return {"status": "deleted"}