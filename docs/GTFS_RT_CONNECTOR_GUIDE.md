# GTFS-RT Connector Guide

## Overview

You have **two ways** to fetch GTFS-RT feeds from the NYC MTA:

1. **Backend GTFS-RT Connector** - Built into the FastAPI backend, polls every 20 seconds
2. **Prefect Scheduler** - Separate service that runs on a schedule (every 30 minutes by default)

Both use the same underlying `GTFSRTConnector` class, but they work differently.

---

## Option 1: Backend GTFS-RT Connector

### What It Is

The backend connector is built into the FastAPI application. It's initialized when the backend starts but **doesn't run automatically** - you need to start it manually via API.

### Features

- ✅ Fast polling (20 seconds by default)
- ✅ Runs in the backend container
- ✅ Simple to use - just start/stop via API
- ✅ Real-time status and statistics
- ✅ Automatic cloud storage upload (if configured)

### How to Use

**1. Start the connector:**
```bash
# Bash/Linux/Mac
curl -X POST http://localhost:8000/gtfs-rt/start

# PowerShell/Windows
Invoke-WebRequest -Uri http://localhost:8000/gtfs-rt/start -Method POST
```

**2. Check status:**
```bash
# Bash/Linux/Mac
curl http://localhost:8000/gtfs-rt/status

# PowerShell/Windows
Invoke-WebRequest -Uri http://localhost:8000/gtfs-rt/status | Select-Object -ExpandProperty Content
```

**3. Stop the connector:**
```bash
# Bash/Linux/Mac
curl -X POST http://localhost:8000/gtfs-rt/stop

# PowerShell/Windows
Invoke-WebRequest -Uri http://localhost:8000/gtfs-rt/stop -Method POST
```

**4. Manual fetch (without starting continuous polling):**
```bash
# Bash/Linux/Mac
curl -X POST "http://localhost:8000/gtfs-rt/fetch?feed_type=vehicle_positions"

# PowerShell/Windows
Invoke-WebRequest -Uri "http://localhost:8000/gtfs-rt/fetch?feed_type=vehicle_positions" -Method POST
```

### Status Response

```json
{
  "is_running": true,
  "poll_interval": 20,
  "storage_path": "./data/gtfs_rt",
  "stats": {
    "total_fetches": 100,
    "successful_fetches": 98,
    "failed_fetches": 2,
    "last_fetch_time": "2025-11-18T16:46:00",
    "last_error": null
  },
  "cloud_storage": {
    "enabled": true,
    "provider": "S3StorageProvider",
    "total_uploads": 200,
    "successful_uploads": 198,
    "failed_uploads": 2
  }
}
```

### Configuration

The connector is configured in `backend/main.py`:

```python
gtfs_connector = GTFSRTConnector(
    storage_path="./data/gtfs_rt",  # Where to save files
    poll_interval=20,               # Polling interval (10-30s)
    max_retries=3,                  # Retry attempts
    retry_delay=5.0,                # Delay between retries
)
```

### When to Use

- ✅ You want fast, frequent polling (every 20 seconds)
- ✅ You want manual control (start/stop via API)
- ✅ You're testing or developing
- ✅ You want real-time status via API

### Limitations

- ❌ Requires manual start (doesn't auto-start)
- ❌ Stops if backend container restarts
- ❌ No built-in scheduling (runs continuously once started)

---

## Option 2: Prefect Scheduler

### What It Is

The Prefect scheduler is a separate service that runs scheduled ingestion flows. It uses the same `GTFSRTConnector` but runs on a schedule (every 30 minutes by default).

### Features

- ✅ Automatic scheduling (runs on schedule)
- ✅ Better logging and monitoring (Prefect UI)
- ✅ Automatic retries with backoff
- ✅ Runs independently of backend
- ✅ Can run multiple feed types concurrently
- ✅ Automatic cloud storage upload (if configured)

### Current Issue: Ephemeral Server

**Problem:** The scheduler is currently running in "ephemeral server" mode, which means:
- ❌ It **cannot** automatically schedule flows
- ✅ It **can** run flows manually via `prefect deployment run`
- ⚠️ You'll see a warning: "Cannot schedule flows on an ephemeral server"

**Solution:** You have two options:

#### Solution A: Use the Backend Connector Instead

If you want automatic periodic fetching, use the backend connector and start it:

```bash
# Start the connector (polls every 20 seconds)
Invoke-WebRequest -Uri http://localhost:8000/gtfs-rt/start -Method POST
```

#### Solution B: Fix Prefect to Actually Schedule

To make Prefect actually schedule flows, you need to run a dedicated Prefect server:

**1. Update `docker-compose.yml`:**

```yaml
scheduler:
  # ... existing config ...
  command: ["sh", "-c", "prefect server start --host 0.0.0.0 & sleep 5 && python deploy_scheduler.py --interval 30"]
  ports:
    - "4200:4200"  # Prefect UI
```

**2. Or run Prefect server separately:**

```bash
# Terminal 1: Start Prefect server
docker-compose exec scheduler prefect server start --host 0.0.0.0

# Terminal 2: Deploy the flow
docker-compose exec scheduler python deploy_scheduler.py --interval 30
```

**3. Or use Prefect Cloud (hosted):**

- Sign up at https://app.prefect.cloud/
- Configure Prefect Cloud API key
- Deploy flows to Prefect Cloud instead of local server

### How to Use (Current Setup)

Since the scheduler is in ephemeral mode, you can trigger runs manually:

```bash
# Trigger a manual run
docker-compose exec scheduler prefect deployment run 'gtfs_rt_ingestion_flow/gtfs-rt-ingestion-scheduled'
```

### When to Use

- ✅ You want scheduled, periodic ingestion (every 30+ minutes)
- ✅ You want better logging and monitoring
- ✅ You're running in production
- ✅ You want automatic retries and error handling

### Limitations (Current Setup)

- ❌ Ephemeral server can't auto-schedule (needs fix)
- ❌ Longer default interval (30 min vs 20s)
- ❌ More complex setup

---

## Comparison

| Feature | Backend Connector | Prefect Scheduler |
|---------|------------------|------------------|
| **Polling Interval** | 20 seconds | 30 minutes (default) |
| **Auto-Start** | ❌ Manual via API | ✅ Automatic (when fixed) |
| **Status API** | ✅ `/gtfs-rt/status` | ❌ Prefect UI only |
| **Logging** | Backend logs | Prefect UI + logs |
| **Retries** | ✅ Built-in | ✅ Built-in + better |
| **Cloud Storage** | ✅ Automatic | ✅ Automatic |
| **Concurrent Feeds** | ✅ Sequential | ✅ Concurrent |
| **Production Ready** | ⚠️ Good for dev | ✅ Better for prod |

---

## Recommended Setup

### For Development/Testing

**Use the Backend Connector:**
```bash
# Start services
docker-compose up -d

# Start connector (polls every 20s)
Invoke-WebRequest -Uri http://localhost:8000/gtfs-rt/start -Method POST

# Check status
Invoke-WebRequest -Uri http://localhost:8000/gtfs-rt/status | Select-Object -ExpandProperty Content
```

### For Production

**Option 1: Use Backend Connector with Auto-Start**

Modify `backend/main.py` to auto-start the connector:

```python
@app.on_event("startup")
async def startup_event():
    global gtfs_connector
    if gtfs_connector:
        await gtfs_connector.start()
```

**Option 2: Fix Prefect Scheduler**

Set up a dedicated Prefect server (see Solution B above) or use Prefect Cloud.

---

## Troubleshooting

### Connector Not Starting

```bash
# Check if backend is running
docker-compose ps backend

# Check backend logs
docker-compose logs backend

# Verify API key is set
docker-compose exec backend env | grep MTA_API_KEY
```

### Scheduler Warning About Ephemeral Server

This is expected with the current setup. The scheduler can still run flows manually, but won't auto-schedule. Either:
1. Use the backend connector instead
2. Fix Prefect to use a dedicated server (see Solution B above)

### No Files Being Saved

```bash
# Check storage path exists
docker-compose exec backend ls -la /app/data/gtfs_rt/

# Check permissions
docker-compose exec backend ls -ld /app/data/gtfs_rt/

# Check connector status
curl http://localhost:8000/gtfs-rt/status
```

### Cloud Storage Not Uploading

```bash
# Check if cloud storage is enabled
curl http://localhost:8000/gtfs-rt/status | jq .cloud_storage.enabled

# Check credentials
docker-compose exec backend env | grep CLOUD_STORAGE

# Check logs for errors
docker-compose logs backend | grep -i "cloud\|storage"
```

---

## Summary

**For most use cases, use the Backend Connector:**
- Simple to use
- Fast polling (20s)
- Good status API
- Works out of the box

**For production with scheduling, fix Prefect:**
- Better logging
- Automatic scheduling (when fixed)
- Better error handling
- More production-ready

See [Deployment Guide](DEPLOYMENT_GUIDE.md) for more details.

