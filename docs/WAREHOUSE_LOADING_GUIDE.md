# Warehouse Loading - Complete Guide

This guide covers loading ETL output into data warehouses (Redshift, BigQuery, Snowflake).

## Overview

The warehouse loading system takes Parquet files from the Spark ETL staging area and loads them into your chosen data warehouse, making the data queryable for analytics.

## Quick Start

### 1. Run Spark ETL

First, ensure your data is processed and staged:

```bash
# Process all feeds
python etl/spark_etl.py

# Verify Parquet files exist
ls data/staging/vehicle_positions/
ls data/staging/trip_updates/
```

### 2. Configure Warehouse Credentials

Set environment variables for your warehouse (see [Configuration](#configuration) below).

### 3. Install Warehouse Dependencies

```bash
# For BigQuery
pip install google-cloud-bigquery[pandas] pandas pyarrow

# For Redshift
pip install sqlalchemy psycopg2-binary boto3 pandas pyarrow

# For Snowflake
pip install snowflake-connector-python[pandas] pandas pyarrow

# Or install all
pip install -r etl/requirements-warehouse.txt
```

### 4. Load Data

```bash
# Load all feeds to BigQuery
python etl/warehouse_loader.py \
    --warehouse bigquery \
    --feed-type all \
    --schema nyc_transit \
    --mode append
```

## Complete ETL Pipeline

```bash
# Step 1: Run Spark ETL (processes raw JSON → Parquet)
python etl/spark_etl.py

# Step 2: Load to warehouse (Parquet → Warehouse tables)
python etl/warehouse_loader.py --warehouse bigquery --feed-type all
```

## Configuration

### BigQuery Setup

1. **Create Service Account**:
   - Go to Google Cloud Console → IAM & Admin → Service Accounts
   - Create new service account with BigQuery Data Editor role
   - Download JSON key file

2. **Set Environment Variables**:
   ```bash
   export GOOGLE_CLOUD_PROJECT="your-project-id"
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
   export BIGQUERY_DATASET="nyc_transit"  # Optional
   ```

3. **Load Data**:
   ```bash
   python etl/warehouse_loader.py --warehouse bigquery --feed-type all
   ```

### Redshift Setup

1. **Get Connection Details**:
   - AWS Console → Redshift → Clusters
   - Note: endpoint, port, database name, username, password

2. **Set Environment Variables**:
   ```bash
   export REDSHIFT_CONNECTION_STRING="postgresql://user:password@host:5439/database"
   # Optional: For S3 COPY command
   export REDSHIFT_S3_BUCKET="your-bucket"
   export REDSHIFT_IAM_ROLE="arn:aws:iam::..."
   ```

3. **Load Data**:
   ```bash
   python etl/warehouse_loader.py --warehouse redshift --feed-type all
   ```

### Snowflake Setup

1. **Get Account Details**:
   - Snowflake Console → Account Info
   - Note: account identifier, username, password

2. **Set Environment Variables**:
   ```bash
   export SNOWFLAKE_ACCOUNT="your-account"
   export SNOWFLAKE_USER="your-user"
   export SNOWFLAKE_PASSWORD="your-password"
   export SNOWFLAKE_WAREHOUSE="COMPUTE_WH"  # Optional
   export SNOWFLAKE_DATABASE="NYC_TRANSIT"  # Optional
   ```

3. **Load Data**:
   ```bash
   python etl/warehouse_loader.py --warehouse snowflake --feed-type all
   ```

## Query Examples

After loading, query your data:

### Vehicle Positions by Line

```sql
-- BigQuery
SELECT 
    line,
    COUNT(*) as vehicle_count,
    AVG(speed) as avg_speed
FROM `nyc_transit.vehicle_positions`
WHERE vehicle_timestamp_dt >= CURRENT_TIMESTAMP() - INTERVAL 1 HOUR
GROUP BY line
ORDER BY vehicle_count DESC;

-- Redshift / Snowflake
SELECT 
    line,
    COUNT(*) as vehicle_count,
    AVG(speed) as avg_speed
FROM nyc_transit.vehicle_positions
WHERE vehicle_timestamp_dt >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
GROUP BY line
ORDER BY vehicle_count DESC;
```

### Delays by Line

```sql
-- BigQuery
SELECT 
    line,
    AVG(delay_seconds) as avg_delay_seconds,
    MAX(delay_seconds) as max_delay_seconds,
    COUNT(*) as update_count
FROM `nyc_transit.trip_updates`
WHERE departure_time_dt >= CURRENT_TIMESTAMP() - INTERVAL 1 DAY
  AND delay_seconds IS NOT NULL
GROUP BY line
ORDER BY avg_delay_seconds DESC;

-- Redshift / Snowflake  
SELECT 
    line,
    AVG(delay_seconds) as avg_delay_seconds,
    MAX(delay_seconds) as max_delay_seconds,
    COUNT(*) as update_count
FROM nyc_transit.trip_updates
WHERE departure_time_dt >= CURRENT_TIMESTAMP - INTERVAL '1 day'
  AND delay_seconds IS NOT NULL
GROUP BY line
ORDER BY avg_delay_seconds DESC;
```

### Real-time Vehicle Locations

```sql
-- Get latest position for each vehicle
SELECT DISTINCT ON (vehicle_id)
    vehicle_id,
    train_id,
    line,
    latitude,
    longitude,
    speed,
    vehicle_timestamp_dt
FROM nyc_transit.vehicle_positions
WHERE vehicle_timestamp_dt >= CURRENT_TIMESTAMP - INTERVAL '5 minutes'
ORDER BY vehicle_id, vehicle_timestamp_dt DESC;
```

## Integration with Prefect

Automate the complete pipeline:

```python
from prefect import task, flow
from etl.spark_etl import GTFSRTETL
from etl.warehouse_loader import load_to_warehouse

@task
def run_spark_etl():
    etl = GTFSRTETL(
        raw_data_path="./data/gtfs_rt",
        staging_path="./data/staging"
    )
    try:
        etl.process_all()
    finally:
        etl.stop()

@task
def load_to_warehouse_task():
    load_to_warehouse(
        warehouse_type="bigquery",
        feed_type="all",
        schema_name="nyc_transit",
        mode="append"
    )

@flow(name="ETL Pipeline")
def etl_pipeline():
    run_spark_etl()
    load_to_warehouse_task()

if __name__ == "__main__":
    etl_pipeline()
```

## Acceptance Criteria

✅ **Data is queryable in warehouse**: After running the loader, you should be able to query tables directly in your warehouse.

**Verification**:
```sql
-- Check row counts
SELECT COUNT(*) FROM nyc_transit.vehicle_positions;
SELECT COUNT(*) FROM nyc_transit.trip_updates;

-- Sample data
SELECT * FROM nyc_transit.vehicle_positions LIMIT 10;
```

## Troubleshooting

See the main [Warehouse Loader README](../etl/WAREHOUSE_LOADER_README.md) for detailed troubleshooting.

## Next Steps

- Set up scheduled loading (via Prefect or cron)
- Create views for common queries
- Set up data retention policies
- Implement incremental loading strategies

