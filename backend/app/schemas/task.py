"""
Task Pydantic schemas
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class TaskBase(BaseModel):
    upload_id: int
    status: str
    progress: int
    message: str
    parameters: Dict[str, Any] = {}


class TaskCreate(TaskBase):
    pass


class TaskStatus(BaseModel):
    task_id: int
    status: str
    progress: int
    message: str
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class TaskResponse(TaskBase):
    id: int
    celery_task_id: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

