# GCP Infrastructure Setup

Infrastructure setup scripts and configurations for deploying NYC Transit Analytics on Google Cloud Platform.

## Quick Start

### Option 1: Automated Setup Script

```bash
# Make scripts executable (Linux/Mac)
chmod +x infrastructure/gcp/*.sh

# Run setup
cd infrastructure/gcp
./setup.sh
```

### Option 2: Terraform

```bash
cd infrastructure/terraform/gcp

# Initialize
terraform init

# Copy and edit variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your project ID

# Plan and apply
terraform plan
terraform apply
```

### Option 3: Manual Setup

See [GCP Deployment Guide](../../docs/GCP_DEPLOYMENT_GUIDE.md) for step-by-step instructions.

## Files Overview

- `setup.sh` - Automated infrastructure setup
- `deploy.sh` - Complete deployment script
- `cloudbuild.yaml` - CI/CD pipeline configuration
- `dataproc-serverless-job.yaml` - Spark ETL job configuration
- `cloud-run-ingestion/` - Cloud Run service for data ingestion

## Prerequisites

1. Google Cloud SDK installed
2. Authenticated: `gcloud auth login`
3. Project set: `gcloud config set project YOUR_PROJECT_ID`
4. Billing enabled on project

## Cost Estimation

See main [GCP Deployment Guide](../../docs/GCP_DEPLOYMENT_GUIDE.md) for cost breakdown.

## Next Steps

After setup:
1. Store secrets (MTA API key, etc.)
2. Deploy services (ingestion, API)
3. Set up Cloud Scheduler
4. Run Spark ETL
5. Load to BigQuery

