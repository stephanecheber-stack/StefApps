# -*- coding: utf-8 -*-
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import models
import schemas
from database import SessionLocal, engine
import os
from engine import process_workflow

# Création des tables au démarrage
models.Base.metadata.create_all(bind=engine)

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

@app.get("/tasks/")
def read_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Task).offset(skip).limit(limit).all()

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
        children = db.query(models.Task).filter(models.Task.parent_id == task_id).all()
        for child in children:
            child.status = "Terminé"
            # Log de propagation
            log = models.AuditLog(message=f"[SYSTEME] Clôture auto (Parent #{task_id} terminé) pour l'enfant #{child.id}")
            db.add(log)

    db.commit()
    db.refresh(db_task)

    # Déclenchement du workflow (sauf si forcé par l'admin)
    if not skip_workflow:
        process_workflow(db_task.id, db)

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

@app.get("/groups/")
def read_groups(db: Session = Depends(get_db)):
    return db.query(models.SupportGroup).order_by(models.SupportGroup.name).all()

@app.post("/groups/")
def create_group(group: schemas.GroupCreate, db: Session = Depends(get_db)):
    db_group = models.SupportGroup(name=group.name)
    db.add(db_group)
    try:
        db.commit()
    except:
        raise HTTPException(status_code=400, detail="Group already exists")
    return db_group

@app.delete("/groups/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db)):
    db_group = db.query(models.SupportGroup).filter(models.SupportGroup.id == group_id).first()
    if db_group:
        db.delete(db_group)
        db.commit()
    return {"message": "Group deleted"}

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
def get_audit_logs(limit: int = 100, db: Session = Depends(get_db)):
    """Récupère les derniers journaux d'audit."""
    return db.query(models.AuditLog).order_by(models.AuditLog.id.desc()).limit(limit).all()

@app.post("/audit/logs")
def create_audit_log(log_entry: schemas.AuditLogCreate, db: Session = Depends(get_db)):
    """Permet au Frontend d'écrire manuellement dans l'audit."""
    db_log = models.AuditLog(message=log_entry.message)
    db.add(db_log)
    db.commit()
    return db_log

@app.get("/backup")
def get_db_backup():
    """Renvoie le fichier SQLite pour téléchargement."""
    db_path = "workflow.db"
    if os.path.exists(db_path):
        return FileResponse(
            path=db_path, 
            filename=f"liteflow_prod_backup.db", 
            media_type='application/x-sqlite3'
        )
    raise HTTPException(status_code=404, detail="Database file not found")