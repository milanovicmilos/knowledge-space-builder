# API Test Scripts

Python skripte za testiranje svih API zahteva koje frontend šalje backend-u.

## Instalacija

```bash
pip install requests
```

## Testovi

### 1. Kompletan test workflow-a

Pokreće sve testove redom:
1. Upload CSV fajla
2. Praćenje progresa task-a
3. Preuzimanje rezultata
4. Preuzimanje statistike
5. Preuzimanje vizualizacije
6. Lista fajlova

```bash
python test_api.py
```

**Output:**
- ✓ Zelene poruke = uspešno
- ✗ Crvene poruke = greška
- ℹ Plave poruke = info
- ⚠ Žute poruke = upozorenje

### 2. Pojedinačni testovi

Za testiranje samo jednog endpointa:

```bash
# Upload CSV fajla
python test_individual.py upload ../data/COINS-alle-Cluster-CH.txt

# Provera statusa
python test_individual.py status 1

# Preuzimanje rezultata
python test_individual.py results 1

# Preuzimanje statistike
python test_individual.py statistics 1

# Preuzimanje vizualizacije
python test_individual.py visualization 1

# Lista fajlova
python test_individual.py files 1
```

## API Endpoints

### POST /api/v1/analysis/run
Upload CSV fajla i kreiranje task-a

**Request:**
- file: FormData sa CSV fajlom

**Response:**
```json
{
  "task_id": 1,
  "status": "pending",
  "progress": 0,
  "message": "Inicijalizujem analizu..."
}
```

### GET /api/v1/analysis/{task_id}/status
Provera statusa task-a (polling svake 1s)

**Response:**
```json
{
  "task_id": 1,
  "status": "running",
  "progress": 45,
  "message": "Aggregation stage...",
  "created_at": "2026-01-20T00:00:00",
  "started_at": "2026-01-20T00:00:01",
  "completed_at": null,
  "error_message": null
}
```

**Statusi:**
- `pending` - Task kreiran, čeka izvršavanje
- `running` - Task se izvršava (0-100%)
- `completed` - Task završen uspešno
- `failed` - Task neuspešan

### GET /api/v1/analysis/{task_id}/results
Preuzimanje svih rezultata (JSON fajlovi)

**Response:**
```json
{
  "task_id": 1,
  "status": "completed",
  "completed_at": "2026-01-20T00:05:00",
  "files": {
    "llm_item_classifications.json": {...},
    "knowledge_space.json": {...},
    "implications.json": {...},
    "semantic_clusters.json": {...}
  }
}
```

### GET /api/v1/analysis/{task_id}/statistics
Preuzimanje statistike

**Response:**
```json
{
  "task_id": 1,
  "status": "completed",
  "statistics": {
    "total_items": 150,
    "total_concepts": 45,
    "total_students": 2500,
    "knowledge_space_states": 89,
    "prerequisites_found": 234,
    "semantic_clusters": 12,
    "root_concepts": 5
  }
}
```

### GET /api/v1/analysis/{task_id}/visualization
Preuzimanje info o vizualizaciji (graph PNG)

**Response:**
```json
{
  "task_id": 1,
  "graph_file": "/app/learning_space_generator/output/knowledge_space_graph.png",
  "graph_exists": true
}
```

### GET /api/v1/analysis/{task_id}/files
Lista svih dostupnih fajlova

**Response:**
```json
{
  "task_id": 1,
  "total_files": 9,
  "files": [
    {
      "name": "llm_item_classifications.json",
      "size": 15360,
      "path": "/app/learning_space_generator/output/llm_item_classifications.json"
    },
    {
      "name": "knowledge_space.json",
      "size": 8192,
      "path": "/app/learning_space_generator/output/knowledge_space.json"
    }
  ]
}
```

## Workflow

Frontend šalje zahteve u sledećem redosledu:

```
1. Upload CSV → POST /run
   ↓
2. Poll status → GET /{task_id}/status (svake 1s)
   ↓ (dok status != 'completed')
3. Get statistics → GET /{task_id}/statistics
   ↓
4. Get visualization → GET /{task_id}/visualization
   ↓
5. Get results → GET /{task_id}/results
   ↓
6. List files → GET /{task_id}/files
```

## Troubleshooting

### Backend nije dostupan
```
ERROR: Backend nije dostupan!
⚠ Da li je Docker pokrenut? Komanda: docker compose up -d
```

**Rešenje:**
```bash
cd c:\Users\Milos\PythonProjects\knowledge-space-builder
docker compose up -d
```

### Task failed
```
✗ Task neuspešan!
  Error: File processing error
```

**Proveri logove:**
```bash
docker compose logs celery_worker --tail=50
docker compose logs backend --tail=50
```

### Upload failed (400/500)
```
✗ Upload failed: 400
  Response: {"detail": "Only CSV files are allowed"}
```

**Proveri:**
- Da li je fajl CSV format?
- Da li ima validne kolone (student_id, item_1, item_2, ...)?

## Test CSV Format

```csv
student_id,item_1,item_2,item_3,item_4,item_5
1,1,1,0,0,0
2,1,1,1,0,0
3,1,1,1,1,0
4,0,1,0,0,0
5,1,0,1,0,1
```

## Napomene

- Testovi automatski kreiraju test CSV fajl
- Backend mora biti pokrenut (docker compose up -d)
- PostgreSQL mora biti dostupan
- Celery worker mora biti pokrenut
- Redis mora biti pokrenut
