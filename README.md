# NYC Transit Analytics

A real-time data ingestion and analytics platform for NYC MTA transit data using GTFS-RT feeds.

## Features

- ✅ **GTFS-RT Feed Ingestion** - Automatic polling of vehicle positions and trip updates
- ✅ **Cloud Storage** - Automatic upload to AWS S3 or Google Cloud Storage
- ✅ **Scheduled Processing** - Prefect-based scheduler for periodic data collection
- ✅ **REST API** - FastAPI backend with health checks and monitoring
- ✅ **Docker Support** - Full containerization with Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose
- MTA API Key ([Get one here](https://api.mta.info/))

### 1. Clone and Setup

```bash
git clone https://github.com/yourusername/NYCTransitAnalytics.git
cd NYCTransitAnalytics
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
MTA_API_KEY=your_api_key_here
```

### 3. Start Services

```bash
docker-compose up --build
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Backend API (port 8000)
- Prefect Scheduler (runs every 30 minutes)

### 4. Test Everything

```bash
# Health check
curl http://localhost:8000/health

# All services status
curl http://localhost:8000/health/all

# Manual feed fetch
curl -X POST "http://localhost:8000/gtfs-rt/fetch?feed_type=vehicle_positions"
```

## Documentation

- **[Complete Deployment Guide](docs/DEPLOYMENT_GUIDE.md)** - Testing, running, and deploying your service
- **[GTFS-RT Connector Guide](docs/GTFS_RT_CONNECTOR_GUIDE.md)** - Understanding the connector vs scheduler
- **[Quick Start](docs/QUICK_START.md)** - Basic setup and health checks
- **[Cloud Storage Setup](docs/CLOUD_STORAGE_SETUP.md)** - Configure S3 or GCS
- **[GTFS Interpretation Guide](docs/GTFS_INTERPRETATION_GUIDE.md)** - Understanding the data
- **[Testing Guide](docs/GTFS_RT_TEST.md)** - Testing the GTFS-RT connector

## Project Structure

```
NYCTransitAnalytics/
├── backend/          # FastAPI application
├── frontend/         # Next.js frontend
├── etl/              # Prefect scheduler and flows
├── infrastructure/   # Infrastructure as code
├── tests/            # Test suite
├── docs/             # Documentation
└── docker-compose.yml # Docker orchestration
```

## API Endpoints

- `GET /health` - Basic health check
- `GET /health/db` - Database connection status
- `GET /health/redis` - Redis connection status
- `GET /health/all` - All services status
- `GET /gtfs-rt/status` - Connector status and statistics
- `POST /gtfs-rt/start` - Start periodic polling
- `POST /gtfs-rt/stop` - Stop periodic polling
- `POST /gtfs-rt/fetch` - Manually fetch a feed

## Running on a Server

See the [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) for detailed instructions on:
- Deploying to cloud VMs (AWS EC2, GCP, DigitalOcean)
- Using managed services (Railway, Render, Fly.io)
- Setting up auto-restart and monitoring

## Cloud Storage

The service automatically uploads feed files to cloud storage (S3 or GCS) when configured. See [Cloud Storage Setup](docs/CLOUD_STORAGE_SETUP.md) for details.

## Scheduler

The Prefect scheduler runs automatically in Docker. To customize the schedule, see [Scheduler Documentation](etl/SCHEDULER_README.md).

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please open an issue or pull request.

