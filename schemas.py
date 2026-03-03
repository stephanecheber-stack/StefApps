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
    classification_id: Optional[int] = None
    created_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

class TaskCreate(TaskBase):
    classification_id: int

class TaskUpdate(TaskBase):
    title: Optional[str] = None

class Task(TaskBase):
    id: int
    classification_name: Optional[str] = None
    class Config: from_attributes = True

class GroupCreate(BaseModel):
    name: str
    classification_ids: List[int]

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    classification_ids: Optional[List[int]] = None

class SupportGroup(BaseModel):
    id: int
    name: str
    classifications: List[Classification] = []
    class Config: from_attributes = True

class AuditLogCreate(BaseModel):
    message: str

class ClassificationCreate(BaseModel):
    name: str

class Classification(ClassificationCreate):
    id: int
    class Config: from_attributes = True