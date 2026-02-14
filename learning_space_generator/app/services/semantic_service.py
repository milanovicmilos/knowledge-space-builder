import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import AgglomerativeClustering
from pypdf import PdfReader
from learning_space_generator.app.core.config import settings
import logging
import json
import numpy as np

logger = logging.getLogger(__name__)

class SemanticService:
    def __init__(self):
        self.model = None
        self.embeddings = None
        self.item_texts = {}
        self.similarity_matrix = None
        
    def load_model(self):
        if self.model is None:
            logger.info(f"Loading Semantic Model: {settings.SEMANTIC_MODEL_NAME}...")
            # Explicitly force CPU to avoid any CUDA dependencies on non-GPU machines
            self.model = SentenceTransformer(settings.SEMANTIC_MODEL_NAME, device='cpu')
            
    def _read_text_file(self, path) -> str:
        for encoding in ("utf-8", "latin-1"):
            try:
                with open(path, "r", encoding=encoding) as f:
                    return f.read()
            except Exception:
                continue
        raise ValueError(f"Unable to read text file: {path}")

    def _extract_snippet(self, full_text: str, search_term: str) -> str | None:
        idx = full_text.find(search_term)
        if idx == -1:
            return None

        snippet = full_text[idx:idx + 1500]

        # Stop at common delimiters if present after the match
        cut_points = []
        for marker in ("Platz für Notizen", "--- PAGE", "Aufgabe "):
            pos = snippet.find(marker, 1)
            if pos != -1:
                cut_points.append(pos)

        if cut_points:
            snippet = snippet[:min(cut_points)]

        # Normalize whitespace for consistent output
        return " ".join(snippet.split()).strip()

    def extract_item_texts(self, items: list) -> dict:
        """
        Extracts text definitions for items from COINS TXT/PDF.
        Maps item_code -> text_snippet.
        """
        full_text = ""

        if settings.COINS_TEXT_FILE.exists():
            logger.info(f"Extracting text from TXT: {settings.COINS_TEXT_FILE}")
            try:
                full_text = self._read_text_file(settings.COINS_TEXT_FILE)
            except Exception as e:
                logger.error(f"Failed to read TXT file: {e}")

        if not full_text and settings.PDF_FILE.exists():
            logger.info(f"Extracting text from PDF: {settings.PDF_FILE}")
            try:
                reader = PdfReader(settings.PDF_FILE)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
            except Exception as e:
                logger.error(f"Failed to read PDF: {e}")

        if not full_text:
            logger.error("No text source available for item descriptions.")
            return {item: "Description not found" for item in items}

        descriptions = {}
        found_count = 0

        for item in items:
            # Heuristic: Items are codes like 's1m11a091'.
            # In COINS text they appear as 'm11a091'.
            if item.startswith('s1') or item.startswith('s2'):
                search_term = item[2:]
            else:
                search_term = item

            snippet = self._extract_snippet(full_text, search_term)
            if snippet:
                descriptions[item] = snippet
                found_count += 1
            else:
                descriptions[item] = f"Question {item} (Text not found)"

        logger.info(f"Extracted descriptions for {found_count}/{len(items)} items.")
        self.item_texts = descriptions
        return descriptions

    def generate_embeddings(self, items: list):
        if not self.item_texts:
            self.extract_item_texts(items)
            
        texts = [self.item_texts.get(item, "") for item in items]
        
        self.load_model()
        logger.info("Generating embeddings...")
        self.embeddings = self.model.encode(texts)
        return self.embeddings

    def calculate_similarity_matrix(self, items: list) -> pd.DataFrame:
        if self.embeddings is None:
            self.generate_embeddings(items)
            
        logger.info("Calculating cosine similarity matrix...")
        sim_matrix = cosine_similarity(self.embeddings)
        
        # Convert to DataFrame for easy lookup
        df_sim = pd.DataFrame(sim_matrix, index=items, columns=items)
        self.similarity_matrix = df_sim
        return df_sim

    def generate_semantic_clusters(self, items: list, n_clusters=None):
        """
        Groups items into semantic clusters (concepts) using Agglomerative Clustering.
        """
        if self.embeddings is None:
            self.generate_embeddings(items)
            
        # Distance matrix = 1 - Similarity (approx)
        # Or just use euclidean on embeddings
        
        logger.info("Clustering items semantically...")
        # Heuristic: If n_clusters not provided, try to find reasonable number
        # e.g. sqrt(n_items) or something, or distance threshold
        
        if n_clusters is None:
            n_clusters = max(5, int(len(items) / 5)) # ~25 items per cluster roughly?
        
        clustering = AgglomerativeClustering(n_clusters=n_clusters)
        labels = clustering.fit_predict(self.embeddings)
        
        clusters = {}
        for item, label in zip(items, labels):
            lbl_str = str(label)
            if lbl_str not in clusters:
                clusters[lbl_str] = []
            clusters[lbl_str].append(item)
            
        # Save visualization data
        output_path = settings.OUTPUT_DIR / "semantic_clusters.json"
        with open(output_path, 'w') as f:
            json.dump(clusters, f, indent=2)
            
        logger.info(f"Saved {len(clusters)} semantic clusters to {output_path}")
        return clusters

    def run_semantic_classification(self):
        """
        Main workflow: Load items, classify via LLM, cluster via embeddings, save results.
        """
        logger.info("Starting semantic classification workflow...")
        
        # Load cleaned data
        from learning_space_generator.app.services.preprocessing_service import preprocessing_service
        data = preprocessing_service.load_cleaned_data()
        items = data.columns.tolist()
        
        logger.info(f"Processing {len(items)} items...")
        
        # Step 1: Extract texts
        item_texts = self.extract_item_texts(items)
        
        # Step 2: LLM classification (optional, can be disabled if quota low)
        llm_classifications = {}
        try:
            from learning_space_generator.app.services.llm_service import llm_service
            if llm_service.client:
                logger.info("Attempting LLM-based domain classification...")
                llm_classifications = llm_service.classify_items_batch(item_texts, batch_size=10, use_cache=True)
            else:
                logger.warning("LLM client unavailable; skipping LLM classification.")
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}. Continuing with embedding clustering only.")
        
        # Step 3: Embedding-based clustering
        clusters = self.generate_semantic_clusters(items, n_clusters=None)
        
        logger.info("Semantic classification complete.")
        return clusters, llm_classifications

semantic_service = SemanticService()
