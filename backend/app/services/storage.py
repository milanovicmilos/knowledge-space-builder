import os
import uuid
from pathlib import Path
from app.config import settings


class StorageService:
    """Local file storage service"""
    
    def __init__(self):
        self.storage_path = Path(settings.STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def save_upload(self, content: bytes, filename: str) -> str:
        """Save uploaded file and return storage key"""
        upload_id = str(uuid.uuid4())
        storage_key = f"uploads/{upload_id}/{filename}"
        full_path = self.storage_path / storage_key
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'wb') as f:
            f.write(content)
        
        return storage_key
    
    def get_file(self, storage_key: str) -> bytes:
        """Retrieve file by storage key"""
        full_path = self.storage_path / storage_key
        with open(full_path, 'rb') as f:
            return f.read()
    
    def get_file_path(self, storage_key: str) -> str:
        """Get absolute path to file"""
        return str(self.storage_path / storage_key)
    
    def save_result(self, content: str, task_id: int, filename: str) -> str:
        """Save result file and return storage key"""
        storage_key = f"results/{task_id}/{filename}"
        full_path = self.storage_path / storage_key
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'w') as f:
            f.write(content)
        
        return storage_key
    
    def delete_file(self, storage_key: str):
        """Delete file by storage key"""
        full_path = self.storage_path / storage_key
        if full_path.exists():
            full_path.unlink()


storage_service = StorageService()
