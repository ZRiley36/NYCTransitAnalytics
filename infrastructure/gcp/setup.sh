#!/bin/bash
# GCP Setup Script
# Automated setup of NYC Transit Analytics on GCP

set -e

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project)}
REGION=${REGION:-us-central1}
ENVIRONMENT=${ENVIRONMENT:-dev}

echo "=========================================="
echo "GCP Setup for NYC Transit Analytics"
echo "=========================================="
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"
echo ""

# Check if project is set
if [ -z "$PROJECT_ID" ]; then
    echo "ERROR: Project ID not set"
    echo "Set GOOGLE_CLOUD_PROJECT or run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

# Enable APIs
echo "Enabling required APIs..."
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
    secretmanager.googleapis.com \
    --project=$PROJECT_ID

# Create Storage Buckets
echo "Creating Cloud Storage buckets..."
gsutil mb -l $REGION gs://${PROJECT_ID}-nyc-transit-raw || echo "Bucket may already exist"
gsutil mb -l $REGION gs://${PROJECT_ID}-nyc-transit-staging || echo "Bucket may already exist"

# Create Cloud SQL
echo "Creating Cloud SQL instance..."
gcloud sql instances create nyc-transit-db-$ENVIRONMENT \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --root-password=$(openssl rand -base64 16) \
    --project=$PROJECT_ID || echo "SQL instance may already exist"

gcloud sql databases create nyc_transit \
    --instance=nyc-transit-db-$ENVIRONMENT \
    --project=$PROJECT_ID || echo "Database may already exist"

# Create Redis
echo "Creating Memorystore Redis instance..."
gcloud redis instances create nyc-transit-redis-$ENVIRONMENT \
    --size=1 \
    --region=$REGION \
    --redis-version=REDIS_7_0 \
    --project=$PROJECT_ID || echo "Redis instance may already exist"

# Create BigQuery Dataset
echo "Creating BigQuery dataset..."
bq mk --dataset \
    --location=$REGION \
    --project_id=$PROJECT_ID \
    nyc_transit || echo "Dataset may already exist"

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Store secrets:"
echo "   echo -n 'YOUR_MTA_API_KEY' | gcloud secrets create mta-api-key --data-file=-"
echo ""
echo "2. Deploy ingestion service:"
echo "   gcloud run deploy gtfs-rt-ingestion --source . --region=$REGION"
echo ""
echo "3. Deploy API:"
echo "   gcloud run deploy nyc-transit-api --source ./backend --region=$REGION"
echo ""
echo "4. Set up Cloud Scheduler jobs"
echo ""

