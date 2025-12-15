from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    # pending, running, completed, failed
    celery_task_id = Column(String(255), unique=True)
    parameters = Column(JSONB, nullable=False)
    progress_percent = Column(Integer, default=0)
    current_generation = Column(Integer)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
