# GCP Cost Optimization Guide

How to deploy NYC Transit Analytics on GCP for **under $25/month**.

## Cost-Optimized Architecture

**Key Cost Reductions:**
- ❌ Remove Memorystore (Redis) - $30/month saved
- ✅ Use Dataproc Serverless (pay-per-job) instead of cluster
- ✅ Use Cloud Functions instead of Cloud Run for ingestion
- ✅ Make PostgreSQL optional (use only if API needs it)
- ✅ Optimize storage with lifecycle policies

## Optimized Cost Breakdown

| Service | Cost/Month | Notes |
|---------|-----------|-------|
| Cloud Storage (50 GB) | $1.00 | Lifecycle policy auto-deletes old data |
| Cloud SQL (db-f1-micro) | $0.00 | **OPTIONAL** - Skip if API doesn't need DB |
| Memorystore (Redis) | $0.00 | **REMOVED** - Use in-memory cache or skip |
| Cloud Functions (Ingestion) | $0.00-1.00 | Free tier covers most usage |
| Cloud Run (API, minimal) | $0.00-2.00 | Free tier: 2M requests/month |
| Dataproc Serverless | $5.00-10.00 | Pay per job, not hourly cluster |
| BigQuery | $0.00-5.00 | Free tier: 10 GB storage, 1 TB queries |
| **Total** | **~$6-20/month** | ✅ Well under $25! |

## What You Get

### Minimal Setup (ETL Pipeline Only) - **~$6-15/month**

- ✅ Cloud Storage (raw + staging)
- ✅ Cloud Functions (data ingestion)
- ✅ Dataproc Serverless (Spark ETL)
- ✅ BigQuery (data warehouse)
- ✅ Cloud Scheduler (triggers)

**No API, No PostgreSQL, No Redis** - Just the data pipeline!

### With API (Optimized) - **~$10-20/month**

Everything above, plus:
- ✅ Cloud Run (minimal API - health checks, basic endpoints)
- ❌ Skip PostgreSQL (if API doesn't need persistent data)
- ❌ Skip Redis (use in-memory cache or skip entirely)

## Implementation Steps

### Step 1: Skip Redis (Save $30/month)

Redis is only used for caching in the API. For cost optimization:
- **Option A**: Remove Redis dependency entirely
- **Option B**: Use in-memory cache in Cloud Run
- **Option C**: Use Cloud Firestore (free tier: 1 GB storage)

### Step 2: Make PostgreSQL Optional (Save $7.50/month)

If the API doesn't need persistent storage:
- Skip Cloud SQL entirely
- API becomes stateless (just health checks and GTFS endpoints)

### Step 3: Use Dataproc Serverless (Save $10-15/month)

Instead of persistent cluster, use serverless jobs:
- Pay only when ETL runs
- No cluster running 24/7
- Estimated: $0.10-0.50 per job run

### Step 4: Use Cloud Functions for Ingestion (Save $2-5/month)

Instead of Cloud Run:
- Cloud Functions has generous free tier
- Only pay for execution time
- Perfect for scheduled ingestion

### Step 5: Optimize Storage Costs

```bash
# Auto-delete files older than 7 days (raw data)
gsutil lifecycle set lifecycle-raw.json gs://PROJECT-nyc-transit-raw

# Lifecycle config: lifecycle-raw.json
{
  "lifecycle": {
    "rule": [{
      "action": {"type": "Delete"},
      "condition": {"age": 7}
    }]
  }
}
```

## Optimized Terraform Configuration

See `infrastructure/terraform/gcp/cost-optimized/` for minimal infrastructure:
- No Cloud SQL
- No Memorystore
- Dataproc Serverless only
- Cloud Functions for ingestion

## Minimal Deployment Script

Create `infrastructure/gcp/setup-cost-optimized.sh` that:
- Creates only essential services
- Skips expensive resources
- Sets up lifecycle policies

## Cost Monitoring

Set up budget alerts:
```bash
# Create budget alert at $20/month
gcloud billing budgets create \
    --billing-account=BILLING_ACCOUNT_ID \
    --display-name="NYC Transit Analytics Budget" \
    --budget-amount=20USD \
    --threshold-rule=percent=80 \
    --threshold-rule=percent=100
```

## Next Steps

1. Create cost-optimized Terraform config
2. Create minimal deployment script
3. Remove Redis dependency (or make optional)
4. Make PostgreSQL optional
5. Update documentation

