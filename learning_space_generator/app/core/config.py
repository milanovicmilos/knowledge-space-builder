import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "SOTIS 2026 Knowledge Space"
    PROJECT_VERSION: str = "1.0.0"
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    OUTPUT_DIR: Path = BASE_DIR / "output"
    
    # INPUT_FILE: Try uploaded_data.csv first (from frontend), fallback to matheGesamt.csv (local)
    _uploaded = DATA_DIR / "uploaded_data.csv"
    INPUT_FILE: Path = _uploaded if _uploaded.exists() else DATA_DIR / "matheGesamt.csv"
    PDF_FILE: Path = DATA_DIR / "COINS-alle-Cluster-CH.pdf"
    
    CLEANED_DATA_FILE: Path = OUTPUT_DIR / "cleaned_responses.csv"
    IMPLICATIONS_FILE: Path = OUTPUT_DIR / "implications.json"
    KNOWLEDGE_SPACE_FILE: Path = OUTPUT_DIR / "knowledge_space.json"
    GRAPH_IMAGE_FILE: Path = OUTPUT_DIR / "knowledge_structure_graph.png"
    
    # DAE Settings
    DAE_EPOCHS: int = 50
    DAE_BATCH_SIZE: int = 32
    DAE_LEARNING_RATE: float = 0.001
    DAE_NOISE_FACTOR: float = 0.1
    
    # IITA Settings
    IITA_THRESHOLD_RATE: float = 0.05
    USE_CONCEPT_LEVEL_IITA: bool = True  # NEW: Run IITA on concepts, not items
    
    # JSON Generation
    MAX_STATES_LIMIT: int = 50000  # Increased to allow full generation without artificial cutoff
    
    # Semantic Settings
    SEMANTIC_MODEL_NAME: str = "all-MiniLM-L6-v2"
    SEMANTIC_WEIGHT: float = 0.3 # Lambda factor for regularizer settings (DISABLED for concept-level IITA)
    
    # LLM & Ontology Settings
    # GitHub Models API
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_API_URL: str = "https://models.github.ai/inference"
    # Primary model (gpt-4o-mini for free tier)
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    # Comma separated list of alternative models to try if primary fails
    LLM_ALTERNATIVES: str = os.getenv(
        "LLM_ALTERNATIVES",
        "gpt-4o-mini",
    )
    # How many clusters to batch per LLM request
    LLM_BATCH_SIZE: int = int(os.getenv("LLM_BATCH_SIZE", "5"))
    # Pause seconds between batches to reduce rate-limit hits
    LLM_BATCH_PAUSE: float = float(os.getenv("LLM_BATCH_PAUSE", "2"))
    # LLM cache file name (stored in OUTPUT_DIR)
    LLM_CACHE_FILE: str = os.getenv("LLM_CACHE_FILE", "llm_cache.json")
    
settings = Settings()
