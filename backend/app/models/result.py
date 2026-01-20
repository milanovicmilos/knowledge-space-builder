from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, BigInteger
from sqlalchemy.sql import func
from app.database import Base


class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    
    # Statistics
    total_items = Column(Integer)
    total_concepts = Column(Integer)
    total_students = Column(Integer)
    knowledge_space_states = Column(Integer)
    prerequisites_found = Column(Integer)
    semantic_clusters = Column(Integer)
    root_concepts = Column(Integer)
    
    # Storage keys za fajlove
    result_files = Column(JSON)  # {filename: storage_path}
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
