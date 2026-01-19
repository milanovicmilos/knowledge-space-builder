# Implementation Phase 2: Semantic Enrichment & Hybrid Algorithms

## Overview
This phase elevates the project from a standard statistical analysis to a **Hybrid Semantic-Statistical approach**. We will introduce "Semantic Regularization" to the Knowledge Space Theory (KST) construction process. 

By analyzing the textual content of the items (questions), we can extract semantic features and relationships (an implicit ontology). These semantic clusters will guide the statistical algorithm (IITA), filtering out spurious correlations and reinforcing logically coherent connections.

## The "Best Idea" Methodology: Semantic-Regularized IITA

We will implement a pipeline that fuses **Natural Language Processing (NLP)** with **Inductive Item Tree Analysis (IITA)**.

### Step 1: Text Extraction & Normalization
*   **Source:** `COINS-alle-Cluster-CH.pdf`.
*   **Action:** Extract text for each item code (`s1m...`).
*   **Technique:** Use PDF parsing with regex matching to map item codes to their question descriptions.

### Step 2: Semantic Embedding (Vector Space)
*   **Technology:** `sentence-transformers` (HuggingFace).
*   **Model:** `all-MiniLM-L6-v2` (Fast, lightweight, high accuracy).
*   **Process:** Convert each item's text into a 384-dimensional dense vector.
*   **Outcome:** A mathematical representation where "similar meanings have similar vectors".

### Step 3: Semantic Similarity Matrix
*   Calculate **Cosine Similarity** between all pairs of items.
*   $S_{xy} \in [0, 1]$, where 1 means texts are almost identical, 0 means unrelated.

### Step 4: Hybrid Structure Extraction (The Core Innovation)
Standard IITA accepts an implication $A \to B$ if the number of counter-examples $b_{xy}$ (students who failed A but solved B) is below a threshold.

**New Hybird Rule:**
We penalize implications between semantically unrelated items.
$$ \text{Score}_{xy} = b_{xy} + \lambda \cdot (1 - S_{xy}) \cdot N_{students} $$

*   **$b_{xy}$**: Statistical "Evidence against implication" (Counter-examples).
*   **$(1 - S_{xy})$**: Semantic "Distance". High if items are unrelated.
*   **$\lambda$ (Lambda)**: Hyperparameter controlling the Semantic Filter strength.

**Logic:**
*   If $A$ and $B$ are semantically close ($S_{xy} \approx 1$), the penalty is 0. We trust the statistics purely.
*   If $A$ and $B$ are unrelated ($S_{xy} \approx 0$), the penalty is high. The statistical evidence must be *extremely strong* (very few counter-examples) to overcome the semantic penalty.

### Step 5: Clustering (Ontology Visualization)
*   Use **Agglomerative Clustering** on the semantic vectors to group items into "Concepts" or "Topics".
*   This creates a coarse-grained Ontology (e.g., "Geometry", "Algebra").
*   These clusters will be saved to `semantic_clusters.json` to enrich the frontend visualization.

## Technical Architecture Changes

1.  **New Service:** `app/services/semantic_service.py`
    *   Handles PDF parsing, Embedding generation, and Similarity calculation.
2.  **Modified Service:** `app/services/structure_service.py`
    *   Integrates the Semantic Matrix into the `extract_implications` loop.
3.  **Config:** New parameters (`SEMANTIC_WEIGHT`, `MODEL_NAME`).
