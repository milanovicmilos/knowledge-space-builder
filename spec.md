# Learning Space Generator - AWS Free Tier Deployment Specification

## 📋 Overview

Kompletna web aplikacija za generisanje learning space-ova sa:
- CSV upload
- Matrix completion (ALS)
- NEAT algoritam background processing
- Interaktivna vizualizacija grafa
- **100% AWS Free Tier** za prvih 12 meseci

---

## 🎯 Tech Stack

| Component | Technology | Razlog |
|-----------|-----------|--------|
| **Backend** | FastAPI | Async, brz, Python-native |
| **Task Queue** | Celery + Redis | Background processing za NEAT |
| **Database** | PostgreSQL (RDS) | Relational, Free Tier 20GB |
| **Storage** | S3 | CSV uploads, JSON results, Free 5GB |
| **Frontend** | React + Vite + TypeScript | Moderan, brz build |
| **Graph Viz** | Cytoscape.js | Interactive graph rendering |
| **Proxy** | Nginx | Reverse proxy + static files |
| **Hosting** | EC2 t2.micro | Free Tier 750h/mesec |
| **CDN** | CloudFront | Frontend delivery, Free 1TB |

---

## 📁 Project Structure

```
knowledge-space-builder/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app
│   │   ├── config.py                  # Settings (env vars)
│   │   ├── database.py                # SQLAlchemy setup
│   │   ├── dependencies.py            # FastAPI dependencies
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── upload.py              # Upload model
│   │   │   ├── task.py                # Task model
│   │   │   └── result.py              # Result model
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── upload.py              # Pydantic schemas
│   │   │   ├── task.py
│   │   │   └── result.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── endpoints/
│   │   │       │   ├── uploads.py     # POST /upload, GET /uploads
│   │   │       │   ├── tasks.py       # POST /tasks, GET /tasks/{id}
│   │   │       │   └── results.py     # GET /results/{task_id}
│   │   │       └── router.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── s3.py                  # S3 upload/download
│   │   │   ├── upload_service.py
│   │   │   └── task_service.py
│   │   └── celery_app/
│   │       ├── __init__.py
│   │       ├── celery_config.py
│   │       └── tasks.py               # NEAT execution task
│   ├── alembic/                       # Database migrations
│   │   ├── versions/
│   │   └── env.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Upload/
│   │   │   │   ├── UploadForm.tsx
│   │   │   │   └── UploadList.tsx
│   │   │   ├── Parameters/
│   │   │   │   └── NEATParameters.tsx
│   │   │   ├── Task/
│   │   │   │   ├── TaskStatus.tsx
│   │   │   │   └── TaskList.tsx
│   │   │   └── Graph/
│   │   │       ├── GraphViewer.tsx    # Cytoscape
│   │   │       └── GraphStats.tsx
│   │   ├── api/
│   │   │   └── client.ts              # Axios API calls
│   │   ├── hooks/
│   │   │   ├── useUpload.ts
│   │   │   ├── useTask.ts
│   │   │   └── usePolling.ts
│   │   ├── types/
│   │   │   └── api.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── Dockerfile
├── nginx/
│   └── nginx.conf
├── learning-space-generator/          # Existing NEAT code
│   └── lsg/                           # Keep as is
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
└── README.md
```

---

## 🗄️ Database Schema

### PostgreSQL Tables

```sql
-- users table (optional, ako dodaš auth kasnije)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- uploads table
CREATE TABLE uploads (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    s3_key VARCHAR(500) NOT NULL UNIQUE,
    file_size_bytes BIGINT NOT NULL,
    num_rows INTEGER,
    num_columns INTEGER,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_uploads (user_id, uploaded_at DESC)
);

-- tasks table
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    upload_id INTEGER NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
        -- pending, running, completed, failed, cancelled
    celery_task_id VARCHAR(255) UNIQUE,
    parameters JSONB NOT NULL,
        -- {generations, als_rank, min_coverage, use_matrix_completion, ...}
    progress_percent INTEGER DEFAULT 0,
    current_generation INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    INDEX idx_task_status (status, created_at DESC),
    INDEX idx_celery_task (celery_task_id)
);

-- results table
CREATE TABLE results (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL UNIQUE REFERENCES tasks(id) ON DELETE CASCADE,
    graph_s3_key VARCHAR(500) NOT NULL,
    num_states INTEGER NOT NULL,
    num_edges INTEGER NOT NULL,
    discrepancy DOUBLE PRECISION NOT NULL,
    is_valid BOOLEAN NOT NULL,
    final_generation INTEGER,
    execution_time_seconds INTEGER,
    metadata JSONB,
        -- {unique_patterns, pattern_length, coverage_stats, ...}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- indexes for performance
CREATE INDEX idx_results_task ON results(task_id);
CREATE INDEX idx_results_created ON results(created_at DESC);
```

---

## 🔧 Implementation Steps

### **Phase 1: Local Development Setup** (Dan 1-2)

#### Step 1.1: Backend Setup

```bash
# 1. Create backend directory structure
cd knowledge-space-builder
mkdir -p backend/app/{models,schemas,api/v1/endpoints,services,celery_app}
mkdir -p backend/alembic/versions

# 2. Create requirements.txt
cat > backend/requirements.txt << 'EOF'
# FastAPI
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Database
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.12.1

# Celery + Redis
celery==5.3.4
redis==5.0.1

# AWS
boto3==1.29.7

# Validation
pydantic==2.5.0
pydantic-settings==2.1.0

# Utilities
python-dotenv==1.0.0

# NEAT dependencies (from learning-space-generator)
neat-python==0.92
numpy>=1.21.0
pandas>=1.3.0
scipy>=1.7.0
bitarray==0.8.3
tqdm==4.31.1
EOF

# 3. Create .env.example
cat > backend/.env.example << 'EOF'
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/learning_space_db

# Redis
REDIS_URL=redis://localhost:6379/0

# AWS S3
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=learning-space-uploads

# App
DEBUG=True
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
EOF

# 4. Install dependencies
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Step 1.2: Database Models

**backend/app/models/upload.py:**
```python
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class Upload(Base):
    __tablename__ = "uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    s3_key = Column(String(500), nullable=False, unique=True)
    file_size_bytes = Column(BigInteger, nullable=False)
    num_rows = Column(Integer)
    num_columns = Column(Integer)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
```

**backend/app/models/task.py:**
```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from app.database import Base

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    celery_task_id = Column(String(255), unique=True)
    parameters = Column(JSON, nullable=False)
    progress_percent = Column(Integer, default=0)
    current_generation = Column(Integer)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
```

**backend/app/models/result.py:**
```python
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.database import Base

class Result(Base):
    __tablename__ = "results"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), unique=True, nullable=False)
    graph_s3_key = Column(String(500), nullable=False)
    num_states = Column(Integer, nullable=False)
    num_edges = Column(Integer, nullable=False)
    discrepancy = Column(Float, nullable=False)
    is_valid = Column(Boolean, nullable=False)
    final_generation = Column(Integer)
    execution_time_seconds = Column(Integer)
    metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

#### Step 1.3: FastAPI Endpoints

**backend/app/api/v1/endpoints/uploads.py:**
```python
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.s3 import upload_to_s3
from app.models.upload import Upload
import pandas as pd
import io

router = APIRouter()

@router.post("/upload")
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Validate CSV
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, "Only CSV files allowed")
    
    # Read CSV metadata
    content = await file.read()
    df = pd.read_csv(io.BytesIO(content))
    
    # Upload to S3
    s3_key = f"uploads/{uuid.uuid4()}/{file.filename}"
    upload_to_s3(content, s3_key)
    
    # Save to DB
    upload = Upload(
        filename=file.filename,
        original_filename=file.filename,
        s3_key=s3_key,
        file_size_bytes=len(content),
        num_rows=len(df),
        num_columns=len(df.columns)
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    
    return {"upload_id": upload.id, "rows": upload.num_rows, "columns": upload.num_columns}

@router.get("/uploads")
async def list_uploads(db: Session = Depends(get_db)):
    uploads = db.query(Upload).order_by(Upload.uploaded_at.desc()).limit(50).all()
    return uploads
```

**backend/app/api/v1/endpoints/tasks.py:**
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.celery_app.tasks import run_neat_task
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskResponse

router = APIRouter()

@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db)
):
    # Create task record
    task = Task(
        upload_id=task_data.upload_id,
        parameters=task_data.parameters.dict(),
        status="pending"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Start Celery task
    celery_task = run_neat_task.delay(task.id, task_data.upload_id, task_data.parameters.dict())
    
    # Update with Celery task ID
    task.celery_task_id = celery_task.id
    db.commit()
    
    return task

@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    return task
```

#### Step 1.4: Celery Worker

**backend/app/celery_app/tasks.py:**
```python
from celery import Task
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.task import Task as TaskModel
from app.models.result import Result
from app.services.s3 import download_from_s3, upload_to_s3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../learning-space-generator'))

from lsg.run import load_response_patterns, run_neat
import tempfile
import time

@celery_app.task(bind=True)
def run_neat_task(self, task_id: int, upload_id: int, parameters: dict):
    db = SessionLocal()
    
    try:
        # Update status
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        task.status = "running"
        task.started_at = func.now()
        db.commit()
        
        # Download CSV from S3
        upload = db.query(Upload).filter(Upload.id == upload_id).first()
        csv_content = download_from_s3(upload.s3_key)
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
            tmp.write(csv_content)
            tmp_path = tmp.name
        
        # Run NEAT
        start_time = time.time()
        
        response_patterns, metadata = load_response_patterns(
            path=tmp_path,
            knowledge_items=parameters.get('knowledge_items'),
            min_coverage=parameters.get('min_coverage', 0.0),
            use_matrix_completion=parameters.get('use_matrix_completion', True),
            als_rank=parameters.get('als_rank', 30),
            als_iterations=parameters.get('als_iterations', 30)
        )
        
        # Progress callback (update every 5 generations)
        def progress_callback(gen, total):
            if gen % 5 == 0:
                self.update_state(
                    state='PROGRESS',
                    meta={'percent': int(100 * gen / total), 'generation': gen}
                )
        
        optimal_ls = run_neat(
            generations=parameters.get('generations', 50),
            config_filename='learning-space-generator/config/default.ini',
            responses=response_patterns,
            early_stopping_patience=parameters.get('patience', 20),
            verbose=True,
            parallel=True
        )
        
        execution_time = int(time.time() - start_time)
        
        # Save graph to S3
        graph_json = optimal_ls.to_json()
        graph_s3_key = f"results/{task_id}/learning_space.json"
        upload_to_s3(graph_json, graph_s3_key)
        
        # Save result
        num_states, num_edges = optimal_ls.size()
        result = Result(
            task_id=task_id,
            graph_s3_key=graph_s3_key,
            num_states=num_states,
            num_edges=num_edges,
            discrepancy=optimal_ls.discrepancy(),
            is_valid=optimal_ls.is_valid(),
            execution_time_seconds=execution_time,
            metadata=metadata
        )
        db.add(result)
        
        # Update task
        task.status = "completed"
        task.completed_at = func.now()
        task.progress_percent = 100
        db.commit()
        
        os.unlink(tmp_path)
        
        return {"result_id": result.id}
        
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        task.completed_at = func.now()
        db.commit()
        raise
    finally:
        db.close()
```

---

### **Phase 2: Frontend Development** (Dan 3-4)

#### Step 2.1: React Setup

```bash
# Create React app with Vite
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install

# Install dependencies
npm install axios react-router-dom @tanstack/react-query
npm install cytoscape cytoscape-dagre
npm install @types/cytoscape
npm install tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

#### Step 2.2: Key Components

**frontend/src/components/Upload/UploadForm.tsx:**
```tsx
import { useState } from 'react';
import { useUpload } from '../../hooks/useUpload';

export const UploadForm = () => {
  const [file, setFile] = useState<File | null>(null);
  const { upload, isLoading } = useUpload();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    
    const result = await upload(file);
    // Redirect to parameters page with upload_id
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="file"
        accept=".csv"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <button disabled={!file || isLoading}>
        {isLoading ? 'Uploading...' : 'Upload CSV'}
      </button>
    </form>
  );
};
```

**frontend/src/components/Graph/GraphViewer.tsx:**
```tsx
import { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';

cytoscape.use(dagre);

interface GraphViewerProps {
  graphData: {
    nodes: Array<{id: string, label: string}>;
    edges: Array<{source: string, target: string}>;
  };
}

export const GraphViewer = ({ graphData }: GraphViewerProps) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || !graphData) return;

    const cy = cytoscape({
      container: containerRef.current,
      elements: {
        nodes: graphData.nodes.map(n => ({ data: n })),
        edges: graphData.edges.map(e => ({ data: e }))
      },
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'background-color': '#3b82f6',
            'color': '#fff',
            'text-valign': 'center',
            'width': 60,
            'height': 60
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#94a3b8',
            'target-arrow-color': '#94a3b8',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier'
          }
        }
      ],
      layout: {
        name: 'dagre',
        rankDir: 'TB'
      }
    });

    return () => cy.destroy();
  }, [graphData]);

  return <div ref={containerRef} className="w-full h-[600px]" />;
};
```

---

### **Phase 3: AWS Infrastructure Setup** (Dan 5-6)

#### Step 3.1: Create AWS Account & Setup

1. **Sign up for AWS Free Tier**: https://aws.amazon.com/free/
2. **Setup IAM User:**
   ```bash
   # Install AWS CLI
   # Windows: https://aws.amazon.com/cli/
   
   # Configure credentials
   aws configure
   # Enter: Access Key ID, Secret Access Key, Region (us-east-1)
   ```

3. **Create S3 Bucket:**
   ```bash
   aws s3 mb s3://learning-space-uploads-YOURNAME
   
   # Enable CORS
   cat > cors.json << 'EOF'
   {
     "CORSRules": [{
       "AllowedOrigins": ["*"],
       "AllowedMethods": ["GET", "PUT", "POST"],
       "AllowedHeaders": ["*"],
       "MaxAgeSeconds": 3000
     }]
   }
   EOF
   
   aws s3api put-bucket-cors --bucket learning-space-uploads-YOURNAME --cors-configuration file://cors.json
   ```

#### Step 3.2: Setup RDS PostgreSQL

```bash
# Create RDS instance (Free Tier)
aws rds create-db-instance \
    --db-instance-identifier learning-space-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --master-username admin \
    --master-user-password YourSecurePassword123 \
    --allocated-storage 20 \
    --backup-retention-period 0 \
    --publicly-accessible \
    --vpc-security-group-ids sg-xxxxxxxx

# Wait for creation (~10 minutes)
aws rds wait db-instance-available --db-instance-identifier learning-space-db

# Get endpoint
aws rds describe-db-instances --db-instance-identifier learning-space-db \
    --query 'DBInstances[0].Endpoint.Address' --output text
```

#### Step 3.3: Launch EC2 Instance

```bash
# Create key pair
aws ec2 create-key-pair --key-name learning-space-key \
    --query 'KeyMaterial' --output text > learning-space-key.pem
chmod 400 learning-space-key.pem

# Launch t2.micro instance (Free Tier)
aws ec2 run-instances \
    --image-id ami-0c55b159cbfafe1f0 \  # Ubuntu 22.04
    --instance-type t2.micro \
    --key-name learning-space-key \
    --security-group-ids sg-xxxxxxxx \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=learning-space-app}]'

# Get public IP
aws ec2 describe-instances --filters "Name=tag:Name,Values=learning-space-app" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' --output text
```

---

### **Phase 4: Deployment** (Dan 7-8)

#### Step 4.1: Deploy to EC2

```bash
# SSH into EC2
ssh -i learning-space-key.pem ubuntu@<PUBLIC_IP>

# Install Docker
sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker ubuntu
# Logout and login again

# Clone repo
git clone https://github.com/YOUR_USERNAME/knowledge-space-builder.git
cd knowledge-space-builder

# Setup environment
cp backend/.env.example backend/.env
# Edit backend/.env with real values (RDS endpoint, S3 bucket, etc.)

# Build and run
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose exec backend alembic upgrade head
```

#### Step 4.2: Docker Compose Production

**docker-compose.prod.yml:**
```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
    depends_on:
      - backend
    restart: unless-stopped

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    env_file:
      - ./backend/.env
    volumes:
      - ./learning-space-generator:/app/learning-space-generator:ro
    depends_on:
      - redis
    restart: unless-stopped

  celery:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A app.celery_app worker --loglevel=info --concurrency=2
    env_file:
      - ./backend/.env
    volumes:
      - ./learning-space-generator:/app/learning-space-generator:ro
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
```

#### Step 4.3: Nginx Configuration

**nginx/nginx.conf:**
```nginx
events {
    worker_connections 1024;
}

http {
    include mime.types;
    default_type application/octet-stream;

    # Compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    # Cache for static files
    proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=1g;

    upstream backend {
        server backend:8000;
    }

    server {
        listen 80;
        server_name _;

        # Frontend (React)
        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
        }

        # API
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            
            # Timeouts for long-running uploads
            proxy_read_timeout 300s;
            proxy_send_timeout 300s;
        }

        # Cache results endpoint
        location /api/results/ {
            proxy_cache api_cache;
            proxy_cache_valid 200 7d;
            proxy_cache_key "$scheme$request_method$host$request_uri";
            add_header X-Cache-Status $upstream_cache_status;
            
            proxy_pass http://backend;
        }
    }
}
```

---

### **Phase 5: Frontend Deployment to CloudFront** (Dan 9)

```bash
# Build frontend
cd frontend
npm run build

# Upload to S3
aws s3 sync dist/ s3://learning-space-frontend-YOURNAME/ --delete

# Create CloudFront distribution
aws cloudfront create-distribution \
    --origin-domain-name learning-space-frontend-YOURNAME.s3.amazonaws.com \
    --default-root-object index.html

# Get CloudFront domain
aws cloudfront list-distributions \
    --query 'DistributionList.Items[0].DomainName' --output text
# Result: d1234abcd.cloudfront.net
```

---

## 🚀 Testing & Validation

### Local Testing Checklist

- [ ] Backend starts: `docker-compose up backend`
- [ ] Celery worker starts: `docker-compose up celery`
- [ ] Frontend builds: `npm run build`
- [ ] CSV upload works
- [ ] NEAT task runs in background
- [ ] Graph visualization renders

### Production Testing Checklist

- [ ] EC2 accessible via HTTP
- [ ] S3 uploads work
- [ ] RDS connection works
- [ ] Celery tasks execute
- [ ] Results saved to S3
- [ ] CloudFront serves frontend

---

## 💰 Cost Monitoring

**Free Tier Limits:**
- EC2 t2.micro: 750 hours/month (1 instance 24/7 = 720h)
- RDS t3.micro: 750 hours/month
- S3: 5GB storage, 20k GET, 2k PUT
- CloudFront: 1TB transfer

**Set billing alarm:**
```bash
aws cloudwatch put-metric-alarm \
    --alarm-name "Billing Alert" \
    --alarm-description "Alert when charges exceed $5" \
    --metric-name EstimatedCharges \
    --namespace AWS/Billing \
    --statistic Maximum \
    --period 21600 \
    --threshold 5 \
    --comparison-operator GreaterThanThreshold
```

---

## 🔒 Security Considerations

1. **Environment Variables**: NEVER commit `.env` to git
2. **S3 Bucket Policy**: Private by default, presigned URLs for downloads
3. **RDS**: Not publicly accessible (only from EC2 security group)
4. **HTTPS**: Use Let's Encrypt SSL certificate (after initial deployment)
5. **Rate Limiting**: Add nginx rate limiting for uploads

---

## 📊 Monitoring & Logging

**CloudWatch Logs:**
```bash
# Enable logging from EC2
sudo apt install awslogs
# Configure /etc/awslogs/awslogs.conf

# View logs
aws logs tail /aws/ec2/learning-space-backend --follow
```

---

## 🔄 CI/CD (Optional - Phase 6)

**GitHub Actions** for automatic deployment:
- Push to `main` → Build frontend → Deploy to S3
- Push to `main` → SSH to EC2 → Pull & restart containers

---

## 📞 Support & Next Steps

After deployment:
1. Test with small CSV (~100 rows)
2. Test with medium CSV (~10k rows)
3. Monitor CloudWatch metrics
4. Add authentication (JWT)
5. Add user dashboards
6. Implement result caching

**Estimated Timeline:**
- Days 1-2: Backend core
- Days 3-4: Frontend core
- Days 5-6: AWS setup
- Days 7-8: Deployment
- Day 9: Testing & fixes
- Day 10: Production ready

**Total Implementation Time: ~10 days** (assuming 4-6h/day)
