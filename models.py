# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Table
from sqlalchemy.orm import relationship, backref
from database import Base
import datetime

def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

group_classification_link = Table(
    "group_classification_link",
    Base.metadata,
    Column("group_id", Integer, ForeignKey("groups.id"), primary_key=True),
    Column("classification_id", Integer, ForeignKey("classifications.id"), primary_key=True)
)

user_group_link = Table(
    "user_group_link",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id"), primary_key=True)
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    user_code = Column(String, unique=True, index=True) # A001 format
    first_name = Column(String)
    last_name = Column(String)
    location_id = Column(Integer, ForeignKey('locations.id'), nullable=True)
    
    groups = relationship("SupportGroup", secondary=user_group_link, backref="users")
    location = relationship("Location", backref="users")

class SupportGroup(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    classifications = relationship("TaskClassification", secondary=group_classification_link, backref="groups")

class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    asset_type = Column(String) # PC, Serveur, Mobile, Logiciel
    serial_number = Column(String, unique=True, index=True)
    status = Column(String, default="En stock") # En stock, Utilisé, En réparation, Hors service
    assigned_user = Column(String, nullable=True)

class TaskClassification(Base):
    __tablename__ = "classifications"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    priority = Column(String, default="Moyenne")
    status = Column(String, default="Nouveau")
    assigned_to = Column(String, default="Non assigné")
    tags = Column(String, nullable=True)
    parent_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    classification_id = Column(Integer, ForeignKey("classifications.id"), nullable=False)
    created_at = Column(DateTime, default=get_utc_now)
    closed_at = Column(DateTime, nullable=True)
    
    children = relationship("Task", cascade="all, delete-orphan", backref=backref('parent', remote_side=[id]))
    asset = relationship("Asset", backref="tasks")
    classification = relationship("TaskClassification", backref="tasks")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    message = Column(String)
    timestamp = Column(DateTime, default=get_utc_now)

class Location(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # Site or building name
    address = Column(String)
    zip_code = Column(String)
    city = Column(String)