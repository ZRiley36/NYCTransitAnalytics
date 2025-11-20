FROM python:3.11-slim

WORKDIR /app

# Copy requirements from backend (build context is project root in docker-compose)
COPY backend/requirements.txt ./backend-requirements.txt
RUN pip install --no-cache-dir -r backend-requirements.txt

# Copy backend code (needed for imports like gtfs_rt_connector)
COPY backend ./backend

# Copy etl/scheduler code
COPY etl ./etl

# Set Python path to include backend for imports
ENV PYTHONPATH=/app/backend:/app/etl:$PYTHONPATH

# Default command - runs the scheduler (can be overridden in docker-compose)
WORKDIR /app/etl
CMD ["python", "deploy_scheduler.py", "--interval", "30"]

