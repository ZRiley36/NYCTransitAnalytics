# GTFS-RT Feed Connector

## Overview

The GTFS-RT (General Transit Feed Specification Realtime) connector pulls subway position data and delay information from NYC MTA's real-time feeds every 10-30 seconds.

## Setup

### 1. Get MTA API Key

1. Visit: https://api.mta.info/
2. Sign up for an API key
3. Add the key to your environment:

**Option A: Environment Variable**
```bash
export MTA_API_KEY=your_api_key_here
```

**Option B: Docker Compose (.env file)**
Create a `.env` file in the project root:
```
MTA_API_KEY=your_api_key_here
```

### 2. Storage

Feeds are saved to `./data/gtfs_rt/` (mapped to `/app/data/gtfs_rt` in Docker).

## API Endpoints

### Start Connector
```bash
POST http://localhost:8000/gtfs-rt/start
```

Starts continuous polling of GTFS-RT feeds (every 20 seconds by default).

### Stop Connector
```bash
POST http://localhost:8000/gtfs-rt/stop
```

Stops the polling loop.

### Get Status
```bash
GET http://localhost:8000/gtfs-rt/status
```

Returns connector status and statistics:
```json
{
  "is_running": true,
  "poll_interval": 20,
  "storage_path": "./data/gtfs_rt",
  "stats": {
    "total_fetches": 100,
    "successful_fetches": 98,
    "failed_fetches": 2,
    "last_fetch_time": "2025-11-17T18:00:00",
    "last_error": null
  }
}
```

### Manual Fetch
```bash
POST http://localhost:8000/gtfs-rt/fetch?feed_type=vehicle_positions
```

Manually trigger a single feed fetch without starting the polling loop.

**Feed Types:**
- `vehicle_positions` - Subway vehicle positions
- `trip_updates` - Trip updates and delays
- `alerts` - Service alerts (coming soon)

## Features

✅ **API Connection** - Connects to NYC MTA GTFS-RT feeds  
✅ **JSON Parsing** - Parses Protocol Buffer feeds to JSON  
✅ **Error Handling + Retries** - Automatic retries with exponential backoff  
✅ **Local Storage** - Saves raw `.pb` files and parsed `.json` files  
✅ **Polling** - Configurable polling interval (10-30 seconds)  

## Acceptance Criteria

✅ **Raw feed saved to local storage** - All feeds are saved to `./data/gtfs_rt/`  
- Protocol Buffer files: `vehicle_positions_YYYYMMDD_HHMMSS.pb`  
- JSON files: `vehicle_positions_YYYYMMDD_HHMMSS.json`  

## Example Usage

1. Start the backend:
```bash
docker-compose up --build
```

2. Start the connector:
```bash
curl -X POST http://localhost:8000/gtfs-rt/start
```

3. Check status:
```bash
curl http://localhost:8000/gtfs-rt/status
```

4. Stop the connector:
```bash
curl -X POST http://localhost:8000/gtfs-rt/stop
```

## File Structure

```
data/gtfs_rt/
├── vehicle_positions_20251117_180000.pb    # Raw Protocol Buffer
├── vehicle_positions_20251117_180000.json  # Parsed JSON
├── trip_updates_20251117_180005.pb
└── trip_updates_20251117_180005.json
```

## Configuration

The connector can be configured in `backend/main.py`:

```python
gtfs_connector = GTFSRTConnector(
    storage_path="./data/gtfs_rt",  # Storage location
    poll_interval=20,               # Polling interval (10-30s)
    max_retries=3,                  # Retry attempts
    retry_delay=5.0,                # Delay between retries
)
```

