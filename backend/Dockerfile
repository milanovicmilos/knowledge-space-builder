FROM python:3.11-slim

WORKDIR /app

# Copy both requirements files from backend directory
COPY backend/requirements.txt .
COPY backend/lsg_requirements.txt .

# Install CPU-only PyTorch first (significantly reduces image size and build time)
# We do this before generic requirements to ensure the CPU version is preferred
RUN pip install --no-cache-dir "torch>=2.0.0" --index-url https://download.pytorch.org/whl/cpu

# Install remaining Python packages
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r lsg_requirements.txt

# Copy backend application
COPY backend/ .

# Copy learning_space_generator from parent directory
COPY learning_space_generator /app/learning_space_generator

# Create storage directory
RUN mkdir -p /app/storage

ENV PYTHONPATH=/app:/app/learning_space_generator

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
