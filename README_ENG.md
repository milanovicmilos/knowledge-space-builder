# Knowledge Space Builder - SOTIS 2026

**An intelligent platform for constructing, visualizing, and analyzing knowledge spaces in the mathematics domain, with a semantic web layer for SOTIS integration.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.0-61DAFB.svg?logo=react)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6.svg?logo=typescript)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python)](https://www.python.org)

---

## Project Overview

**Knowledge Space Builder** is a full research-to-production application that implements **Knowledge Space Theory (KST)** in the mathematics domain, enriched with semantic annotation and RDF/OWL export compatible with the **SOTIS** platform. The project is developed in collaboration with **Pädagogischen Hochschule St.Gallen (PHSG)** and covers the entire workflow: from ingesting real test data, through knowledge space construction, to pedagogical and semantic analytics.

**Objectives (per specification):**
- Construct and visualize a knowledge space from real mathematics test data.
- Adapt a knowledge space construction algorithm and build a system to manage the results.
- Produce an educational goals ontology for semantic web and SOTIS integration.

---

## System Architecture

![System architecture](diagram2.png)

### Components

1. **Frontend** (`frontend/`)
   - React 18 + TypeScript + Material-UI
   - CSV upload, status monitoring, visualization, and dashboard metrics.

2. **Backend** (`backend/`)
   - FastAPI + SQLAlchemy + Celery + Redis
   - Orchestrator: accepts uploads, schedules tasks, stores results in PostgreSQL, exposes REST APIs.

3. **Learning Space Generator (LSG)** (`learning_space_generator/`)
   - PyTorch + NetworkX + RDFLib + Sentence Transformers
   - Core algorithm, validation, visualization, and ontology generation.

---

## Data Flow

1. **CSV/PDF upload** via UI or API.
2. **Backend** stores the file and creates a task in the database.
3. **Celery** runs the LSG pipeline via direct Python imports.
4. **Artifacts** are written to `learning_space_generator/output/` and indexed in the DB.
5. **Frontend** displays status, graphs, and semantic results.

Note: the data-flow diagram should be a separate image (add it when available).

---

## LSG Pipeline (9 Phases)

The Learning Space Generator (LSG) runs as a sequential pipeline composed of nine phases. These phases reflect the complete analytic flow used in the accompanying seminar paper and implementation.

1. **Data Preparation** – initial checks and metadata extraction.
2. **Data Imputation & Denoising** – DAE (Denoising Autoencoder) to fill missing responses and reduce noise.
3. **Semantic Classification** – LLM-based classification and sentence-embedding clustering to group items into concepts.
4. **Concept Aggregation** – aggregate item-level responses to concept-level mastery matrices.
5. **Difficulty Analysis** – estimate item and concept difficulty and order items pedagogically.
6. **Structure Extraction** – IITA (Inductive Item Tree Analysis) for extracting prerequisite relations.
7. **Knowledge Space Generation** – generate valid knowledge states from the prerequisite graph.
8. **Visualization & Validation** – render graphs, run structural and pedagogical validation tests.
9. **Ontology Export & Persistence** – serialize results to RDF/OWL (Turtle) and save artifacts.

---

## Semantic Web Layer

The semantic layer generates an ontology of educational goals and relations between concepts and items.

- **Format:** Turtle (`.ttl`) and OWL/XML
- **Output:** `learning_space_generator/output/sotis_ontology.ttl`
- **Vocabulary:** SOTIS namespace `http://www.sotis-conference.org/ontology#`

### Semantic API (backend)
- `GET /api/v1/analysis/{task_id}/goals` – list learning goals from the ontology.
- `GET /api/v1/analysis/{task_id}/goal-path?goal_id=...` – recommended learning path based on prerequisites.

---

## Input Data Format

CSV format follows real test data conventions.

- Separator is `;`.
- Item columns start with `s` (except `standort`).
- Values: `1` correct, `0` incorrect.
- `9999` and `666` are treated as missing values.

---

## Output Artifacts

LSG writes artifacts to `learning_space_generator/output/`:

- `cleaned_responses.csv`
- `aggregated_concepts.csv`
- `aggregated_concepts_binary.csv`
- `item_difficulties.json`
- `concepts_sorted_by_difficulty.json`
- `implications.json`
- `knowledge_space.json`
- `knowledge_structure_graph.png`
- `sotis_ontology.ttl`

## Evaluation Summary

Key evaluation metrics reported in the project paper and reproduced by the reference analysis:

- Dataset: 692 students, 121 items
- Semantic concepts (final model): 7
- Generated knowledge states: 44
- Extracted prerequisite relations: 5
- Total valid transitions: 108
- Data density (item-level before processing): ~41%
- Data density after semantic aggregation (concept-level): ~83.75%

These metrics and thresholds are used in the project's validation and reported results; they are reproduced in `seminarski_rad.md`.

---

## Quick Start (Docker)

### Prerequisites

- Docker Desktop or Docker Engine
- Docker Compose (recommended)

```bash
git clone <repository-url>
cd knowledge-space-builder

docker compose up --build
```

**Services:**
- `frontend` → http://localhost:80
- `backend` → http://localhost:8000
- `celery_worker` → background tasks
- `postgres` → port 5432
- `redis` → port 6379

---

## Local Development

### Backend

```bash
cd backend

python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt

cp .env.example .env
alembic upgrade head

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

In a second terminal:

```bash
cd backend
.venv\Scripts\activate  # Windows
celery -A app.celery_app.celery_app worker --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Learning Space Generator (CLI)

```bash
cd learning_space_generator

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt

python app/main.py all
```

---

## API Documentation

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- OpenAPI JSON: http://localhost:8000/api/openapi.json

### Key Endpoints

- `POST /api/v1/analysis/run` – upload CSV (optional PDF) and start task.
- `GET /api/v1/analysis/{task_id}/status` – status and progress.
- `GET /api/v1/analysis/{task_id}/statistics` – aggregated metrics.
- `GET /api/v1/analysis/{task_id}/knowledge-space` – knowledge_space JSON.
- `GET /api/v1/analysis/{task_id}/visualization` – PNG visualization path.
- `GET /api/v1/analysis/{task_id}/files` – list output files.
- `GET /api/v1/analysis/{task_id}/download/{filename}` – download artifact.

---

## Configuration

### Backend `.env`

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/learning_space_db
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
STORAGE_PATH=storage
UPLOAD_PATH=storage/uploads
LSG_PATH=../learning_space_generator
LSG_OUTPUT_PATH=../learning_space_generator/output
```

### Frontend `.env`

```env
VITE_API_URL=http://localhost:8000/api/v1
```

### LSG Configuration

Key parameters live in `learning_space_generator/app/core/config.py` (random seed, DAE, IITA thresholds, LLM settings). `GITHUB_TOKEN` is optional and used for LLM classification.

---

## Testing

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test

# LSG
cd learning_space_generator
python -m pytest tests/
```

---

## Debugging and Operations

```bash
# Docker logs
docker compose logs -f backend
docker compose logs -f celery_worker

# Database shell
docker compose exec postgres psql -U postgres -d learning_space_db
```

---

## Repository Structure

```
knowledge-space-builder/
├── backend/                      # FastAPI + Celery
├── frontend/                     # React + TS UI
├── learning_space_generator/     # KST pipeline + semantic web
├── storage/                      # Uploads and storage
└── docker-compose.yml            # Multi-container orchestration
```

---

## References

1. Doignon, J. P., & Falmagne, J. C. (1999). *Knowledge Spaces*. Springer.
2. W3C: RDF 1.1, OWL 2, SPARQL 1.1
3. SOTIS Conference Proceedings – Semantic Technologies for Intelligent Learning Systems

---

## License

This project is developed for educational purposes in collaboration with **Pädagogischen Hochschule St.Gallen (PHSG)**.

---

## Authors

**SOTIS 2026 - Knowledge Space Builder Team**

Project 3 - Faculty of Technical Sciences, University of Novi Sad

---

## Support

For questions or issues, open a GitHub issue or contact the project team.

---

**Built with ❤️ using FastAPI, React, and PyTorch**
