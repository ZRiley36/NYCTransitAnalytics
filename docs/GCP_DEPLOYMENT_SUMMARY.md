# GCP Deployment Summary

Quick reference for deploying NYC Transit Analytics on Google Cloud Platform.

## 🎯 Three Ways to Deploy

### 1. Automated Script (Fastest)

```bash
cd infrastructure/gcp
chmod +x setup.sh deploy.sh
./setup.sh    # Sets up infrastructure
./deploy.sh   # Deploys services
```

**Time: ~15 minutes**

### 2. Terraform (Infrastructure as Code)

```bash
cd infrastructure/terraform/gcp
terraform init
terraform plan
terraform apply
```

**Time: ~10 minutes setup, then deploy services**

### 3. Manual (Step-by-Step)

Follow [GCP Deployment Guide](./GCP_DEPLOYMENT_GUIDE.md) or [Quick Start](./GCP_QUICK_START.md)

**Time: ~30 minutes**

## 📋 What Gets Deployed

| Service | Purpose | Cost (Dev) |
|---------|---------|------------|
| **Cloud Storage** | Raw JSON & Parquet files | ~$1/month |
| **Cloud SQL** | PostgreSQL database | ~$7.50/month |
| **Memorystore** | Redis cache | ~$30/month |
| **Cloud Run** | API & Ingestion services | ~$0-5/month |
| **Cloud Dataproc** | Spark ETL processing | ~$10-20/month (on-demand) |
| **BigQuery** | Data warehouse | ~$0-5/month (free tier) |
| **Cloud Scheduler** | Scheduled jobs | Free |

**Total: ~$50-75/month** for development

## 🚀 Quick Deploy Commands

```bash
# 1. Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 2. Setup infrastructure
cd infrastructure/gcp && ./setup.sh

# 3. Store secrets
echo -n "YOUR_MTA_API_KEY" | gcloud secrets create mta-api-key --data-file=-

# 4. Deploy ingestion
cd cloud-run-ingestion
gcloud run deploy gtfs-rt-ingestion --source . --region=us-central1

# 5. Deploy API
cd ../../backend
gcloud run deploy nyc-transit-api --source . --region=us-central1

# 6. Schedule ingestion
gcloud scheduler jobs create http gtfs-rt-schedule \
    --schedule="*/30 * * * *" \
    --uri="$(gcloud run services describe gtfs-rt-ingestion --format='value(status.url)')"
```

## 📚 Documentation

- **[GCP Quick Start](./GCP_QUICK_START.md)** - Get started in 30 minutes
- **[GCP Deployment Guide](./GCP_DEPLOYMENT_GUIDE.md)** - Complete detailed guide
- **[Infrastructure README](../infrastructure/gcp/README.md)** - Infrastructure files

## ✅ Acceptance Checklist

- [ ] Infrastructure created (Storage, SQL, Redis, BigQuery)
- [ ] Ingestion service deployed and working
- [ ] Spark ETL can read from Cloud Storage
- [ ] Spark ETL writes Parquet to staging bucket
- [ ] BigQuery loader can read from staging bucket
- [ ] Data is queryable in BigQuery
- [ ] Cloud Scheduler triggers ingestion
- [ ] API deployed and accessible

## 🔧 Troubleshooting

See [GCP Deployment Guide](./GCP_DEPLOYMENT_GUIDE.md) troubleshooting section.

