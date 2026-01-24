FROM python:3.11-slim

WORKDIR /app

# Copy and install backend requirements only (FastAPI, SQLAlchemy, Celery client)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/ .

# Create storage directories
RUN mkdir -p /app/storage/uploads

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


