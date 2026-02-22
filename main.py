from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
import models
from database import SessionLocal, engine, init_db
from engine import process_workflow, cascade_completion
import os
from datetime import datetime
import shutil

# Initialize database (create tables)
init_db()

app = FastAPI(title="LiteFlow API", description="Backend for LiteFlow Task Manager")

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydantic Models ---

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "Moyenne"
    status: models.TaskStatus = models.TaskStatus.NOUVEAU
    tags: Optional[str] = None
    assigned_to: Optional[str] = None
    parent_id: Optional[int] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[models.TaskStatus] = None
    priority: Optional[str] = None
    tags: Optional[str] = None
    assigned_to: Optional[str] = None
    parent_id: Optional[int] = None

class Task(TaskBase):
    id: int
    status: str
    
    # Configuration for Pydantic V2 to work with ORM objects
    model_config = ConfigDict(from_attributes=True)

class AuditLog(BaseModel):
    id: int
    task_id: Optional[int] = None
    message: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class AuditLogCreate(BaseModel):
    message: str
    task_id: Optional[int] = None

class GroupCreate(BaseModel):
    name: str

class GroupResponse(BaseModel):
    id: int
    name: str
    
    model_config = ConfigDict(from_attributes=True)

# --- Endpoints ---

@app.post("/audit/logs", response_model=AuditLog)
def create_audit_log(log: AuditLogCreate, db: Session = Depends(get_db)):
    """
    Create a generic audit log entry.
    """
    db_log = models.AuditLog(
        task_id=log.task_id,
        message=log.message
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

@app.get("/audit/logs", response_model=List[AuditLog])
def read_all_audit_logs(db: Session = Depends(get_db)):
    """
    Get all audit logs from the system.
    """
    return db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).all()

@app.post("/tasks/", response_model=Task)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """
    Create a new task and trigger the workflow engine.
    """
    db_task = models.Task(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Process Workflow Rules
    process_workflow(db_task.id, db)
    db.refresh(db_task) # Refresh to get any changes made by the engine
    
    return db_task

@app.get("/tasks/", response_model=List[Task])
def read_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    List all tasks.
    """
    tasks = db.query(models.Task).offset(skip).limit(limit).all()
    return tasks

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(
    task_id: int, 
    task: TaskUpdate, 
    db: Session = Depends(get_db), 
    skip_workflow: bool = False, 
    is_admin: bool = False
):
    """
    Update an existing task.
    skip_workflow: if true, the workflow engine will not be triggered.
    is_admin: flag to indicate the update comes from an admin.
    """
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Only update provided fields
    update_data = task.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)
    
    db.commit()
    db.refresh(db_task) # Propagate changes (like cascades)
    
    # Cascade completion if status is DONE
    if db_task.status == models.TaskStatus.DONE:
        cascade_completion(db_task, db)
        db.commit() # Commit cascade changes
    
    # Optional: Log if it's an admin update
    if is_admin:
        audit = models.AuditLog(
            task_id=task_id,
            message="[ADMIN] Mise à jour manuelle (Mode Administration)"
        )
        db.add(audit)
        db.commit()
    
    # Process Workflow Rules (only if not skipped)
    if not skip_workflow:
        process_workflow(db_task.id, db)
        db.refresh(db_task)
    
    return db_task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """
    Delete a task from the database.
    Idempotent: Returns success even if task doesn't exist.
    """
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        # Idempotence: If already deleted, consider it done.
        return {"message": f"Task {task_id} already deleted or not found"}
    
    # Optional: Unlink audit logs instead of deleting them to preserve history
    db.query(models.AuditLog).filter(models.AuditLog.task_id == task_id).update({"task_id": None})
    
    # Delete related workflow steps if any
    db.query(models.WorkflowStep).filter(models.WorkflowStep.task_id == task_id).delete()
    
    db.delete(db_task)
    db.commit()
    return {"message": f"Task {task_id} deleted successfully"}

@app.get("/tasks/{task_id}/audit", response_model=List[AuditLog])
def read_audit_logs(task_id: int, db: Session = Depends(get_db)):
    """
    Get audit logs for a specific task.
    """
    logs = db.query(models.AuditLog).filter(models.AuditLog.task_id == task_id).order_by(models.AuditLog.timestamp.desc()).all()
    return logs

@app.get("/backup")
def backup_database():
    """
    Create a backup of the SQLite database and return it as a downloadable file.
    """
    db_file = "workflow.db"
    if not os.path.exists(db_file):
        raise HTTPException(status_code=404, detail="Database file not found")
        
    # Create a backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"workflow_{timestamp}.db"
    
    # In a real app we might want to store backups in a specific folder
    # For now we create a copy on the fly to serve it, or just serve the file directly
    # To be safe and avoid locking issues, we copy it first.
    shutil.copy2(db_file, backup_filename)
    
    return FileResponse(
        path=backup_filename,
        filename=backup_filename,
        media_type='application/octet-stream'
    )

# --- Support Groups Endpoints ---

@app.get("/groups/", response_model=List[GroupResponse])
def get_support_groups(db: Session = Depends(get_db)):
    """
    Get all support groups, sorted by name.
    """
    groups = db.query(models.SupportGroup).order_by(models.SupportGroup.name).all()
    return groups

@app.post("/groups/", response_model=GroupResponse)
def create_support_group(group: GroupCreate, db: Session = Depends(get_db)):
    """
    Create a new support group.
    """
    # Check if group name already exists
    existing = db.query(models.SupportGroup).filter(models.SupportGroup.name == group.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Group name already exists")
    
    db_group = models.SupportGroup(name=group.name)
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    
    # Audit log
    audit = models.AuditLog(message=f"[ADMIN] Groupe de support créé: {group.name}")
    db.add(audit)
    db.commit()
    
    return db_group

@app.delete("/groups/{group_id}")
def delete_support_group(group_id: int, db: Session = Depends(get_db)):
    """
    Delete a support group by ID.
    """
    db_group = db.query(models.SupportGroup).filter(models.SupportGroup.id == group_id).first()
    if not db_group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    group_name = db_group.name
    db.delete(db_group)
    db.commit()
    
    # Audit log
    audit = models.AuditLog(message=f"[ADMIN] Groupe de support supprimé: {group_name}")
    db.add(audit)
    db.commit()
    
    return {"message": f"Group '{group_name}' deleted successfully"}
