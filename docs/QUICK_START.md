# Quick Start Guide

## Starting Services

```bash
docker-compose up --build
```

This will start:
- PostgreSQL on port **5432**
- Redis on port **6379**
- Backend API on port **8000**

## Check Connection Status

Once services are running, test the connections:

### 1. Basic Health Check
**URL:** http://localhost:8000/health

### 2. Database Connection Test
**URL:** http://localhost:8000/health/db

**Expected Response:**
```json
{
  "status": "connected",
  "database": "postgresql",
  "version": "PostgreSQL 15.x..."
}
```

### 3. Redis Connection Test
**URL:** http://localhost:8000/health/redis

**Expected Response:**
```json
{
  "status": "connected",
  "database": "redis",
  "version": "7.x.x",
  "connected_clients": 1
}
```

### 4. All Services Status
**URL:** http://localhost:8000/health/all

**Expected Response:**
```json
{
  "status": "healthy",
  "api": {"status": "healthy"},
  "database": {"status": "connected", ...},
  "redis": {"status": "connected", ...}
}
```

## Alternative: Using curl

```bash
# Basic health
curl http://localhost:8000/health

# Database check
curl http://localhost:8000/health/db

# Redis check
curl http://localhost:8000/health/redis

# All services
curl http://localhost:8000/health/all
```

## Stop Services

Press `Ctrl+C` in the terminal, or run:
```bash
docker-compose down
```

## View Logs

```bash
docker-compose logs -f backend
docker-compose logs -f postgres
docker-compose logs -f redis
```

