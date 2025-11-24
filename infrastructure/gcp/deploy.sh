#!/bin/bash
# Complete GCP Deployment Script

set -e

PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project)}
REGION=${REGION:-us-central1}

echo "=========================================="
echo "Deploying NYC Transit Analytics to GCP"
echo "=========================================="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Step 1: Setup infrastructure
echo "Step 1: Setting up infrastructure..."
cd infrastructure/gcp
./setup.sh
cd ../..

# Step 2: Upload code to Cloud Storage
echo "Step 2: Uploading code to Cloud Storage..."
gsutil mb -l $REGION gs://${PROJECT_ID}-nyc-transit-code || echo "Code bucket exists"
gsutil -m cp -r etl/*.py gs://${PROJECT_ID}-nyc-transit-code/

# Step 3: Deploy ingestion service
echo "Step 3: Deploying ingestion service..."
cd infrastructure/gcp/cloud-run-ingestion
gcloud run deploy gtfs-rt-ingestion \
    --source . \
    --region=$REGION \
    --allow-unauthenticated \
    --set-env-vars GCS_BUCKET_NAME=${PROJECT_ID}-nyc-transit-raw \
    --set-secrets MTA_API_KEY=mta-api-key:latest \
    --memory=512MB \
    --timeout=540s
cd ../../..

# Step 4: Deploy API
echo "Step 4: Deploying API..."
cd backend
gcloud run deploy nyc-transit-api \
    --source . \
    --region=$REGION \
    --allow-unauthenticated \
    --set-env-vars DATABASE_URL=postgresql://postgres:$(gcloud sql users list --instance=nyc-transit-db --format="value(password)")@/nyc_transit?host=/cloudsql/${PROJECT_ID}:${REGION}:nyc-transit-db \
    --add-cloudsql-instances=${PROJECT_ID}:${REGION}:nyc-transit-db \
    --set-env-vars REDIS_HOST=$(gcloud redis instances describe nyc-transit-redis --region=$REGION --format="value(host)") \
    --set-secrets MTA_API_KEY=mta-api-key:latest
cd ..

# Step 5: Set up Cloud Scheduler
echo "Step 5: Setting up Cloud Scheduler..."
INGESTION_URL=$(gcloud run services describe gtfs-rt-ingestion --region=$REGION --format="value(status.url)")

gcloud scheduler jobs create http gtfs-rt-ingestion-schedule \
    --location=$REGION \
    --schedule="*/30 * * * *" \
    --uri="${INGESTION_URL}" \
    --http-method=GET \
    --attempt-deadline=600s || echo "Scheduler job may already exist"

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Services deployed:"
echo "- Ingestion: $INGESTION_URL"
echo "- API: $(gcloud run services describe nyc-transit-api --region=$REGION --format="value(status.url)")"
echo ""
echo "Next steps:"
echo "1. Test ingestion: curl $INGESTION_URL"
echo "2. Run Spark ETL manually or set up scheduled job"
echo "3. Load to BigQuery: python etl/warehouse_loader.py --warehouse bigquery --feed-type all"
echo ""

