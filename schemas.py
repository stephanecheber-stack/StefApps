# -*- coding: utf-8 -*-
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


# -----------------------------------------------------------------------------
# TÂCHES (TICKETS)
# -----------------------------------------------------------------------------

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "Moyenne"
    status: Optional[str] = "Nouveau"
    tags: Optional[str] = None
    assigned_to: Optional[str] = None
    parent_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[str] = None
    assigned_to: Optional[str] = None
    parent_id: Optional[int] = None


class TaskRead(TaskCreate):
    id: int
    status: str

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# GROUPES DE SUPPORT
# -----------------------------------------------------------------------------

class GroupCreate(BaseModel):
    name: str


class GroupRead(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# LOGS D'AUDIT
# -----------------------------------------------------------------------------

class AuditLogCreate(BaseModel):
    message: str
    task_id: Optional[int] = None


class AuditLogRead(BaseModel):
    id: int
    task_id: Optional[int] = None
    message: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
