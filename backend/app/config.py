from pydantic_settings import BaseSettings
from typing import List
from pathlib import Path
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@postgres:5432/learning_space_db"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Storage
    STORAGE_TYPE: str = "local"  # local or s3
    STORAGE_PATH: str = "storage" # Relative path for local dev, or /app/storage for docker
    
    # App
    DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost"
    
    # --- LSG Settings ---
    PROJECT_NAME: str = "SOTIS 2026 Knowledge Space"
    PROJECT_VERSION: str = "1.0.0"

    # OpenAI / LLM
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN") or os.getenv("OPENAI_API_KEY", "")
    GITHUB_API_URL: str = "https://models.inference.ai.azure.com"
    LLM_MODEL: str = "gpt-4o"
    LLM_ALTERNATIVES: str = "gpt-4o-mini,gpt-4"
    LLM_BATCH_SIZE: int = 20
    LLM_BATCH_PAUSE: float = 1.0
    LLM_CACHE_FILE: str = "llm_cache.json"

    # DAE Settings
    DAE_EPOCHS: int = 50
    DAE_BATCH_SIZE: int = 32
    DAE_LEARNING_RATE: float = 0.001
    DAE_NOISE_FACTOR: float = 0.1
    
    # IITA Settings
    IITA_THRESHOLD_RATE: float = 0.05 
    SEMANTIC_WEIGHT: float = 0.3
    MAX_STATES_LIMIT: int = 100000
    SEMANTIC_MODEL_NAME: str = "paraphrase-multilingual-MiniLM-L12-v2"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def BASE_DIR(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def DATA_DIR(self) -> Path:
        path = Path(self.STORAGE_PATH) / "inputs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def OUTPUT_DIR(self) -> Path:
        path = Path(self.STORAGE_PATH) / "outputs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    # Derived Paths (Properties to be compatible with LSG logic)
    @property
    def INPUT_FILE(self) -> Path:
        return self.DATA_DIR / "matheGesamt.csv" # Default, can be overridden by task

    @property
    def CLEANED_DATA_FILE(self) -> Path:
        return self.OUTPUT_DIR / "cleaned_responses.csv"

    @property
    def IMPLICATIONS_FILE(self) -> Path:
        return self.OUTPUT_DIR / "implications.json"

    @property
    def KNOWLEDGE_SPACE_FILE(self) -> Path:
        return self.OUTPUT_DIR / "knowledge_space.json"

    @property
    def GRAPH_IMAGE_FILE(self) -> Path:
         return self.OUTPUT_DIR / "knowledge_structure_graph.png"

    @property
    def PDF_FILE(self) -> Path:
        return self.DATA_DIR / "curriculum.pdf"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

