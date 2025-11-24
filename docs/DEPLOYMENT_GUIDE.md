# Complete Testing & Deployment Guide

This guide covers everything you need to test, run, and deploy your NYC Transit Analytics service.

## Table of Contents

1. [Testing Everything Works](#testing-everything-works)
2. [Running the Service with Periodic API Polling](#running-the-service-with-periodic-api-polling)
3. [Running the Prefect Scheduler](#running-the-prefect-scheduler)
4. [Setting Up Cloud Storage](#setting-up-cloud-storage)
5. [Deploying to a Server](#deploying-to-a-server)

---

## Testing Everything Works

### Step 1: Get Your MTA API Key

1. Visit https://api.mta.info/
2. Sign up for a free API key
3. Save it - you'll need it for all services

### Step 2: Start All Services Locally

```bash
# Create a .env file in the project root
cat > .env << EOF
MTA_API_KEY=your_api_key_here
EOF

# Start all services (Postgres, Redis, Backend, Scheduler)
docker-compose up --build
```

This starts:
- **PostgreSQL** on port 5432
- **Redis** on port 6379
- **Backend API** on port 8000
- **Scheduler** (Prefect) - runs automatically

### Step 3: Test Health Endpoints

Open a new terminal and test:

**Bash/Linux/Mac:**
```bash
# Basic health check
curl http://localhost:8000/health

# Database connection
curl http://localhost:8000/health/db

# Redis connection
curl http://localhost:8000/health/redis

# All services status
curl http://localhost:8000/health/all
```

**PowerShell/Windows:**
```powershell
# Basic health check
Invoke-WebRequest -Uri http://localhost:8000/health | Select-Object -ExpandProperty Content

# Database connection
Invoke-WebRequest -Uri http://localhost:8000/health/db | Select-Object -ExpandProperty Content

# Redis connection
Invoke-WebRequest -Uri http://localhost:8000/health/redis | Select-Object -ExpandProperty Content

# All services status
Invoke-WebRequest -Uri http://localhost:8000/health/all | Select-Object -ExpandProperty Content
```

**Expected:** All should return `"status": "connected"` or `"healthy"`

### Step 4: Test GTFS-RT Connector

**Bash/Linux/Mac:**
```bash
# Check connector status
curl http://localhost:8000/gtfs-rt/status

# Manually fetch a feed (test API connection)
curl -X POST "http://localhost:8000/gtfs-rt/fetch?feed_type=vehicle_positions"

# Check if files were saved
ls -la ./data/gtfs_rt/
```

**PowerShell/Windows:**
```powershell
# Check connector status
Invoke-WebRequest -Uri http://localhost:8000/gtfs-rt/status | Select-Object -ExpandProperty Content

# Manually fetch a feed (test API connection)
Invoke-WebRequest -Uri "http://localhost:8000/gtfs-rt/fetch?feed_type=vehicle_positions" -Method POST

# Check if files were saved
Get-ChildItem -Path ./data/gtfs_rt/ | Select-Object Name, Length, LastWriteTime
```

You should see `.pb` and `.json` files created.

### Step 5: Verify Scheduler is Running

```bash
# Check scheduler logs
docker-compose logs -f scheduler

# You should see Prefect flow runs every 30 minutes (default)
```

---

## Running the Service with Periodic API Polling

You have **two options** for periodic polling:

### Option A: Using the Backend Connector (Manual Start)

The backend has a built-in connector that polls every 20 seconds:

**Bash/Linux/Mac:**
```bash
# Start the connector
curl -X POST http://localhost:8000/gtfs-rt/start

# Check status
curl http://localhost:8000/gtfs-rt/status

# Stop when done
curl -X POST http://localhost:8000/gtfs-rt/stop
```

**PowerShell/Windows:**
```powershell
# Start the connector
Invoke-WebRequest -Uri http://localhost:8000/gtfs-rt/start -Method POST

# Check status
Invoke-WebRequest -Uri http://localhost:8000/gtfs-rt/status | Select-Object -ExpandProperty Content

# Stop when done
Invoke-WebRequest -Uri http://localhost:8000/gtfs-rt/stop -Method POST
```

**Pros:** Simple, fast polling (20s intervals)  
**Cons:** Requires manual start, runs in backend container

### Option B: Using Prefect Scheduler

⚠️ **Important:** The Prefect scheduler is currently running in "ephemeral server" mode, which means it **cannot automatically schedule flows**. You'll see a warning: "Cannot schedule flows on an ephemeral server."

**Current Status:**
- ✅ Can run flows manually via `prefect deployment run`
- ❌ Cannot auto-schedule flows
- ⚠️ Requires fix to enable automatic scheduling

**To fix automatic scheduling**, you need to run a dedicated Prefect server. See [GTFS-RT Connector Guide](GTFS_RT_CONNECTOR_GUIDE.md) for details.

**For now, use Option A (Backend Connector) for automatic periodic polling.**

**To customize the schedule** (once fixed), edit `docker-compose.yml`:

```yaml
scheduler:
  # ... existing config ...
  command: ["python", "deploy_scheduler.py", "--interval", "15"]  # Every 15 minutes
  # or
  command: ["python", "deploy_scheduler.py", "--cron", "*/20 * * * *"]  # Every 20 minutes
```

**Pros:** Better logging, retries, production-ready (when fixed)  
**Cons:** Currently can't auto-schedule, longer default interval (30 min vs 20s)

**See [GTFS-RT Connector Guide](GTFS_RT_CONNECTOR_GUIDE.md) for complete details on both options.**

---

## Running the Prefect Scheduler

### Method 1: Using Docker Compose (Easiest)

The scheduler is already configured in `docker-compose.yml`:

```bash
# Start scheduler (starts automatically with docker-compose up)
docker-compose up -d scheduler

# View logs
docker-compose logs -f scheduler

# Stop scheduler
docker-compose stop scheduler
```

### Method 2: Running Locally (Without Docker)

**Prerequisites:**
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Set environment variables
export MTA_API_KEY="your_api_key_here"
export GTFS_STORAGE_PATH="./data/gtfs_rt"
```

**Run the scheduler:**

```bash
# Option A: Using deploy script (recommended)
cd etl
python deploy_scheduler.py --interval 30

# Option B: Using Prefect CLI
prefect server start  # Terminal 1
python deploy_scheduler.py --interval 30  # Terminal 2
```

**Access Prefect UI:**
- URL: http://127.0.0.1:4200
- View flow runs, logs, and status

### Customizing the Schedule

```bash
# Every 15 minutes
python deploy_scheduler.py --interval 15

# Every 20 minutes using cron
python deploy_scheduler.py --cron "*/20 * * * *"

# Every hour
python deploy_scheduler.py --cron "0 * * * *"

# Business hours only (9 AM - 5 PM, weekdays)
python deploy_scheduler.py --cron "*/15 9-17 * * 1-5"
```

---

## Setting Up Cloud Storage

Cloud storage automatically uploads all feed files to S3 or GCS. Files are organized by date: `YYYY/MM/DD/filename`.

### Option A: AWS S3 Setup

**1. Create S3 Bucket:**
```bash
aws s3 mb s3://nyc-transit-gtfs-rt --region us-east-1
```

**2. Create IAM User with S3 Permissions:**
- Go to AWS IAM Console
- Create user with programmatic access
- Attach policy: `AmazonS3FullAccess` (or custom policy with `s3:PutObject`, `s3:GetObject`)
- Save Access Key ID and Secret Access Key

**3. Configure Environment Variables:**

Create/update `.env` file:
```bash
CLOUD_STORAGE_TYPE=s3
S3_BUCKET_NAME=nyc-transit-gtfs-rt
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_REGION=us-east-1
```

**4. Restart Services:**
```bash
docker-compose down
docker-compose up -d
```

**5. Verify Upload:**

**Bash/Linux/Mac:**
```bash
# Check status
curl http://localhost:8000/gtfs-rt/status | jq .cloud_storage

# Check bucket
aws s3 ls s3://nyc-transit-gtfs-rt/2025/11/18/
```

**PowerShell/Windows:**
```powershell
# Check status (requires jq or parse JSON manually)
$response = Invoke-WebRequest -Uri http://localhost:8000/gtfs-rt/status
$json = $response.Content | ConvertFrom-Json
$json.cloud_storage

# Check bucket
aws s3 ls s3://nyc-transit-gtfs-rt/2025/11/18/
```

### Option B: Google Cloud Storage Setup

**1. Create GCS Bucket:**
```bash
gsutil mb -p your-project-id -l us-east1 gs://nyc-transit-gtfs-rt
```

**2. Create Service Account:**
```bash
gcloud iam service-accounts create gtfs-rt-uploader \
    --display-name="GTFS-RT Uploader"

gcloud projects add-iam-policy-binding your-project-id \
    --member="serviceAccount:gtfs-rt-uploader@your-project-id.iam.gserviceaccount.com" \
    --role="roles/storage.objectCreator"
```

**3. Download Credentials:**
```bash
gcloud iam service-accounts keys create credentials.json \
    --iam-account=gtfs-rt-uploader@your-project-id.iam.gserviceaccount.com
```

**4. Configure Environment Variables:**

Create/update `.env` file:
```bash
CLOUD_STORAGE_TYPE=gcs
GCS_BUCKET_NAME=nyc-transit-gtfs-rt
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

**5. Mount Credentials in Docker:**

Update `docker-compose.yml`:
```yaml
scheduler:
  volumes:
    - ./credentials.json:/app/credentials.json
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json
```

**6. Restart Services:**
```bash
docker-compose down
docker-compose up -d
```

**7. Verify Upload:**
```bash
# Check status
curl http://localhost:8000/gtfs-rt/status | jq .cloud_storage

# Check bucket
gsutil ls gs://nyc-transit-gtfs-rt/2025/11/18/
```

### Testing Cloud Storage

**Bash/Linux/Mac:**
```bash
# Trigger a manual fetch
curl -X POST "http://localhost:8000/gtfs-rt/fetch?feed_type=vehicle_positions"

# Check logs for upload confirmation
docker-compose logs backend | grep -i "uploaded"

# Verify files in bucket
# S3:
aws s3 ls s3://nyc-transit-gtfs-rt/$(date +%Y/%m/%d)/

# GCS:
gsutil ls gs://nyc-transit-gtfs-rt/$(date +%Y/%m/%d)/
```

**PowerShell/Windows:**
```powershell
# Trigger a manual fetch
Invoke-WebRequest -Uri "http://localhost:8000/gtfs-rt/fetch?feed_type=vehicle_positions" -Method POST

# Check logs for upload confirmation
docker-compose logs backend | Select-String -Pattern "uploaded" -CaseSensitive:$false

# Verify files in bucket
# S3:
$date = Get-Date -Format "yyyy/MM/dd"
aws s3 ls "s3://nyc-transit-gtfs-rt/$date/"

# GCS:
$date = Get-Date -Format "yyyy/MM/dd"
gsutil ls "gs://nyc-transit-gtfs-rt/$date/"
```

---

## Deploying to a Server

You have several options for running your service on a server so you don't need your laptop open.

### Option 1: Cloud VM (AWS EC2, Google Compute Engine, DigitalOcean)

**Recommended for:** Full control, cost-effective

**Steps:**

1. **Launch a VM:**
   - AWS EC2: t3.small or t3.medium (2GB+ RAM)
   - Google Compute Engine: e2-small or e2-medium
   - DigitalOcean: 2GB Droplet ($12/month)
   - Ubuntu 22.04 LTS recommended

2. **SSH into the server:**
   ```bash
   ssh user@your-server-ip
   ```

3. **Install Docker and Docker Compose:**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y

   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh

   # Install Docker Compose
   sudo apt install docker-compose-plugin -y

   # Add user to docker group
   sudo usermod -aG docker $USER
   # Log out and back in for this to take effect
   ```

4. **Clone your repository:**
   ```bash
   git clone https://github.com/yourusername/NYCTransitAnalytics.git
   cd NYCTransitAnalytics
   ```

5. **Create `.env` file:**
   ```bash
   nano .env
   ```
   Add:
   ```
   MTA_API_KEY=your_api_key_here
   CLOUD_STORAGE_TYPE=s3
   S3_BUCKET_NAME=nyc-transit-gtfs-rt
   AWS_ACCESS_KEY_ID=your_key
   AWS_SECRET_ACCESS_KEY=your_secret
   AWS_REGION=us-east-1
   ```

6. **Start services:**
   ```bash
   docker-compose up -d --build
   ```

7. **Verify it's running:**
   ```bash
   docker-compose ps
   docker-compose logs -f scheduler
   ```

8. **Set up auto-restart (systemd service):**
   ```bash
   sudo nano /etc/systemd/system/nyc-transit.service
   ```
   Add:
   ```ini
   [Unit]
   Description=NYC Transit Analytics
   Requires=docker.service
   After=docker.service

   [Service]
   Type=oneshot
   RemainAfterExit=yes
   WorkingDirectory=/home/user/NYCTransitAnalytics
   ExecStart=/usr/bin/docker compose up -d
   ExecStop=/usr/bin/docker compose down
   TimeoutStartSec=0

   [Install]
   WantedBy=multi-user.target
   ```

   Enable:
   ```bash
   sudo systemctl enable nyc-transit.service
   sudo systemctl start nyc-transit.service
   ```

### Option 2: AWS ECS / Fargate

**Recommended for:** Serverless, auto-scaling, managed

**Steps:**

1. **Create ECR repository:**
   ```bash
   aws ecr create-repository --repository-name nyc-transit-analytics
   ```

2. **Build and push Docker images:**
   ```bash
   # Get login token
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

   # Build and tag
   docker build -t nyc-transit-backend ./backend
   docker tag nyc-transit-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/nyc-transit-analytics:backend

   # Push
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/nyc-transit-analytics:backend
   ```

3. **Create ECS Task Definition** (use AWS Console or Terraform)
   - Define containers: backend, scheduler, postgres, redis
   - Set environment variables
   - Configure volumes

4. **Create ECS Service** with desired count = 1

### Option 3: Google Cloud Run

**Recommended for:** Serverless, pay-per-use

**Steps:**

1. **Build and push to GCR:**
   ```bash
   gcloud builds submit --tag gcr.io/your-project/nyc-transit-backend ./backend
   ```

2. **Deploy to Cloud Run:**
   ```bash
   gcloud run deploy nyc-transit-backend \
     --image gcr.io/your-project/nyc-transit-backend \
     --platform managed \
     --region us-east1 \
     --set-env-vars MTA_API_KEY=your_key
   ```

### Option 4: Railway / Render / Fly.io

**Recommended for:** Easiest deployment, managed services

**Railway:**
1. Connect GitHub repo
2. Add environment variables
3. Deploy automatically

**Render:**
1. Create new Web Service
2. Connect GitHub repo
3. Set build command: `docker-compose build`
4. Set start command: `docker-compose up`
5. Add environment variables

**Fly.io:**
1. Install flyctl
2. `fly launch`
3. Configure `fly.toml`
4. Deploy: `fly deploy`

### Monitoring Your Deployment

**Check logs remotely:**
```bash
# SSH into server
ssh user@your-server-ip

# View logs
docker-compose logs -f scheduler
docker-compose logs -f backend

# Check service status
docker-compose ps
curl http://localhost:8000/health/all
```

**Set up monitoring:**
- Use Prefect UI (if accessible): http://your-server-ip:4200
- Set up health check alerts (UptimeRobot, Pingdom)
- Monitor cloud storage uploads via AWS/GCS console

### Cost Estimates

**VM (DigitalOcean 2GB):** ~$12/month
- 24/7 operation
- Full control

**AWS ECS Fargate:** ~$15-30/month
- Pay for compute time
- Auto-scaling

**Cloud Run:** ~$5-10/month
- Pay per request
- Scales to zero

---

## Quick Reference

### Start Everything
```bash
docker-compose up -d
```

### Stop Everything
```bash
docker-compose down
```

### View Logs
```bash
docker-compose logs -f scheduler
docker-compose logs -f backend
```

### Test Health

**Bash/Linux/Mac:**
```bash
curl http://localhost:8000/health/all
```

**PowerShell/Windows:**
```powershell
Invoke-WebRequest -Uri http://localhost:8000/health/all | Select-Object -ExpandProperty Content
```

### Manual Feed Fetch

**Bash/Linux/Mac:**
```bash
curl -X POST "http://localhost:8000/gtfs-rt/fetch?feed_type=vehicle_positions"
```

**PowerShell/Windows:**
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/gtfs-rt/fetch?feed_type=vehicle_positions" -Method POST
```

### Check Cloud Storage Status

**Bash/Linux/Mac:**
```bash
curl http://localhost:8000/gtfs-rt/status | jq .cloud_storage
```

**PowerShell/Windows:**
```powershell
$response = Invoke-WebRequest -Uri http://localhost:8000/gtfs-rt/status
$json = $response.Content | ConvertFrom-Json
$json.cloud_storage
```

---

## Troubleshooting

### Services Won't Start
- Check Docker is running: `docker ps`
- Check ports aren't in use: `netstat -tulpn | grep 8000`
- Check logs: `docker-compose logs`

### Scheduler Not Running
- Check environment variables: `docker-compose exec scheduler env | grep MTA`
- Check Prefect: `docker-compose exec scheduler python -c "import prefect; print(prefect.__version__)"`
- View logs: `docker-compose logs -f scheduler`

### Cloud Storage Not Working
- Verify credentials in `.env`
- Check bucket exists and is accessible
- Check logs: `docker-compose logs backend | grep -i cloud`

### API Connection Fails
- Verify MTA_API_KEY is set correctly
- Test API key: `curl -H "x-api-key: YOUR_KEY" https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs`
- Check network connectivity from container

---

For more details, see:
- [Quick Start Guide](QUICK_START.md)
- [Cloud Storage Setup](CLOUD_STORAGE_SETUP.md)
- [Scheduler Documentation](../etl/SCHEDULER_README.md)

