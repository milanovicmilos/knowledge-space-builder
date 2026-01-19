import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import AgglomerativeClustering
from pypdf import PdfReader
from app.config import settings
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
            self.model = SentenceTransformer(settings.SEMANTIC_MODEL_NAME)
            
    def extract_item_texts(self, items: list) -> dict:
        """
        Extracts text definitions for items from the PDF.
        Maps item_code -> text_snippet.
        """
        if not settings.PDF_FILE.exists():
            logger.error(f"PDF file not found at {settings.PDF_FILE}")
            return {item: "Description not found" for item in items}

        logger.info("Extracting text from PDF...")
        try:
            reader = PdfReader(settings.PDF_FILE)
            full_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
        except Exception as e:
            logger.error(f"Failed to read PDF: {e}")
            return {}

        descriptions = {}
        found_count = 0
        
        for item in items:
            # Heuristic: Items are codes like 's1m11a091'.
            # In PDF they appear as 'm11a091' usually.
            if item.startswith('s1') or item.startswith('s2'):
                search_term = item[2:]
            else:
                search_term = item
            
            # Find in text
            idx = full_text.find(search_term)
            if idx != -1:
                # Capture next 300 chars, assuming it's the question text
                snippet = full_text[idx:idx+400].replace('\n', ' ')
                
                # Cleanup: regex or just simple string manip
                # Maybe stop at "Platz für Notizen" or next "Aufgabe"
                if "Platz für Notizen" in snippet:
                    snippet = snippet.split("Platz für Notizen")[0]
                
                descriptions[item] = snippet.strip()
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

    def generate_semantic_clusters(self, items: list, n_clusters=None, output_dir=None):
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
        if output_dir:
            from pathlib import Path
            output_path = Path(output_dir) / "semantic_clusters.json"
        else:
            output_path = settings.OUTPUT_DIR / "semantic_clusters.json"
            
        with open(output_path, 'w') as f:
            json.dump(clusters, f, indent=2)
            
        logger.info(f"Saved {len(clusters)} semantic clusters to {output_path}")
        return clusters

    def run_semantic_classification(self, cleaned_file_path=None, output_dir=None):
        """
        Main workflow: Load items, classify via LLM, cluster via embeddings, save results.
        """
        logger.info("Starting semantic classification workflow...")
        
        # Load cleaned data
        if cleaned_file_path:
            import pandas as pd
            data = pd.read_csv(cleaned_file_path)
            logger.info(f"Loaded cleaned data from {cleaned_file_path}")
        else:
            from app.services.preprocessing_service import preprocessing_service
            data = preprocessing_service.load_cleaned_data()
        
        items = data.columns.tolist()
        
        logger.info(f"Processing {len(items)} items...")
        
        # Step 1: Extract texts
        item_texts = self.extract_item_texts(items)
        
        # Step 2: LLM classification (optional, can be disabled if quota low)
        llm_classifications = {}
        try:
            from app.services.llm_service import llm_service
            if llm_service.client:
                logger.info("Attempting LLM-based domain classification...")
                llm_classifications = llm_service.classify_items_batch(item_texts, batch_size=10, use_cache=True)
            else:
                logger.warning("LLM client unavailable; skipping LLM classification.")
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}. Continuing with embedding clustering only.")
        
        # Step 3: Embedding-based clustering
        clusters = self.generate_semantic_clusters(items, n_clusters=None, output_dir=output_dir)
        
        logger.info("Semantic classification complete.")
        return clusters, llm_classifications

semantic_service = SemanticService()
