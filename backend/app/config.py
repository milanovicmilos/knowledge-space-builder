from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@postgres:5432/learning_space_db"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Storage
    STORAGE_TYPE: str = "local"  # local or s3
    STORAGE_PATH: str = "/app/storage"
    
    # App
    DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
