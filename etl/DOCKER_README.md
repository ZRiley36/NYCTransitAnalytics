# Running Scheduler in Docker

The scheduler is configured to run in Docker alongside the backend service.

## Docker Setup

The scheduler runs as a separate service in `docker-compose.yml`. It:
- Shares the same dependencies as the backend
- Has access to the backend code for imports
- Uses the same environment variables (MTA_API_KEY, cloud storage, etc.)
- Writes data to the shared `/app/data` volume

## Running with Docker Compose

1. **Start all services including the scheduler:**
   ```bash
   docker-compose up -d
   ```

2. **Start just the scheduler:**
   ```bash
   docker-compose up -d scheduler
   ```

3. **View scheduler logs:**
   ```bash
   docker-compose logs -f scheduler
   ```

4. **Stop the scheduler:**
   ```bash
   docker-compose stop scheduler
   ```

## Configuration

The scheduler runs with default settings:
- **Schedule**: Every 30 minutes
- **Storage path**: `/app/data/gtfs_rt` (mapped to `./data/gtfs_rt` on host)
- **Prefect server**: Runs in the same container (use Prefect UI for monitoring)

### Customizing the Schedule

Edit `docker-compose.yml` to change the scheduler command:

```yaml
scheduler:
  # ...
  command: ["python", "deploy_scheduler.py", "--interval", "15"]  # Every 15 minutes
  # or
  command: ["python", "deploy_scheduler.py", "--cron", "*/30 * * * *"]  # Cron expression
```

### Running Prefect UI

To access Prefect UI, uncomment the port mapping in `docker-compose.yml`:

```yaml
scheduler:
  ports:
    - "4200:4200"  # Prefect UI
```

Then access it at http://localhost:4200

## Environment Variables

The scheduler uses the same environment variables as the backend:
- `MTA_API_KEY`: Required for GTFS-RT API access
- `GTFS_STORAGE_PATH`: Path to store feeds (default: `/app/data/gtfs_rt`)
- Cloud storage config (S3, GCS) - same as backend

## Troubleshooting

1. **Scheduler not starting:**
   ```bash
   docker-compose logs scheduler
   ```

2. **Check if dependencies are installed:**
   ```bash
   docker-compose exec scheduler pip list | grep prefect
   ```

3. **Test the scheduler manually:**
   ```bash
   docker-compose exec scheduler python deploy_scheduler.py --interval 5
   ```

4. **Verify data is being saved:**
   ```bash
   docker-compose exec scheduler ls -la /app/data/gtfs_rt/
   ```

## Development

For development, the scheduler container has volumes mounted for live code changes:
- `./backend:/app/backend`
- `./etl:/app/etl`

Changes to scheduler code will be reflected immediately (container restart may be needed for Prefect to pick up changes).

