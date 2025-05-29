# Dockerfile
FROM python:3.8-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python code
COPY src/ /app/src/

# Set default command (can override in compose)
CMD ["python", "src/data_ingestion/mqtt_consumer.py"]