# GTFS-RT Feed Ingestion Scheduler

This directory contains Prefect flows and deployment scripts for scheduled ingestion of GTFS-RT feeds from NYC MTA.

## Overview

The scheduler uses [Prefect](https://www.prefect.io/) to orchestrate periodic ingestion of GTFS-RT feeds:
- **Vehicle Positions**: Real-time vehicle location data
- **Trip Updates**: Real-time trip delay and arrival predictions

## Features

- ✅ Scheduled periodic ingestion (configurable interval or cron)
- ✅ Automatic retries on failure
- ✅ Comprehensive logging (successes and failures)
- ✅ Concurrent ingestion of multiple feed types
- ✅ Prefect UI integration for monitoring

## Prerequisites

1. Install dependencies:
   ```bash
   # On Windows, use 'py' instead of 'python'
   py -m pip install -r ../backend/requirements.txt
   
   # Or if 'python' works in your environment:
   python -m pip install -r ../backend/requirements.txt
   ```

2. Set environment variables:
   ```bash
   export MTA_API_KEY="your-mta-api-key"
   export GTFS_STORAGE_PATH="./data/gtfs_rt"  # Optional, defaults to ./data/gtfs_rt
   ```

3. Start Prefect server:
   ```bash
   # On Windows, use 'py -m prefect' if 'prefect' command doesn't work
   py -m prefect server start
   # or
   prefect server start
   ```
   
   **Note:** If you're using `py` to run scripts, also use it for Prefect:
   ```powershell
   py -m prefect server start
   ```
   This will start the Prefect UI at http://127.0.0.1:4200

## Quick Start

### Option 1: Using the Deployment Script (Recommended)

The deployment script uses Prefect's `serve` method which handles both deployment and execution:

```bash
# Deploy with default 30-minute interval
# On Windows, use 'py' instead of 'python' if 'python' doesn't work
py deploy_scheduler.py
# or
python deploy_scheduler.py

# Deploy with custom interval (in minutes)
py deploy_scheduler.py --interval 15

# Deploy with cron expression
py deploy_scheduler.py --cron "*/30 * * * *"
```

The script will:
1. Create a deployment for the GTFS-RT ingestion flow
2. Start serving the deployment (running flows on schedule)
3. Run continuously until stopped (Ctrl+C)

### Option 2: Using Prefect CLI

1. Deploy the flow:
   ```bash
   # Create deployment file (deployment.yaml) first
   # Then deploy:
   prefect deploy gtfs_ingestion_flow.py:gtfs_rt_ingestion_flow \
     --name gtfs-rt-ingestion-scheduled \
     --cron "*/30 * * * *"
   ```

2. Start an agent to run the deployment:
   ```bash
   python run_scheduler.py
   # Or use Prefect CLI directly:
   prefect agent start -q gtfs-ingestion
   ```

## Configuration

### Schedule Options

- **Interval Schedule**: Run every N minutes
  ```bash
  python deploy_scheduler.py --interval 30  # Every 30 minutes
  ```

- **Cron Schedule**: Use cron expression
  ```bash
  python deploy_scheduler.py --cron "*/30 * * * *"  # Every 30 minutes
  python deploy_scheduler.py --cron "0 * * * *"     # Every hour
  python deploy_scheduler.py --cron "0 0 * * *"    # Daily at midnight
  ```

### Work Queue

Work queues organize which agents execute which deployments:

```bash
python deploy_scheduler.py --work-queue my-queue
python run_scheduler.py --work-queue my-queue
```

## Monitoring

### Prefect UI

Once the Prefect server is running, access the UI at:
- URL: http://127.0.0.1:4200

In the UI, you can:
- View all flow runs
- See success/failure status
- View detailed logs
- Monitor execution times
- Set up notifications

### Logs

All runs log:
- Start/end times
- Success/failure status
- Feed file paths
- Statistics (successful/total fetches)
- Error messages (if any)

Logs are available in:
1. Prefect UI (recommended)
2. Console output
3. Prefect logs directory

## Flow Details

### Tasks

- `ingest_vehicle_positions`: Fetches and saves vehicle positions feed
- `ingest_trip_updates`: Fetches and saves trip updates feed

### Retries

Each task has:
- **Retries**: 2 attempts
- **Retry delay**: 30 seconds between retries

### Concurrency

Both feed types are ingested concurrently when `ingest_both=True`.

## Example Usage

### Basic Scheduled Ingestion

```bash
# Terminal 1: Start Prefect server
prefect server start

# Terminal 2: Deploy and run scheduler (30-minute intervals)
python deploy_scheduler.py --interval 30
```

### Custom Schedule

```bash
# Run every 15 minutes during business hours (9 AM - 5 PM, weekdays)
python deploy_scheduler.py --cron "*/15 9-17 * * 1-5"
```

### Multiple Agents

You can run multiple agents for high availability:

```bash
# Terminal 1
python run_scheduler.py --work-queue gtfs-ingestion

# Terminal 2
python run_scheduler.py --work-queue gtfs-ingestion
```

## Troubleshooting

### Agent Not Running Flows

1. Check that Prefect server is running: `prefect server start`
2. Verify deployment exists: Check Prefect UI
3. Ensure work queue names match between deployment and agent
4. Check agent logs for errors

### Flow Failures

1. Check Prefect UI for detailed error messages
2. Verify `MTA_API_KEY` is set correctly
3. Check network connectivity to MTA API
4. Verify storage path is writable

### Import Errors

If you see import errors:
1. Ensure you're in the project root directory
2. Check that `backend/` directory is in Python path
3. Install all dependencies: `pip install -r backend/requirements.txt`

## Acceptance Criteria

✅ **Feed ingestion runs on schedule** - Deployment is configured with interval/cron schedule  
✅ **Logs successes/failures** - All runs log success/failure status with details

## Docker Support

The scheduler is fully configured to run in Docker. See `DOCKER_README.md` for details.

**Quick start with Docker:**
```bash
# Start all services including scheduler
docker-compose up -d

# View scheduler logs
docker-compose logs -f scheduler
```

The scheduler runs as a separate service in `docker-compose.yml` with all necessary dependencies and environment variables configured.

## Files

- `gtfs_ingestion_flow.py`: Prefect flow definitions for feed ingestion
- `deploy_scheduler.py`: Script to deploy scheduled ingestion
- `run_scheduler.py`: Script to run Prefect agent
- `SCHEDULER_README.md`: This file
- `DOCKER_README.md`: Docker-specific documentation
- `Dockerfile`: Docker image definition for scheduler



