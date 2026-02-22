# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from database import Base
import enum

class TaskStatus(str, enum.Enum):
    NOUVEAU = "Nouveau"
    TODO = "À faire"
    IN_PROGRESS = "En cours"
    DONE = "Terminé"

from sqlalchemy.orm import relationship, backref

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    status = Column(Enum(TaskStatus), default=TaskStatus.NOUVEAU)
    priority = Column(String, default="Moyenne")
    tags = Column(String, nullable=True)
    assigned_to = Column(String, nullable=True)
    parent_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    children = relationship("Task", cascade="all, delete-orphan", backref=backref('parent', remote_side=[id]))

class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    action = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    message = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class SupportGroup(Base):
    __tablename__ = "support_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
