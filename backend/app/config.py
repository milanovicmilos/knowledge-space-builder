from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List
import os


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/learning_space_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # App
    DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost"

    # Storage
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "storage")
    UPLOAD_PATH: str = os.getenv("UPLOAD_PATH", "storage/uploads")
    
    # Learning Space Generator
    LSG_PATH: str = os.getenv("LSG_PATH", str(Path(__file__).parent.parent.parent / "learning_space_generator"))
    LSG_OUTPUT_PATH: str = os.getenv("LSG_OUTPUT_PATH", str(Path(__file__).parent.parent.parent / "learning_space_generator" / "output"))
    LSG_SCRIPT: str = "app/main.py"

    # Project Info
    PROJECT_NAME: str = "SOTIS 2026 - Knowledge Space Generator"
    PROJECT_VERSION: str = "2.0.0"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


settings = Settings()
