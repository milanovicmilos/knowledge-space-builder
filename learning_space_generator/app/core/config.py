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
    
    # ===== REPRODUCIBILITY & RANDOMNESS =====
    # RANDOM_SEED: Kontroliše determinizam svih random operacija (numpy, torch, python random)
    # Koristiš: Preprocessing (DAE training), Knowledge space generation
    # Uticaj: Ista vrednost = isti rezultati između pokretanja. Različita = drugačiti DAE trenig
    RANDOM_SEED: int = int(os.getenv("RANDOM_SEED", "42"))
    
    # ===== DENOISING AUTOENCODER (DAE) SETTINGS =====
    # DAE_EPOCHS: Broj iteracija kroz ceo dataset tokom treninga
    # Koristiš: Preprocessing - trenira denoising autoencoder
    # Uticaj: Viši broj = bolje čišćenje podataka ali sporiji kod. 50 je dobar početak.
    DAE_EPOCHS: int = int(os.getenv("DAE_EPOCHS", "50"))
    
    # DAE_BATCH_SIZE: Koliko uzoraka se obradi pre nego što ažuriraj modela
    # Koristiš: Preprocessing - veličina batch-a pri treningu
    # Uticaj: Veći batch = stabilniji gradijenti ali više memorije. 32 je standardi
    DAE_BATCH_SIZE: int = int(os.getenv("DAE_BATCH_SIZE", "32"))
    
    # DAE_LEARNING_RATE: Brzina učenja pri optijmizaciji
    # Koristiš: Preprocessing - Adam optimizer learning rate
    # Uticaj: Viša vrednost = brža konvergencija ali može da divergira. 0.001 je klasičan
    DAE_LEARNING_RATE: float = float(os.getenv("DAE_LEARNING_RATE", "0.001"))
    
    # DAE_NOISE_FACTOR: Koliki deo podataka se "kvari" pri treningu (0.0-1.0)
    # Koristiš: Preprocessing - nasumično gašenje neurona ulaza
    # Uticaj: Viši faktor = jače čišćenje ali može da guši informacije. 0.1 = 10% buke
    DAE_NOISE_FACTOR: float = float(os.getenv("DAE_NOISE_FACTOR", "0.1"))
    
    # DAE_DENOISE_THRESHOLD: Prag za binarizaciju rekonstruovanih vrednosti (0.0-1.0)
    # Koristiš: Preprocessing - konvertovanje kontinualnih vrednosti u 0/1
    # Uticaj: Viši prag = strožiji kriterijum za "uspešnost". 0.5 = mora biti > 50%
    DAE_DENOISE_THRESHOLD: float = float(os.getenv("DAE_DENOISE_THRESHOLD", "0.5"))
    
    # ===== CONCEPT AGGREGATION SETTINGS =====
    # CONCEPT_BINARIZE_THRESHOLD: Prag za konverziju mastery score-ova u binarni oblik (0/1)
    # Koristiš: Concept aggregation - pravi agregacije stavki u koncepte
    # Uticaj: Viši prag = manji broj "savladanih" koncepata. 0.5 = savladan ako >= 50% stavki uspešnih
    CONCEPT_BINARIZE_THRESHOLD: float = float(os.getenv("CONCEPT_BINARIZE_THRESHOLD", "0.5"))
    
    # ===== IITA & STRUCTURE EXTRACTION SETTINGS =====
    # IITA_THRESHOLD_RATE: Procenat prosečne veličine uzorka (0.0-1.0)
    # Koristiš: Structure extraction - računa B matrica za prerequisite-e
    # Uticaj: Viši % = više prerequisite-a pronađeno. 0.05 = 5% uzorka = stroga selekcija
    IITA_THRESHOLD_RATE: float = float(os.getenv("IITA_THRESHOLD_RATE", "0.05"))
    
    # USE_CONCEPT_LEVEL_IITA: Koristi li IITA na nivu koncepata (True) ili stavki (False)
    # Koristiš: Structure extraction - odlučuje kakve podatke učitati
    # Uticaj: Concept-level = manji graf ali semantički smisleniji. Item-level = detaljniji
    USE_CONCEPT_LEVEL_IITA: bool = os.getenv("USE_CONCEPT_LEVEL_IITA", "True").lower() == "true"
    
    # SEMANTIC_WEIGHT: Kako mnogo semantička sličnost utiče na prerequisite-e (0.0-1.0)
    # Koristiš: Structure extraction - penalizuje nesličnih stavki
    # Uticaj: Viši = ako su stavke semantički različite, teže je preskočiti prerequisite. 0.3 = umeren
    SEMANTIC_WEIGHT: float = float(os.getenv("SEMANTIC_WEIGHT", "0.3"))
    
    # MIN_CLUSTER_SIZE_IITA: Minimalna veličina klastera za pokrećanje IITA na njemu
    # Koristiš: Structure extraction - filtriranje malih klastera
    # Uticaj: Viži broj = manje klastera se obrađuje posebno. 5 je malo malo
    MIN_CLUSTER_SIZE_IITA: int = int(os.getenv("MIN_CLUSTER_SIZE_IITA", "5"))
    
    # ===== KNOWLEDGE SPACE GENERATION SETTINGS =====
    # MAX_STATES_LIMIT: Maksimalan broj stanja koja se mogu generisati
    # Koristiš: Knowledge space generation - sprečava beskonačne petlje
    # Uticaj: Niži limit = brže ali mogućnost da preseče validna stanja. 50000 je bezbedan
    MAX_STATES_LIMIT: int = int(os.getenv("MAX_STATES_LIMIT", "50000"))
    
    # MAX_STATE_SIZE: Maksimalna veličina neposmatranog stanja (broj koncepata)
    # Koristiš: Knowledge space generation - filtrira stanja sa previše koncepata
    # Uticaj: Viži broj = više stanja generiše se (brže se dostiže limit). 8 = umeren
    MAX_STATE_SIZE: int = int(os.getenv("MAX_STATE_SIZE", "8"))
    
    # ===== SEMANTIC & NLP SETTINGS =====
    # SEMANTIC_MODEL_NAME: Koji model se koristi za računanje sličnosti između stavki
    # Koristiš: Semantic clustering - SentenceTransformer model
    # Uticaj: Drugačiji model = drugačije klastering. all-MiniLM je brz i dobar
    SEMANTIC_MODEL_NAME: str = os.getenv("SEMANTIC_MODEL_NAME", "all-MiniLM-L6-v2")
    
    # ===== LLM & ONTOLOGY SETTINGS =====
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
