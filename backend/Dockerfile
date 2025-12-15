FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

# Install Python packages (use wheels when possible, no compilation needed)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create storage directory
RUN mkdir -p /app/storage

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
