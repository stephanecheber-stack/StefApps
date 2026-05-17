# -*- coding: utf-8 -*-
from pydantic import BaseModel, ConfigDict
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
    model_config = ConfigDict(from_attributes=True)

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
    model_config = ConfigDict(from_attributes=True)

class ClassificationCreate(BaseModel):
    name: str

class ClassificationUpdate(BaseModel):
    name: Optional[str] = None

class Classification(ClassificationCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

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
    model_config = ConfigDict(from_attributes=True)

class AuditLogCreate(BaseModel):
    message: str
class UserBase(BaseModel):
    first_name: str
    last_name: str
    location_id: Optional[int] = None

class UserCreate(UserBase):
    group_ids: List[int]

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    group_ids: Optional[List[int]] = None
    location_id: Optional[int] = None

class LocationBase(BaseModel):
    name: str
    address: str
    zip_code: str
    city: str

class LocationCreate(LocationBase):
    pass

class LocationUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None

class LocationNested(LocationBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class User(UserBase):
    id: int
    user_code: str
    groups: List[SupportGroup] = []
    location: Optional[LocationNested] = None
    model_config = ConfigDict(from_attributes=True)

class UserNested(UserBase):
    id: int
    user_code: str
    model_config = ConfigDict(from_attributes=True)

class Location(LocationBase):
    id: int
    users: List[UserNested] = []
    model_config = ConfigDict(from_attributes=True)
