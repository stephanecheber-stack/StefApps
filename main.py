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

# Création des tables au démarrage
models.Base.metadata.create_all(bind=engine)

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

app = FastAPI(title="LiteFlow Pro API")

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
    return db.query(models.SupportGroup).order_by(models.SupportGroup.name).all()

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

@app.get("/backup")
def get_backup():
    import os
    from fastapi.responses import FileResponse
    if os.path.exists("workflow.db"):
        return FileResponse("workflow.db", filename="liteflow_backup.db")
    raise HTTPException(status_code=404)