from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, BigInteger, Text
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
    
    # Primary result payloads stored as JSON in the DB
    knowledge_space = Column(JSON)  # Full knowledge_space.json structure
    implications = Column(JSON)  # Extracted prerequisite relationships
    semantic_clusters_data = Column(JSON)  # Semantic clusters mapping
    llm_classifications = Column(JSON)  # Item -> concept mappings
    item_difficulties = Column(JSON)  # Item difficulty scores

    # Storage keys for result files (if saved on disk)
    result_files = Column(JSON)  # {filename: storage_path}
    
    # Metadata
    source = Column(String)  # 'web_app' ili 'cli'
    storage_location = Column(String)  # 'postgresql' ili 'filesystem'
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

