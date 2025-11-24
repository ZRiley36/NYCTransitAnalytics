# GCP Deployment Guide

Complete guide to deploying NYC Transit Analytics on Google Cloud Platform.

## Architecture Overview

```
┌─────────────────┐
│  Cloud Scheduler│  (Triggers every 30 min)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Cloud Function │  (GTFS-RT Ingestion)
│  / Cloud Run    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Cloud Storage   │  (Raw JSON files)
│   (Raw Data)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Cloud Dataproc │  (Spark ETL Job)
│   (Spark ETL)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Cloud Storage   │  (Parquet staging)
│  (Staging)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    BigQuery     │  (Data Warehouse)
│  (Analytics)    │
└─────────────────┘

┌─────────────────┐
│   Cloud Run     │  (FastAPI Backend)
│    (API)        │
└─────────────────┘

┌─────────────────┐
│ Cloud SQL       │  (PostgreSQL)
│   (Metadata)    │
└─────────────────┘

┌─────────────────┐
│  Memorystore    │  (Redis)
│   (Cache)       │
└─────────────────┘
```

## Prerequisites

1. **Google Cloud Account**
   - Create account at https://cloud.google.com
   - Enable billing

2. **Google Cloud SDK (gcloud)**
   ```bash
   # Install gcloud CLI
   # Windows: https://cloud.google.com/sdk/docs/install
   # Or use Cloud Shell in browser
   ```

3. **Authentication**
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

4. **Set Project**
   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```

## Quick Start (Automated)

### Option 1: Terraform (Recommended)

```bash
cd infrastructure/terraform/gcp
terraform init
terraform plan
terraform apply
```

### Option 2: gcloud Scripts

```bash
cd infrastructure/gcp
./setup.sh
```

### Option 3: Manual Setup

Follow the sections below step-by-step.

## Manual Setup Steps

### Step 1: Enable Required APIs

```bash
gcloud services enable \
    cloudfunctions.googleapis.com \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    dataproc.googleapis.com \
    storage-component.googleapis.com \
    bigquery.googleapis.com \
    sql-component.googleapis.com \
    redis.googleapis.com \
    cloudscheduler.googleapis.com \
    secretmanager.googleapis.com
```

### Step 2: Create Cloud Storage Buckets

```bash
PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"

# Raw data bucket
gsutil mb -l ${REGION} gs://${PROJECT_ID}-nyc-transit-raw

# Staging bucket
gsutil mb -l ${REGION} gs://${PROJECT_ID}-nyc-transit-staging

# Set lifecycle policies (optional - auto-delete old data)
gsutil lifecycle set lifecycle-config.json gs://${PROJECT_ID}-nyc-transit-raw
```

### Step 3: Create Cloud SQL (PostgreSQL)

```bash
gcloud sql instances create nyc-transit-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=${REGION} \
    --root-password=CHANGE_ME

# Create database
gcloud sql databases create nyc_transit --instance=nyc-transit-db

# Get connection name
gcloud sql instances describe nyc-transit-db --format="value(connectionName)"
```

### Step 4: Create Memorystore (Redis)

```bash
gcloud redis instances create nyc-transit-redis \
    --size=1 \
    --region=${REGION} \
    --redis-version=REDIS_7_0

# Get Redis IP
gcloud redis instances describe nyc-transit-redis \
    --region=${REGION} \
    --format="value(host)"
```

### Step 5: Store Secrets

```bash
# MTA API Key
echo -n "YOUR_MTA_API_KEY" | gcloud secrets create mta-api-key --data-file=-

# Database password
echo -n "YOUR_DB_PASSWORD" | gcloud secrets create db-password --data-file=-
```

### Step 6: Deploy Cloud Function / Cloud Run (Data Ingestion)

#### Option A: Cloud Function

```bash
cd backend
gcloud functions deploy gtfs-rt-ingestion \
    --runtime python311 \
    --trigger-http \
    --allow-unauthenticated \
    --set-env-vars MTA_API_KEY=$(gcloud secrets versions access latest --secret=mta-api-key) \
    --set-env-vars GCS_BUCKET_NAME=${PROJECT_ID}-nyc-transit-raw \
    --region=${REGION} \
    --memory=512MB \
    --timeout=540s
```

#### Option B: Cloud Run (Recommended)

See `infrastructure/gcp/cloud-run-ingestion/` for full setup.

```bash
cd infrastructure/gcp/cloud-run-ingestion
gcloud run deploy gtfs-rt-ingestion \
    --source . \
    --region=${REGION} \
    --allow-unauthenticated \
    --set-env-vars GCS_BUCKET_NAME=${PROJECT_ID}-nyc-transit-raw \
    --set-secrets MTA_API_KEY=mta-api-key:latest
```

### Step 7: Deploy Spark ETL to Dataproc

```bash
# Create Dataproc cluster
gcloud dataproc clusters create nyc-transit-etl \
    --region=${REGION} \
    --zone=${REGION}-a \
    --master-machine-type=n1-standard-2 \
    --master-boot-disk-size=50GB \
    --num-workers=2 \
    --worker-machine-type=n1-standard-2 \
    --worker-boot-disk-size=50GB \
    --image-version=2.1-debian11 \
    --properties spark:spark.sql.adaptive.enabled=true

# Submit Spark job
gcloud dataproc jobs submit pyspark \
    etl/spark_etl.py \
    --cluster=nyc-transit-etl \
    --region=${REGION} \
    --py-files=etl/spark_etl.py \
    --properties=spark.executor.memory=4g,spark.executor.cores=2 \
    -- \
    --raw-path gs://${PROJECT_ID}-nyc-transit-raw \
    --staging-path gs://${PROJECT_ID}-nyc-transit-staging
```

### Step 8: Set Up Cloud Scheduler

```bash
# Schedule data ingestion (every 30 minutes)
gcloud scheduler jobs create http gtfs-rt-ingestion-schedule \
    --location=${REGION} \
    --schedule="*/30 * * * *" \
    --uri="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/gtfs-rt-ingestion" \
    --http-method=GET

# Schedule ETL job (every hour)
gcloud scheduler jobs create http spark-etl-schedule \
    --location=${REGION} \
    --schedule="0 * * * *" \
    --uri="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/trigger-dataproc-job" \
    --http-method=POST
```

### Step 9: Load Data to BigQuery

```bash
# Set environment variables
export GOOGLE_CLOUD_PROJECT=${PROJECT_ID}
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Load data
python etl/warehouse_loader.py \
    --warehouse bigquery \
    --feed-type all \
    --staging-path gs://${PROJECT_ID}-nyc-transit-staging \
    --mode append
```

### Step 10: Deploy FastAPI Backend to Cloud Run

```bash
cd backend
gcloud run deploy nyc-transit-api \
    --source . \
    --region=${REGION} \
    --allow-unauthenticated \
    --set-env-vars DATABASE_URL=postgresql://user:pass@/nyc_transit?host=/cloudsql/${PROJECT_ID}:${REGION}:nyc-transit-db \
    --add-cloudsql-instances=${PROJECT_ID}:${REGION}:nyc-transit-db \
    --set-env-vars REDIS_HOST=$(gcloud redis instances describe nyc-transit-redis --region=${REGION} --format="value(host)") \
    --set-secrets MTA_API_KEY=mta-api-key:latest
```

## Infrastructure as Code

### Terraform

See `infrastructure/terraform/gcp/` for complete Terraform configuration.

### Cloud Build

See `infrastructure/gcp/cloudbuild.yaml` for CI/CD pipeline.

## Cost Estimation

### Small Scale (Development)

| Service | Cost/Month |
|---------|-----------|
| Cloud Storage (50 GB) | $1.00 |
| Cloud SQL (db-f1-micro) | $7.50 |
| Memorystore (1 GB Redis) | $30.00 |
| Cloud Run (API, low traffic) | $0.00-5.00 |
| Cloud Functions (Ingestion) | $0.00-2.00 |
| Dataproc (on-demand, 1 hour/day) | $10.00-20.00 |
| BigQuery (10 GB + queries) | $0.00-5.00 |
| **Total** | **~$50-75/month** |

### Production Scale

| Service | Cost/Month |
|---------|-----------|
| Cloud Storage (500 GB) | $10.00 |
| Cloud SQL (db-n1-standard-1) | $50.00 |
| Memorystore (5 GB Redis) | $150.00 |
| Cloud Run (API) | $20.00-50.00 |
| Cloud Functions | $5.00-10.00 |
| Dataproc (persistent cluster) | $200.00-300.00 |
| BigQuery | $20.00-50.00 |
| **Total** | **~$450-600/month** |

## Monitoring & Logging

### Cloud Monitoring

```bash
# View logs
gcloud logging read "resource.type=cloud_function" --limit=50

# Create dashboard
# Go to Cloud Console → Monitoring → Dashboards
```

### Cloud Logging

All services automatically log to Cloud Logging:
- Cloud Functions/Cloud Run: Application logs
- Dataproc: Spark job logs
- Cloud SQL: Database logs

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   # Grant necessary roles
   gcloud projects add-iam-policy-binding ${PROJECT_ID} \
       --member=serviceAccount:YOUR_SERVICE_ACCOUNT \
       --role=roles/storage.admin
   ```

2. **Cold Starts (Cloud Functions)**
   - Use Cloud Run instead (keeps container warm)
   - Or use minimum instances

3. **Dataproc Costs**
   - Use serverless Dataproc (Dataproc Serverless)
   - Or create clusters on-demand

## Next Steps

1. Set up monitoring and alerts
2. Configure auto-scaling
3. Set up backup policies
4. Implement CI/CD pipeline
5. Add security hardening

See detailed sections below for each component.

