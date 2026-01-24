# Knowledge Space Builder - SOTIS 2026

**Inteligentna platforma za konstruisanje, vizuelizaciju i analizu prostora znanja u matematičkom domenu**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.0-61DAFB.svg?logo=react)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6.svg?logo=typescript)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python)](https://www.python.org)

---

## 📚 Opis projekta

**Knowledge Space Builder** je kompleksna web aplikacija koja implementira **Teoriju Prostora Znanja (Knowledge Space Theory - KST)** iz oblasti matematičke psihologije. Projekat je razvijen u saradnji sa **Pädagogischen Hochschule St.Gallen (PHSG)** i integriše se sa **SOTIS** platformom za pravljenje inteligentnih tutora.

### 🎯 Ključne funkcionalnosti

- 🧠 **Neuroevolutivni algoritam** za konstrukciju prostora znanja
- 📊 **Analiza realnih test podataka** iz matematike
- 🔬 **Semantička klasifikacija** pomoću LLM-a i embeddings
- 📈 **Vizuelizacija prostora znanja** sa interaktivnim grafovima
- 🌐 **RDF/OWL ontologija** za semantički web (SOTIS integracija)
- 🎓 **Pedagoška analiza** i analiza težine koncepata
- ⚡ **Asinhrono procesiranje** sa real-time progress tracking
- 🐳 **Docker deployment** sa potpunom kontejnerizacijom

---

## 🏗️ Arhitektura

Projekat je organizovan kao **microservices arhitektura** sa tri glavne komponente:

```
┌─────────────────┐      ┌─────────────────┐      ┌──────────────────────┐
│                 │      │                 │      │                      │
│    Frontend     │◄────►│     Backend     │◄────►│  Learning Space      │
│  React + TS     │      │   FastAPI       │      │  Generator (LSG)     │
│                 │      │   + Celery      │      │  Core Algorithm      │
└─────────────────┘      └─────────────────┘      └──────────────────────┘
        │                        │                           │
        │                        │                           │
        ▼                        ▼                           ▼
   Nginx Static           PostgreSQL                  Python Services
                          + Redis                     (10 modules)
```

### **1. Frontend** (`frontend/`)
- **Stack:** React 18 + TypeScript + Material-UI
- **Vizualizacija:** ReactFlow za interaktivne grafove prostora znanja
- **Funkcionalnosti:**
  - Upload CSV podataka
  - Real-time progress monitoring
  - Interaktivna vizualizacija rezultata
  - Dashboard sa statistikama i metrikama

### **2. Backend** (`backend/`)
- **Stack:** FastAPI + SQLAlchemy + Celery + Redis
- **Uloga:** REST API most između frontend-a i LSG algoritma
- **Funkcionalnosti:**
  - Upravljanje upload-ima i task-ovima
  - Asinkrono izvršavanje LSG-a preko Celery tasks-a
  - Perzistencija rezultata u PostgreSQL
  - Real-time progress updates

### **3. Learning Space Generator** (`learning_space_generator/`)
- **Stack:** PyTorch + NetworkX + RDFLib + Sentence Transformers
- **Uloga:** Core algoritam za konstrukciju prostora znanja
- **Pipeline** (7 koraka):
  1. **Preprocessing** - DAE (Denoising Autoencoder)
  2. **Semantic Clustering** - LLM klasifikacija + embeddings
  3. **Concept Aggregation** - Grupacija items → concepts
  4. **Difficulty Analysis** - Sortiranje po težini
  5. **Structure Extraction** - IITA algoritam za prerequisite odnose
  6. **Knowledge Space Generation** - Generisanje validnih knowledge states
  7. **Ontology Export** - RDF/OWL export za semantički web

---

## 🚀 Quick Start

### Preduslovi

- **Docker** i **Docker Compose** (preporučeno)
- ili **Python 3.11+** i **Node.js 18+** za lokalni development

### 🐳 Docker Deployment (Najlakši način)

```bash
# 1. Kloniraj projekat
git clone <repository-url>
cd knowledge-space-builder

# 2. Pokreni sve servise
docker compose up --build

# 3. Aplikacija je dostupna na:
#    - Frontend: http://localhost:80
#    - Backend API: http://localhost:8000
#    - API Docs: http://localhost:8000/api/docs
```

**Servisi:**
- `frontend` → http://localhost:80
- `backend` → http://localhost:8000
- `celery_worker` → Background tasks
- `postgres` → Database (port 5432)
- `redis` → Message broker (port 6379)

---

## 💻 Lokalni Development

### Backend Setup

```bash
cd backend

# Kreiraj virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Instaliraj dependencies
pip install -r requirements.txt

# Setup .env fajl
cp .env.example .env
# Konfiguriši DATABASE_URL, REDIS_URL, itd.

# Pokreni migracije
alembic upgrade head

# Pokreni FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# U drugom terminalu: Pokreni Celery worker
celery -A app.celery_app.celery_app worker --loglevel=info
```

### Frontend Setup

```bash
cd frontend

# Instaliraj dependencies
npm install

# Pokreni development server
npm run dev

# Aplikacija dostupna na http://localhost:5173
```

### Learning Space Generator Setup

```bash
cd learning_space_generator

# Kreiraj virtual environment
python -m venv .venv
.venv\Scripts\activate

# Instaliraj dependencies
pip install -r requirements.txt

# Testiraj pipeline
python app/main.py all
```

---

## 📂 Struktura projekta

```
knowledge-space-builder/
│
├── backend/                      # FastAPI Backend
│   ├── app/
│   │   ├── api/v1/              # REST API endpoints
│   │   │   └── endpoints/
│   │   │       └── analysis.py  # Main API: upload, status, results
│   │   ├── celery_app/          # Async task processing
│   │   │   └── tasks.py         # Celery task: run LSG
│   │   ├── models/              # SQLAlchemy models
│   │   │   ├── upload.py        # Upload tracking
│   │   │   ├── task.py          # Task execution tracking
│   │   │   └── result.py        # Results storage
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── config.py            # Application settings
│   │   ├── database.py          # DB connection
│   │   └── main.py              # FastAPI app initialization
│   ├── alembic/                 # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                     # React Frontend
│   ├── src/
│   │   ├── components/          # React components
│   │   │   ├── Home.tsx         # Landing page
│   │   │   ├── UploadForm.tsx   # CSV upload
│   │   │   ├── ProgressMonitor.tsx  # Real-time tracking
│   │   │   ├── ResultsDashboard.tsx # Results display
│   │   │   ├── KnowledgeSpaceGraph.tsx  # Graph visualization
│   │   │   └── TaskHistory.tsx  # Task management
│   │   ├── api/                 # API client
│   │   ├── utils/               # Utilities
│   │   ├── types/               # TypeScript type definitions
│   │   └── App.tsx              # Main app
│   ├── package.json
│   └── Dockerfile
│
├── learning_space_generator/    # Core Algorithm
│   ├── app/
│   │   ├── services/            # 10 business logic services
│   │   │   ├── preprocessing_service.py    # DAE preprocessing
│   │   │   ├── semantic_service.py         # LLM + embeddings
│   │   │   ├── concept_aggregation_service.py  # Items → Concepts
│   │   │   ├── difficulty_service.py       # Difficulty analysis
│   │   │   ├── structure_service.py        # IITA algorithm
│   │   │   ├── knowledge_space_service.py  # State generation
│   │   │   ├── visualization_service.py    # Graph generation
│   │   │   ├── validation_service.py       # Result validation
│   │   │   └── ontology_service.py         # RDF/OWL export
│   │   ├── core/                # Configuration
│   │   ├── models/              # Data models
│   │   ├── utils/               # Helper functions
│   │   └── main.py              # CLI entry point
│   ├── data/                    # Input CSV files
│   ├── output/                  # Generated results
│   ├── notebooks/               # Research notebooks
│   ├── scripts/                 # Utility scripts
│   ├── tests/                   # Test files
│   └── requirements.txt
│
├── storage/                      # Persistent storage
│   └── uploads/                 # Uploaded CSV files
│
├── docker-compose.yml            # Multi-container orchestration
└── README.md                     # This file
```

---

## 📊 API Dokumentacija

Backend pruža RESTful API sa automatski generisanom OpenAPI/Swagger dokumentacijom.

**📖 Pristup dokumentaciji:**
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- OpenAPI JSON: http://localhost:8000/api/openapi.json

### Ključni API Endpoints

#### **POST** `/api/v1/analysis/run`
Upload CSV fajla i pokreni analizu prostora znanja.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/analysis/run" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test_data.csv"
```

**Response:**
```json
{
  "task_id": "12345",
  "upload_id": "67890",
  "status": "pending",
  "message": "Task created successfully"
}
```

#### **GET** `/api/v1/analysis/status/{task_id}`
Proveri status izvršavanja task-a (real-time progress).

**Response:**
```json
{
  "task_id": 12345,
  "status": "running",
  "progress": 65,
  "message": "IITA prerequisite extraction...",
  "started_at": "2026-01-24T10:30:00",
  "completed_at": null
}
```

#### **GET** `/api/v1/analysis/results/{task_id}`
Preuzmi rezultate analize.

**Response:**
```json
{
  "task_id": 12345,
  "statistics": {
    "total_items": 50,
    "total_concepts": 12,
    "knowledge_space_states": 187,
    "prerequisites_found": 28
  },
  "knowledge_space": [...],
  "implications": {...},
  "ontology_url": "/api/v1/analysis/download/ontology/12345"
}
```

---

## 🧪 Testiranje

```bash
# Backend unit tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# LSG integration tests
cd learning_space_generator
python -m pytest tests/
```

---

## 🔧 Konfiguracija

### Backend Environment Variables (`.env`)

```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/learning_space_db

# Redis
REDIS_URL=redis://localhost:6379/0

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Storage paths
STORAGE_PATH=storage
UPLOAD_PATH=storage/uploads

# LSG paths
LSG_PATH=../learning_space_generator
LSG_OUTPUT_PATH=../learning_space_generator/output
```

### Frontend Environment Variables (`.env`)

```env
VITE_API_URL=http://localhost:8000/api/v1
```

---

## 🐛 Debugging

### Backend logs
```bash
# Docker
docker compose logs -f backend

# Local
uvicorn app.main:app --reload --log-level debug
```

### Celery worker logs
```bash
# Docker
docker compose logs -f celery_worker

# Local
celery -A app.celery_app.celery_app worker --loglevel=debug
```

### Database inspect
```bash
docker compose exec postgres psql -U postgres -d learning_space_db
```

---

## 🤝 SOTIS Integracija

Projekat generiše **RDF/OWL ontologiju** u formatu kompatibilnom sa **SOTIS** platformom:

- **Format:** Turtle (`.ttl`)
- **Vocabularies:** SKOS, Dublin Core
- **Output:** `learning_space_generator/output/sotis_ontology.ttl`

**Ontologija sadrži:**
- Obrazovne ciljeve (learning objectives)
- Prerequisite odnose između koncepata
- Metapodatke o težini i semantičkoj sličnosti
- Mapiranje learning objekta na koncepte

---

## 📜 Licenca

Ovaj projekat je razvijen u edukativne svrhe u saradnji sa **Pädagogischen Hochschule St.Gallen (PHSG)**.

---

## 👥 Autori

**SOTIS 2026 - Knowledge Space Builder Team**

Projekat 3 - Fakultet tehničkih nauka, Univerzitet u Novom Sadu

---

## 📞 Podrška

Za pitanja i probleme, otvorite issue na GitHub-u ili kontaktirajte projektni tim.

---

**Built with ❤️ using FastAPI, React, and PyTorch**
