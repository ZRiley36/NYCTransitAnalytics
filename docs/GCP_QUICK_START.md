# GCP Quick Start Guide

Get NYC Transit Analytics running on Google Cloud Platform in 30 minutes.

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **gcloud CLI** installed: https://cloud.google.com/sdk/docs/install
3. **MTA API Key**: https://api.mta.info/

## Step-by-Step Setup

### 1. Authenticate and Set Project

```bash
# Login
gcloud auth login
gcloud auth application-default login

# Create or select project
gcloud projects create nyc-transit-analytics --name="NYC Transit Analytics"
gcloud config set project nyc-transit-analytics

# Enable billing (via console or)
gcloud billing accounts list
gcloud billing projects link nyc-transit-analytics --billing-account=BILLING_ACCOUNT_ID
```

### 2. Run Automated Setup

```bash
cd infrastructure/gcp
chmod +x setup.sh
./setup.sh
```

This creates:
- ✅ Cloud Storage buckets (raw & staging)
- ✅ Cloud SQL (PostgreSQL)
- ✅ Memorystore (Redis)
- ✅ BigQuery dataset

### 3. Store Secrets

```bash
# MTA API Key (get from https://api.mta.info/)
read -s MTA_API_KEY
echo -n "$MTA_API_KEY" | gcloud secrets create mta-api-key --data-file=-
```

### 4. Deploy Data Ingestion

```bash
cd infrastructure/gcp/cloud-run-ingestion

gcloud run deploy gtfs-rt-ingestion \
    --source . \
    --region=us-central1 \
    --allow-unauthenticated \
    --set-env-vars GCS_BUCKET_NAME=$(gcloud config get-value project)-nyc-transit-raw \
    --set-secrets MTA_API_KEY=mta-api-key:latest \
    --memory=512MB \
    --timeout=540s
```

Get the URL:
```bash
INGESTION_URL=$(gcloud run services describe gtfs-rt-ingestion --region=us-central1 --format="value(status.url)")
echo $INGESTION_URL
```

### 5. Test Ingestion

```bash
curl $INGESTION_URL
```

Check Cloud Storage:
```bash
gsutil ls gs://$(gcloud config get-value project)-nyc-transit-raw/gtfs_rt/
```

### 6. Schedule Automatic Ingestion

```bash
gcloud scheduler jobs create http gtfs-rt-schedule \
    --location=us-central1 \
    --schedule="*/30 * * * *" \
    --uri=$INGESTION_URL \
    --http-method=GET \
    --time-zone="America/New_York"
```

### 7. Run Spark ETL

#### Option A: Dataproc Serverless (Recommended)

```bash
PROJECT_ID=$(gcloud config get-value project)
REGION=us-central1

# Upload Spark ETL code
gsutil mb -l $REGION gs://${PROJECT_ID}-nyc-transit-code
gsutil cp etl/spark_etl.py gs://${PROJECT_ID}-nyc-transit-code/

# Submit job
gcloud dataproc batches submit pyspark \
    gs://${PROJECT_ID}-nyc-transit-code/spark_etl.py \
    --batch=nyc-transit-etl-$(date +%s) \
    --region=$REGION \
    --subnet=default \
    --service-account=$(gcloud iam service-accounts list --filter="displayName:Compute Engine default" --format="value(email)") \
    --project=$PROJECT_ID \
    -- \
    --raw-path gs://${PROJECT_ID}-nyc-transit-raw/gtfs_rt \
    --staging-path gs://${PROJECT_ID}-nyc-transit-staging
```

#### Option B: Dataproc Cluster

```bash
# Create cluster
gcloud dataproc clusters create nyc-transit-etl \
    --region=us-central1 \
    --zone=us-central1-a \
    --master-machine-type=n1-standard-2 \
    --master-boot-disk-size=50GB \
    --num-workers=2 \
    --worker-machine-type=n1-standard-2 \
    --image-version=2.1-debian11

# Submit job
gcloud dataproc jobs submit pyspark \
    etl/spark_etl.py \
    --cluster=nyc-transit-etl \
    --region=us-central1 \
    -- \
    --raw-path gs://${PROJECT_ID}-nyc-transit-raw/gtfs_rt \
    --staging-path gs://${PROJECT_ID}-nyc-transit-staging
```

### 8. Load to BigQuery

```bash
# Set credentials
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
export GOOGLE_APPLICATION_CREDENTIALS=$HOME/.config/gcloud/application_default_credentials.json

# Install dependencies
pip install google-cloud-bigquery[pandas] pandas pyarrow

# Load data
python etl/warehouse_loader.py \
    --warehouse bigquery \
    --feed-type all \
    --staging-path gs://${PROJECT_ID}-nyc-transit-staging \
    --mode append
```

### 9. Query Your Data!

```bash
# Query BigQuery
bq query --use_legacy_sql=false \
  "SELECT line, COUNT(*) as count FROM \`nyc_transit.vehicle_positions\` GROUP BY line LIMIT 10"
```

Or in BigQuery Console:
```sql
SELECT 
    line,
    COUNT(*) as vehicle_count,
    AVG(speed) as avg_speed
FROM `nyc_transit.vehicle_positions`
WHERE vehicle_timestamp_dt >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
GROUP BY line
ORDER BY vehicle_count DESC;
```

## Verify Everything Works

```bash
# 1. Check ingestion is running
gcloud scheduler jobs describe gtfs-rt-schedule --location=us-central1

# 2. Check data in storage
gsutil ls -lh gs://$(gcloud config get-value project)-nyc-transit-raw/gtfs_rt/ | head -5

# 3. Check BigQuery tables
bq ls nyc_transit

# 4. Query data
bq query "SELECT COUNT(*) FROM \`nyc_transit.vehicle_positions\`"
```

## Cost Optimization

- Use **Dataproc Serverless** instead of persistent clusters
- Set Cloud Storage lifecycle policies to auto-delete old data
- Use Cloud SQL with auto-shutdown for dev environments
- Scale down Redis when not needed

## Troubleshooting

See [GCP Deployment Guide](./GCP_DEPLOYMENT_GUIDE.md) for detailed troubleshooting.

## Next Steps

- Set up monitoring and alerts
- Create scheduled Spark ETL job
- Set up automated BigQuery loading
- Create dashboards and reports

