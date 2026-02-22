# Knowledge Space Builder - SOTIS 2026

**Inteligentna platforma za konstruisanje, vizuelizaciju i analizu prostora znanja u matematičkom domenu, sa semantičkim web slojem za SOTIS integraciju.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.0-61DAFB.svg?logo=react)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6.svg?logo=typescript)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python)](https://www.python.org)

---

## Opis projekta

**Knowledge Space Builder** je celovita istraživačko-proizvodna aplikacija koja implementira **Teoriju Prostora Znanja (Knowledge Space Theory - KST)** u matematičkom domenu, uz semantičku anotaciju i RDF/OWL izvoz kompatibilan sa **SOTIS** platformom. Projekat je razvijen u saradnji sa **Pädagogischen Hochschule St.Gallen (PHSG)** i pokriva kompletan tok rada: od učitavanja realnih test podataka, preko konstrukcije prostora znanja, do pedagoške i semantičke analitike.

**Ciljevi (prema specifikaciji):**
- Konstrukcija i vizuelizacija prostora znanja nad realnim podacima iz testova matematike.
- Prilagođavanje algoritma konstrukcije prostora znanja i izgradnja aplikacije za upravljanje rezultatima.
- Kreiranje ontologije obrazovnih ciljeva za semantički web i SOTIS integraciju.

---

## Arhitektura sistema

![Sistemska arhitektura](diagram2.png)

### Komponente

1. **Frontend** (`frontend/`)
   - React 18 + TypeScript + Material-UI
   - Upload CSV datoteka, praćenje statusa, vizuelizacija i dashboard metrika.

2. **Backend** (`backend/`)
   - FastAPI + SQLAlchemy + Celery + Redis
   - Orkestrator: prima upload, inicira zadatke, čuva rezultate u PostgreSQL i izlaže REST API.

3. **Learning Space Generator (LSG)** (`learning_space_generator/`)
   - PyTorch + NetworkX + RDFLib + Sentence Transformers
   - Sadrži jezgro algoritma, validaciju, vizuelizaciju i ontologiju.

---

## Glavni tok podataka

1. **CSV/PDF upload** kroz UI ili API.
2. **Backend** čuva fajl i kreira zadatak u bazi.
3. **Celery** pokreće LSG pipeline direktnim Python importom.
4. **Rezultati** se zapisuju u `learning_space_generator/output/` i indeksiraju u bazi.
5. **Frontend** prikazuje statuse, grafove i semantičke rezultate.

Napomena: dijagram toka podataka je izdvojen (ubaci posebnu sliku kada bude dostupna).

---

## LSG pipeline (9 faza)

LSG pipeline izvodi se kao sekvencijalni niz od devet faza koji odgovara opisu u seminarskom radu.

1. **Priprema podataka** – inicijalne provere i ekstrakcija metapodataka.
2. **Popunjavanje i uklanjanje šuma** – DAE za popunjavanje nedostajućih odgovora i uklanjanje šuma.
3. **Semantička klasifikacija** – LLM klasifikacija i embeddings za grupisanje stavki u koncepte.
4. **Sažimanje na nivo koncepta** – agregacija odgovora sa stavke na koncept.
5. **Analiza zahtevnosti** – procena težine stavki i koncepta.
6. **Ekstrakcija strukture** – IITA za izdvajanje relacija preduslova.
7. **Generisanje prostora znanja** – generisanje validnih stanja znanja.
8. **Vizualizacija i validacija** – generisanje grafikona i validacija rezultata.
9. **Generisanje ontologije i čuvanje** – serijalizacija u RDF/OWL i čuvanje artefakata.

---

## Semantički web sloj

Semantički sloj generiše ontologiju obrazovnih ciljeva i veza između koncepata i stavki.

- **Format:** Turtle (`.ttl`) i OWL/XML
- **Output:** `learning_space_generator/output/sotis_ontology.ttl`
- **Vocabulary:** SOTIS namespace `http://www.sotis-conference.org/ontology#`

### Semantički API (backend)
- `GET /api/v1/analysis/{task_id}/goals` – lista learning goals iz ontologije.
- `GET /api/v1/analysis/{task_id}/goal-path?goal_id=...` – preporučeni učni put baziran na prerequisitima.

---

## Format ulaznih podataka

CSV format je prilagođen realnim test podacima.

- Separator je `;`.
- Stavke su kolone koje počinju sa `s` (osim `standort`).
- Vrednosti: `1` tačan, `0` netačan odgovor.
- `9999` i `666` se tretiraju kao nedostajuće vrednosti.

---

## Output fajlovi

LSG generiše artefakte u `learning_space_generator/output/`:

- `cleaned_responses.csv`
- `aggregated_concepts.csv`
- `aggregated_concepts_binary.csv`
- `item_difficulties.json`
- `concepts_sorted_by_difficulty.json`
- `implications.json`
- `knowledge_space.json`
- `knowledge_structure_graph.png`
- `sotis_ontology.ttl`

## Rezime evaluacije

Ključni metrički podaci iz seminarskog rada i referentne analize:

- Skup podataka: 692 studenta, 121 stavka
- Broj semantičkih koncepata (finalni model): 7
- Generisana stanja znanja: 44
- Ekstrahovane relacije preduslova: 5
- Ukupno validnih tranzicija: 108
- Gustina podataka (stavke, pre obrade): ~41%
- Gustina podataka nakon semantičke agregacije (koncepti): ~83.75%

Ovi rezultati i pragovi su dokumentovani u `seminarski_rad.md`.

---

## Quick start (Docker)

### Preduslovi

- Docker Desktop ili Docker Engine
- Docker Compose (preporučeni način)

```bash
git clone <repository-url>
cd knowledge-space-builder

docker compose up --build
```

**Servisi:**
- `frontend` → http://localhost:80
- `backend` → http://localhost:8000
- `celery_worker` → background tasks
- `postgres` → port 5432
- `redis` → port 6379

---

## Lokalni development

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

U drugom terminalu:

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

## API dokumentacija

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- OpenAPI JSON: http://localhost:8000/api/openapi.json

### Najvažniji endpoint-i

- `POST /api/v1/analysis/run` – upload CSV (opciono PDF) i start zadatka.
- `GET /api/v1/analysis/{task_id}/status` – status i progres.
- `GET /api/v1/analysis/{task_id}/statistics` – agregirane metrike.
- `GET /api/v1/analysis/{task_id}/knowledge-space` – knowledge_space JSON.
- `GET /api/v1/analysis/{task_id}/visualization` – putanja do PNG vizualizacije.
- `GET /api/v1/analysis/{task_id}/files` – lista svih output fajlova.
- `GET /api/v1/analysis/{task_id}/download/{filename}` – preuzimanje fajla.

---

## Konfiguracija

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

### LSG konfiguracija

Ključni parametri su u `learning_space_generator/app/core/config.py` (random seed, DAE, IITA pragovi, LLM podešavanja). `GITHUB_TOKEN` je opcionalan i koristi se za LLM klasifikaciju.

---

## Testiranje

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

## Debugging i operacije

```bash
# Docker logs
docker compose logs -f backend
docker compose logs -f celery_worker

# Database shell
docker compose exec postgres psql -U postgres -d learning_space_db
```

---

## Struktura repozitorijuma

```
knowledge-space-builder/
├── backend/                      # FastAPI + Celery
├── frontend/                     # React + TS UI
├── learning_space_generator/     # KST pipeline + semantic web
├── storage/                      # Uploads i storage
└── docker-compose.yml            # Multi-container orkestracija
```

---

## Literatura i reference

1. Doignon, J. P., & Falmagne, J. C. (1999). *Knowledge Spaces*. Springer.
2. W3C: RDF 1.1, OWL 2, SPARQL 1.1
3. SOTIS Conference Proceedings – Semantic Technologies for Intelligent Learning Systems

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
