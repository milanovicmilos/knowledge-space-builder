"""
Result Pydantic schemas
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class ResultBase(BaseModel):
    task_id: int
    total_items: int = 0
    total_concepts: int = 0
    total_students: int = 0
    knowledge_space_states: int = 0
    prerequisites_found: int = 0
    semantic_clusters: int = 0
    root_concepts: int = 0


class ResultCreate(ResultBase):
    result_files: Dict[str, str] = {}


class ResultStatistics(BaseModel):
    total_items: int
    total_concepts: int
    total_students: int
    knowledge_space_states: int
    prerequisites_found: int
    semantic_clusters: int
    root_concepts: int
    
    model_config = ConfigDict(from_attributes=True)


class ResultResponse(ResultBase):
    id: int
    result_files: Dict[str, Any] = {}
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
