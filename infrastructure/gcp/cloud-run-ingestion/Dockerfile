FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run ingestion service
CMD ["python", "-m", "etl.gtfs_ingestion_service"]

