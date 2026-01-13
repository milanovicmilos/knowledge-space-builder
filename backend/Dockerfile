FROM python:3.11-slim

WORKDIR /app

# Copy both requirements files
COPY requirements.txt .
COPY lsg_requirements.txt .

# Install Python packages (backend + learning_space_generator dependencies)
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r lsg_requirements.txt

# Copy application
COPY . .

# Create storage directory
RUN mkdir -p /app/storage

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
