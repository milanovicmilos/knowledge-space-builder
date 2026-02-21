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
    # PDF_FILE: Try uploaded_tasks.pdf first (from frontend), fallback to default COINS PDF
    _uploaded_pdf = DATA_DIR / "uploaded_tasks.pdf"
    PDF_FILE: Path = _uploaded_pdf if _uploaded_pdf.exists() else DATA_DIR / "COINS-alle-Cluster-CH.pdf"
    COINS_TEXT_FILE: Path = DATA_DIR / "COINS-alle-Cluster-CH.txt"
    
    CLEANED_DATA_FILE: Path = OUTPUT_DIR / "cleaned_responses.csv"
    IMPLICATIONS_FILE: Path = OUTPUT_DIR / "implications.json"
    KNOWLEDGE_SPACE_FILE: Path = OUTPUT_DIR / "knowledge_space.json"
    GRAPH_IMAGE_FILE: Path = OUTPUT_DIR / "knowledge_structure_graph.png"
    
    # ===== REPRODUCIBILITY & RANDOMNESS =====
    # RANDOM_SEED: Controls determinism for random operations (numpy, torch, python random)
    # Used by: Preprocessing (DAE training), knowledge space generation
    # Effect: Same value -> reproducible runs. Different value -> different DAE training
    RANDOM_SEED: int = int(os.getenv("RANDOM_SEED", "42"))
    
    # ===== DENOISING AUTOENCODER (DAE) SETTINGS =====
    # DAE_EPOCHS: Number of full passes over the dataset during training
    # Used by: Preprocessing - trains the denoising autoencoder
    # Effect: Higher = better cleaning but slower. 50 is a reasonable default.
    DAE_EPOCHS: int = int(os.getenv("DAE_EPOCHS", "50"))
    
    # DAE_BATCH_SIZE: Number of samples processed before updating the model
    # Used by: Preprocessing - training batch size
    # Effect: Larger batch = more stable gradients but higher memory. 32 is standard.
    DAE_BATCH_SIZE: int = int(os.getenv("DAE_BATCH_SIZE", "32"))
    
    # DAE_LEARNING_RATE: Learning rate for the optimizer
    # Used by: Preprocessing - Adam optimizer learning rate
    # Effect: Higher = faster convergence but risk of divergence. 0.001 is common.
    DAE_LEARNING_RATE: float = float(os.getenv("DAE_LEARNING_RATE", "0.001"))
    
    # DAE_NOISE_FACTOR: Fraction of input values masked/noised during training (0.0-1.0)
    # Used by: Preprocessing - input dropout/noise
    # Effect: Higher = stronger denoising but may remove signal. 0.1 = 10% noise.
    DAE_NOISE_FACTOR: float = float(os.getenv("DAE_NOISE_FACTOR", "0.1"))
    
    # DAE_DENOISE_THRESHOLD: Threshold to binarize reconstructed values (0.0-1.0)
    # Used by: Preprocessing - convert continuous reconstructions into 0/1
    # Effect: Higher = stricter mastery criterion. 0.5 = >50% considered success.
    DAE_DENOISE_THRESHOLD: float = float(os.getenv("DAE_DENOISE_THRESHOLD", "0.5"))
    
    # ===== CONCEPT AGGREGATION SETTINGS =====
    # CONCEPT_BINARIZE_THRESHOLD: Threshold to convert mastery scores to binary (0/1)
    # Used by: Concept aggregation - aggregate item-level responses into concepts
    # Effect: Higher threshold = fewer concepts considered mastered. 0.5 = >=50% items.
    CONCEPT_BINARIZE_THRESHOLD: float = float(os.getenv("CONCEPT_BINARIZE_THRESHOLD", "0.5"))
    
    # ===== IITA & STRUCTURE EXTRACTION SETTINGS =====
    # IITA_THRESHOLD_RATE: Fraction of average sample size used in IITA (0.0-1.0)
    # Used by: Structure extraction - computes B matrices for prerequisites
    # Effect: Higher = more prerequisites detected. 0.05 = strict selection.
    IITA_THRESHOLD_RATE: float = float(os.getenv("IITA_THRESHOLD_RATE", "0.05"))
    
    # USE_CONCEPT_LEVEL_IITA: Run IITA at concept level (True) or item level (False)
    # Used by: Structure extraction - chooses which data to load
    # Effect: Concept-level = smaller, semantically meaningful graph. Item-level = more detailed.
    USE_CONCEPT_LEVEL_IITA: bool = os.getenv("USE_CONCEPT_LEVEL_IITA", "True").lower() == "true"
    
    # SEMANTIC_WEIGHT: How much semantic similarity influences prerequisites (0.0-1.0)
    # Used by: Structure extraction - penalizes semantically dissimilar items
    # Effect: Higher = harder to skip prerequisites when items are dissimilar. 0.3 = moderate.
    SEMANTIC_WEIGHT: float = float(os.getenv("SEMANTIC_WEIGHT", "0.3"))
    
    # MIN_CLUSTER_SIZE_IITA: Minimum cluster size to run IITA on
    # Used by: Structure extraction - filter out very small clusters
    # Effect: Higher = fewer clusters are processed separately. 5 is small.
    MIN_CLUSTER_SIZE_IITA: int = int(os.getenv("MIN_CLUSTER_SIZE_IITA", "5"))
    
    # ===== KNOWLEDGE SPACE GENERATION SETTINGS =====
    # MAX_STATES_LIMIT: Maximum number of knowledge states to generate
    # Used by: Knowledge space generation - prevents infinite loops
    # Effect: Lower limit = faster but may cut valid states. 50000 is safe.
    MAX_STATES_LIMIT: int = int(os.getenv("MAX_STATES_LIMIT", "50000"))
    
    # MAX_STATE_SIZE: Maximum size of an unobserved state (number of concepts)
    # Used by: Knowledge space generation - filter states with too many concepts
    # Effect: Higher = more states generated (limit reached faster). 8 = moderate.
    MAX_STATE_SIZE: int = int(os.getenv("MAX_STATE_SIZE", "8"))
    
    # ===== SEMANTIC & NLP SETTINGS =====
    # SEMANTIC_MODEL_NAME: Model used for computing item similarity
    # Used by: Semantic clustering - SentenceTransformer model
    # Effect: Different model -> different clustering. all-MiniLM is fast and good.
    SEMANTIC_MODEL_NAME: str = os.getenv("SEMANTIC_MODEL_NAME", "all-MiniLM-L6-v2")
    
    # ===== LLM & ONTOLOGY SETTINGS =====
    # GitHub Models API
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_API_URL: str = "https://models.github.ai/inference"
    OPENAI_API_URL: str = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1")
    
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

    # Controlled domain vocabulary for item/cluster labeling
    ALLOWED_MATH_DOMAINS: str = os.getenv(
        "ALLOWED_MATH_DOMAINS",
        "Lineare Funktionen,Geradengleichungen und Graphen,Steigung und Parallelität,Gleichungen und Umformungen,Algebra und Terme,Geometrie,Anwendungsaufgaben,Finanzmathematik"
    )
    
settings = Settings()
