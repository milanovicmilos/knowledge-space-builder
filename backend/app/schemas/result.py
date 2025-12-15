from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any


class ResultResponse(BaseModel):
    id: int
    task_id: int
    graph_storage_key: str
    num_states: int | None
    num_edges: int | None
    num_relations: int | None
    discrepancy: float | None
    is_valid: bool | None
    algorithm: str
    final_generation: int | None
    execution_time_seconds: int | None
    result_metadata: Dict[str, Any] | None
    created_at: datetime
    
    class Config:
        from_attributes = True
