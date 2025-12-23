# Knowledge Space Builder

Full-stack application for constructing learning spaces from educational response patterns using NEAT evolutionary algorithm with automatic item clustering.

## Architecture

- **Backend**: FastAPI + PostgreSQL + Celery + Redis
- **Frontend**: React + TypeScript + Vite
- **Algorithm**: NEAT with missing-aware fitness evaluation
- **Deployment**: Docker Compose multi-container setup

## Features

- **CSV Upload**: Response pattern matrix ingestion
- **Background Processing**: Async task execution with Celery
- **Real-time Progress**: WebSocket-based live status updates
- **Item Clustering**: Automatic partitioning for large datasets (50+ items)
- **Missing Value Support**: Native handling of incomplete data
- **Graph Visualization**: Interactive learning space exploration
- **Export**: JSON and PNG output formats

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
cd learning-space-generator
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m lsg.run --help
```

## Usage Workflow

1. **Upload CSV**: Submit response pattern matrix (rows = students, columns = items)
2. **Configure**: Set NEAT parameters and clustering options
3. **Execute**: Launch background task
4. **Monitor**: Track real-time progress (clustering → evolution)
5. **Download**: Export learning space as JSON or PNG

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

JSON with original item IDs:
```json
{
  "∅": ["{M178832}"],
  "{M178832}": ["{M178832, M178357}"],
  "{M178832, M178357}": []
}
```

## API Endpoints

- `POST /api/v1/uploads/` - Upload CSV file
- `POST /api/v1/tasks/` - Create analysis task
- `GET /api/v1/tasks/{id}` - Get task status
- `GET /api/v1/results/{id}/download` - Download results

See full API docs at `/docs` when running.

## Configuration

**Backend** ([backend/app/config.py](backend/app/config.py)):
- Database connection
- Redis broker URL
- Storage paths

**NEAT** ([learning-space-generator/config/default.ini](learning-space-generator/config/default.ini)):
- Genome structure
- Mutation rates
- Fitness thresholds

## Project Structure

```
knowledge-space-builder/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── api/         # REST endpoints
│   │   ├── celery_app/  # Background tasks
│   │   ├── models/      # SQLAlchemy models
│   │   ├── schemas/     # Pydantic schemas
│   │   └── services/    # Business logic
│   └── Dockerfile
├── frontend/            # React application
│   ├── src/
│   │   ├── components/  # UI components
│   │   ├── api/         # API client
│   │   └── types/       # TypeScript types
│   └── Dockerfile
├── learning-space-generator/  # Core algorithm
│   ├── lsg/
│   │   ├── algorithms/  # NEAT implementation
│   │   ├── run.py       # CLI entry point
│   │   └── output_utils.py
│   └── config/          # NEAT configuration
└── docker-compose.yml   # Multi-container orchestration
```

## Algorithm Details

**NEAT (NeuroEvolution of Augmenting Topologies)**:
- Genome represents learning space as DAG
- Enforces closure under union constraint
- Evaluates fitness against observed patterns
- Supports missing values via mask arrays

**Item Clustering** (for 50+ items):
1. Pairwise item distance computation
2. Agglomerative hierarchical clustering
3. Silhouette analysis for optimal K
4. Independent NEAT execution per cluster
5. Result merging into unified space

## Contributing

1. Fork repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Open pull request

## License

MIT License - see LICENSE file

## References

- [Learning Spaces Theory](https://arxiv.org/abs/1511.06757)
- [NEAT Algorithm](http://nn.cs.utexas.edu/downloads/papers/stanley.ec02.pdf)
- [neat-python Documentation](https://neat-python.readthedocs.io/)
