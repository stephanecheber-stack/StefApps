# -*- coding: utf-8 -*-
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class AssetBase(BaseModel):
    name: str
    asset_type: str
    serial_number: str
    status: str = "En stock"
    assigned_user: Optional[str] = None

class AssetCreate(AssetBase):
    pass

class Asset(AssetBase):
    id: int
    class Config: from_attributes = True

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[str] = "Moyenne"
    status: Optional[str] = "Nouveau"
    assigned_to: Optional[str] = "Non assigné"
    tags: Optional[str] = None
    parent_id: Optional[int] = None
    asset_id: Optional[int] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(TaskBase):
    title: Optional[str] = None

class Task(TaskBase):
    id: int
    class Config: from_attributes = True

class GroupCreate(BaseModel):
    name: str

class AuditLogCreate(BaseModel):
    message: str