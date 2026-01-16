# Knowledge Space Builder

Full-stack application for generating knowledge spaces from educational response patterns using **MIRT-VAE** (Multidimensional Item Response Theory - Variational Autoencoder).

## Architecture

- **Backend**: FastAPI + PostgreSQL + Celery + Redis
- **Frontend**: React + TypeScript + Vite + React Flow
- **Algorithm**: MIRT-VAE + Prerequisite Inference + Lattice Construction
- **Deployment**: Docker Compose multi-container setup

## Features

- **CSV Upload**: Response pattern matrix ingestion (students × items)
- **MIRT-VAE Training**: Deep learning-based latent knowledge representation
- **Prerequisite Inference**: Automatic discovery of item dependencies
- **Knowledge Space Generation**: Lattice construction from prerequisite DAG
- **Background Processing**: Async task execution with Celery workers
- **Real-time Progress**: Live status updates during training and building
- **Graph Visualization**: Interactive knowledge space exploration with React Flow
- **Export**: JSON output with lattice structure and statistics

## Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+

### Running with Docker

```bash
# Start all services
docker compose up --build

# Access application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

### Development Setup

**Backend:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Learning Space Generator:**
```bash
cd learning_space_generator
pip install -r requirements.txt
python -m learning_space_generator.cli.main --help
```

### Running Locally (CLI)

For best results, use the optimization pipeline which automatically tunes hyperparameters:

```bash
# Activate virtual environment
.venv\Scripts\activate

# Run full optimization pipeline (Optimize -> Build -> Evaluate)
python -m learning_space_generator.cli.optimize full \
  --csv learning_space_generator/data/ResponsePatterns_Stellwerk_Math_2018-2024(in).csv \
  --out_dir learning_space_generator/output \
  --n_trials 3
```

- **Output**: `learning_space_generator/output/knowledge_space_lattice_k30.json`
- **Visualization**: `learning_space_generator/output/knowledge_space_lattice_k30.png`
- **Report**: `learning_space_generator/output/quality_report.json`

## Usage Workflow

1. **Upload CSV**: Submit response pattern matrix (rows = students, columns = items)
2. **Configure Parameters**: 
   - MIRT-VAE: epochs, latent_dim
   - Lattice: select_k, min_support, implication_threshold
3. **Execute**: Launch background Celery task
4. **Monitor**: Track real-time progress (training → prerequisite inference → lattice construction)
5. **View Results**: Explore knowledge space graph in React Flow visualization

### Input Format

CSV with binary values:
- `1` = correct answer
- `0` = incorrect answer
- `-` or empty = missing value

Example:
```csv
M178832,M178357,M176963
1,0,1
-,1,0
1,1,1
```

### Output Format

**knowledge_space_lattice.json**:
```json
{
  "states": [
    {"id": 0, "items": [], "label": "{}"},
    {"id": 1, "items": ["M178832"], "label": "{M178832}"},
    {"id": 2, "items": ["M178832", "M178357"], "label": "{M178832, M178357}"}
  ],
  "edges": [
    {"from": 0, "to": 1, "label": "M178832"},
    {"from": 1, "to": 2, "label": "M178357"}
  ]
}
```

## API Endpoints

- `POST /api/v1/uploads/upload` - Upload CSV file
- `POST /api/v1/tasks/tasks` - Create MIRT-VAE task
- `GET /api/v1/tasks/tasks/{id}` - Get task status and progress
- `GET /api/v1/results/{task_id}` - Get results and download JSON

See full API docs at `http://localhost:8000/docs` when running.

## Configuration

**Backend** ([backend/app/config.py](backend/app/config.py)):
- Database connection (PostgreSQL)
- Redis broker URL
- Storage paths for CSV uploads and outputs

**Default Parameters**:
- MIRT-VAE: `epochs=8, latent_dim=10, batch_size=1024`
- Prerequisite: `pred_threshold=0.6, implication_threshold=0.85`
- Lattice: `select_k=30, min_support=7`

## Project Structure

```
knowledge-space-builder/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/v1/            # REST endpoints (uploads, tasks, results)
│   │   ├── celery_app/        # Background Celery tasks
│   │   ├── models/            # SQLAlchemy models (Upload, Task, Result)
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   └── services/          # Storage service
│   ├── requirements.txt       # Backend dependencies
│   ├── lsg_requirements.txt   # Learning space generator dependencies
│   └── Dockerfile
├── frontend/                   # React application
│   ├── src/
│   │   ├── components/        # UI components (TaskForm, ResultsPanel, GraphVisualization)
│   │   ├── api/              # Axios API client
│   │   └── types/            # TypeScript interfaces
│   └── Dockerfile
├── learning_space_generator/   # MIRT-VAE core algorithm
│   ├── infrastructure/        # Neural network, training, data loading
│   ├── domain/services/       # Prerequisite inference, lattice construction
│   ├── application/           # Pipeline orchestrator
│   ├── cli/                   # Command-line interface (train, build)
│   └── requirements.txt
└── docker-compose.yml         # Multi-container orchestration
```

## Algorithm Details

### MIRT-VAE (Multidimensional Item Response Theory - VAE)

**Architecture**:
- **Encoder**: Response patterns (121 items) → hidden layer (128) → latent (10 dims)
- **Decoder**: Latent vector (10) → discrimination matrix (121×10) + bias → logits
- **Loss**: BCE(reconstruction) + β×KL(latent || N(0,1)) where β=0.001

**Training**:
- Optimizer: Adam with lr=1e-3
- Batch size: 1024
- Epochs: 8 (adjustable)
- Output: Predicted probabilities matrix (N_students × N_items)

### Prerequisite Inference

For each item pair (A, B):
```
P(knows A | knows B) = (students_know_both) / (students_know_B)

If P(A|B) ≥ implication_threshold (0.85):
    Add edge A → B  (A is prerequisite for B)
```

Creates prerequisite DAG with transitive reduction.

### Lattice Construction

1. **Item Selection**: Select top-k items by degree (in+out), expand to ancestors
2. **Ideal Generation**: Generate all closed sets respecting prerequisite order
3. **Empirical Filtering**: Count state frequencies in binarized predictions, filter by min_support
4. **Poset Building**: Construct Hasse diagram (cover relations) from valid states

## Contributing

1. Fork repository
2. Create feature branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -m 'Add feature'`)
4. Push to branch (`git push origin feature/improvement`)
5. Open pull request

## References

- Doignon, J.-P., & Falmagne, J.-C. (1999). *Knowledge Spaces*. Springer.
- Kingma, D. P., & Welling, M. (2014). *Auto-Encoding Variational Bayes*. ICLR.
- Reckase, M. D. (2009). *Multidimensional Item Response Theory*. Springer.
