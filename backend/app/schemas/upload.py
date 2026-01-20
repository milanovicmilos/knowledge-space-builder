"""
Upload Pydantic schemas
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UploadBase(BaseModel):
    filename: str
    storage_key: str
    file_size_bytes: int
    num_rows: int = 0
    num_columns: int = 0


class UploadCreate(UploadBase):
    pass


class UploadResponse(UploadBase):
    id: int
    uploaded_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
