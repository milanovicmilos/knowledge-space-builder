from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class Result(Base):
    __tablename__ = "results"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), unique=True, nullable=False)
    graph_storage_key = Column(String(500), nullable=False)
    num_states = Column(Integer)
    num_edges = Column(Integer)
    execution_time_seconds = Column(Integer)
    result_metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
