# Cloud Storage Setup Guide

## Overview

The GTFS-RT connector can automatically upload raw feed files (both `.pb` and `.json`) to AWS S3 or Google Cloud Storage. Files are organized by date in daily folders: `YYYY/MM/DD/filename`.

## AWS S3 Setup

### 1. Create S3 Bucket

```bash
aws s3 mb s3://nyc-transit-gtfs-rt --region us-east-1
```

### 2. Configure IAM User

Create an IAM user with S3 write permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::nyc-transit-gtfs-rt/*"
    }
  ]
}
```

### 3. Set Environment Variables

**Option A: `.env` file (recommended)**
```bash
CLOUD_STORAGE_TYPE=s3
S3_BUCKET_NAME=nyc-transit-gtfs-rt
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_REGION=us-east-1
```

**Option B: Environment variables**
```bash
export CLOUD_STORAGE_TYPE=s3
export S3_BUCKET_NAME=nyc-transit-gtfs-rt
export AWS_ACCESS_KEY_ID=your_access_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_access_key
export AWS_REGION=us-east-1
```

**Option C: Docker Compose**
Update `docker-compose.yml` or create `.env` file with the variables above.

## Google Cloud Storage Setup

### 1. Create GCS Bucket

```bash
gsutil mb -p your-project-id -l us-east1 gs://nyc-transit-gtfs-rt
```

### 2. Create Service Account

```bash
gcloud iam service-accounts create gtfs-rt-uploader \
    --display-name="GTFS-RT Uploader"

gcloud projects add-iam-policy-binding your-project-id \
    --member="serviceAccount:gtfs-rt-uploader@your-project-id.iam.gserviceaccount.com" \
    --role="roles/storage.objectCreator"
```

### 3. Download Credentials

```bash
gcloud iam service-accounts keys create credentials.json \
    --iam-account=gtfs-rt-uploader@your-project-id.iam.gserviceaccount.com
```

### 4. Set Environment Variables

**Option A: `.env` file**
```bash
CLOUD_STORAGE_TYPE=gcs
GCS_BUCKET_NAME=nyc-transit-gtfs-rt
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

**Option B: Mount credentials in Docker**
```yaml
volumes:
  - ./credentials.json:/app/credentials.json
environment:
  - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json
```

## File Organization

Files are automatically organized by date:

```
bucket/
├── 2025/
│   ├── 11/
│   │   ├── 18/
│   │   │   ├── vehicle_positions_20251118_120000.pb
│   │   │   ├── vehicle_positions_20251118_120000.json
│   │   │   ├── trip_updates_20251118_120005.pb
│   │   │   └── trip_updates_20251118_120005.json
│   │   └── 19/
│   │       └── ...
```

## Testing

### 1. Check Status

```bash
curl http://localhost:8000/gtfs-rt/status
```

Response includes cloud storage stats:
```json
{
  "cloud_storage": {
    "enabled": true,
    "provider": "S3StorageProvider",
    "total_uploads": 100,
    "successful_uploads": 98,
    "failed_uploads": 2
  }
}
```

### 2. Manual Upload Test

Start the connector and check logs:
```bash
docker-compose logs -f backend
```

Look for:
```
INFO: Uploaded to S3: s3://nyc-transit-gtfs-rt/2025/11/18/vehicle_positions_20251118_120000.pb
```

### 3. Verify Files in Bucket

**S3:**
```bash
aws s3 ls s3://nyc-transit-gtfs-rt/2025/11/18/
```

**GCS:**
```bash
gsutil ls gs://nyc-transit-gtfs-rt/2025/11/18/
```

## Acceptance Criteria

✅ **Raw files appear in bucket daily** - Files are automatically organized by date (YYYY/MM/DD/)

### Verification Steps:

1. Start connector: `POST /gtfs-rt/start`
2. Wait for files to be uploaded
3. Check bucket: Files should appear in daily folders
4. Check status: `GET /gtfs-rt/status` shows upload statistics

## Troubleshooting

### Cloud Storage Not Working

1. **Check if enabled:**
   ```bash
   curl http://localhost:8000/gtfs-rt/status | jq .cloud_storage.enabled
   ```

2. **Check credentials:**
   - S3: Verify AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
   - GCS: Verify GOOGLE_APPLICATION_CREDENTIALS path

3. **Check bucket permissions:**
   - S3: User needs `s3:PutObject` permission
   - GCS: Service account needs `storage.objectCreator` role

4. **Check logs:**
   ```bash
   docker-compose logs backend | grep -i "cloud\|storage\|s3\|gcs"
   ```

### Files Not Appearing

- Files are uploaded **after** local save
- Check that connector is running: `GET /gtfs-rt/status`
- Verify network connectivity from container
- Check bucket exists and is accessible

## Cost Considerations

**S3 Pricing (approximate):**
- Storage: $0.023/GB/month
- PUT requests: $0.005 per 1,000 requests
- Example: 1,000 files/day × 30 days = ~$0.45/month in PUT requests

**GCS Pricing (approximate):**
- Storage: $0.020/GB/month
- Class A operations (uploads): $0.05 per 10,000 operations
- Example: 1,000 files/day × 30 days = ~$0.15/month in operations

## Disabling Cloud Storage

To disable cloud storage, simply don't set `CLOUD_STORAGE_TYPE` or set it to empty:

```bash
# Remove from .env or don't set it
# CLOUD_STORAGE_TYPE=
```

Files will still be saved locally.


