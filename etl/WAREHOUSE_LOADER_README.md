# Warehouse Loading Guide

Loads Parquet files from Spark ETL staging area into data warehouses.

## Supported Warehouses

- ✅ **Amazon Redshift**
- ✅ **Google BigQuery**
- ✅ **Snowflake**

## Installation

### Install Warehouse Dependencies

```bash
# Install all warehouse dependencies (optional, install only what you need)
py -m pip install -r etl/requirements-warehouse.txt

# Or install specific warehouse dependencies:

# Redshift only
py -m pip install sqlalchemy psycopg2-binary boto3 pandas pyarrow

# BigQuery only
py -m pip install google-cloud-bigquery[pandas] pandas pyarrow

# Snowflake only
py -m pip install snowflake-connector-python[pandas] pandas pyarrow
```

## Configuration

### Environment Variables

Each warehouse requires different environment variables:

#### Amazon Redshift

```bash
export REDSHIFT_CONNECTION_STRING="postgresql://user:password@host:5439/database"
export REDSHIFT_S3_BUCKET="your-bucket"  # Optional, for COPY command
export REDSHIFT_S3_PREFIX="staging/"      # Optional
export REDSHIFT_IAM_ROLE="arn:aws:iam::..."  # Optional, for S3 COPY
```

#### Google BigQuery

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export BIGQUERY_DATASET="nyc_transit"  # Optional, defaults to nyc_transit
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

#### Snowflake

```bash
export SNOWFLAKE_ACCOUNT="your-account"
export SNOWFLAKE_USER="your-user"
export SNOWFLAKE_PASSWORD="your-password"
export SNOWFLAKE_WAREHOUSE="your-warehouse"  # Optional
export SNOWFLAKE_DATABASE="NYC_TRANSIT"  # Optional, defaults to NYC_TRANSIT
```

## Testing

Before loading data, test your setup:

```bash
# Test configuration for BigQuery
python etl/test_warehouse_loader.py --warehouse bigquery

# Test configuration only (no connection test)
python etl/test_warehouse_loader.py --warehouse bigquery --check-only

# Inspect Parquet file schema
python etl/test_warehouse_loader.py --inspect vehicle_positions
```

The test script will:
- ✅ Check if staging Parquet files exist
- ✅ Verify warehouse credentials are configured
- ✅ Check if required packages are installed
- ✅ Test connection to warehouse
- ✅ Inspect Parquet file schemas

## Usage

### Command Line

```bash
# Load vehicle positions to BigQuery
python etl/warehouse_loader.py \
    --warehouse bigquery \
    --feed-type vehicle_positions \
    --schema nyc_transit \
    --mode append

# Load trip updates to Redshift
python etl/warehouse_loader.py \
    --warehouse redshift \
    --feed-type trip_updates \
    --schema nyc_transit \
    --mode append

# Load all feeds to Snowflake
python etl/warehouse_loader.py \
    --warehouse snowflake \
    --feed-type all \
    --schema NYC_TRANSIT \
    --mode overwrite
```

### Python API

```python
from etl.warehouse_loader import load_to_warehouse, create_loader

# Simple loading
load_to_warehouse(
    warehouse_type="bigquery",
    feed_type="vehicle_positions",
    schema_name="nyc_transit",
    mode="append"
)

# Advanced usage with custom config
from etl.warehouse_loader import BigQueryLoader

loader = BigQueryLoader(
    staging_path="./data/staging",
    project_id="my-project",
    dataset_id="nyc_transit",
    credentials_path="/path/to/key.json"
)

with loader:
    loader.create_schema("nyc_transit")
    loader.create_table("nyc_transit", "vehicle_positions", VEHICLE_POSITIONS_SCHEMA)
    loader.load_data(
        "nyc_transit",
        "vehicle_positions",
        Path("./data/staging/vehicle_positions"),
        mode="append"
    )
```

## Load Modes

- **`append`**: Adds new data to existing table (default)
- **`overwrite`**: Replaces all data in table

## Schema Definitions

### Vehicle Positions Table

| Column | Type | Description |
|--------|------|-------------|
| `feed_timestamp_dt` | TIMESTAMP | Feed timestamp (normalized) |
| `feed_timestamp_unix` | BIGINT | Feed timestamp (Unix) |
| `gtfs_version` | VARCHAR | GTFS-RT version |
| `entity_id` | VARCHAR | Entity ID |
| `vehicle_id` | VARCHAR | Vehicle ID |
| `train_id` | VARCHAR | Trip ID (train identifier) |
| `line` | VARCHAR | Route ID (subway line) |
| `latitude` | DOUBLE | Vehicle latitude |
| `longitude` | DOUBLE | Vehicle longitude |
| `bearing` | DOUBLE | Vehicle bearing |
| `speed` | DOUBLE | Vehicle speed |
| `vehicle_timestamp_dt` | TIMESTAMP | Vehicle timestamp (normalized) |
| `vehicle_timestamp_unix` | BIGINT | Vehicle timestamp (Unix) |
| `stop_sequence` | INTEGER | Current stop sequence |
| `stop_id` | VARCHAR | Current stop ID |
| `ingestion_timestamp` | TIMESTAMP | When record was ingested |

### Trip Updates Table

| Column | Type | Description |
|--------|------|-------------|
| `feed_timestamp_dt` | TIMESTAMP | Feed timestamp (normalized) |
| `feed_timestamp_unix` | BIGINT | Feed timestamp (Unix) |
| `gtfs_version` | VARCHAR | GTFS-RT version |
| `entity_id` | VARCHAR | Entity ID |
| `train_id` | VARCHAR | Trip ID (train identifier) |
| `line` | VARCHAR | Route ID (subway line) |
| `trip_timestamp_dt` | TIMESTAMP | Trip timestamp (normalized) |
| `trip_timestamp_unix` | BIGINT | Trip timestamp (Unix) |
| `stop_sequence` | INTEGER | Stop sequence |
| `stop_id` | VARCHAR | Stop ID |
| `arrival_time_dt` | TIMESTAMP | Arrival time (normalized) |
| `arrival_time_unix` | BIGINT | Arrival time (Unix) |
| `arrival_delay_seconds` | INTEGER | Arrival delay in seconds |
| `departure_time_dt` | TIMESTAMP | Departure time (normalized) |
| `departure_time_unix` | BIGINT | Departure time (Unix) |
| `departure_delay_seconds` | INTEGER | Departure delay in seconds |
| `delay_seconds` | INTEGER | Delay (departure or arrival) |
| `ingestion_timestamp` | TIMESTAMP | When record was ingested |

## Integration with ETL Pipeline

### Standalone Loading

After Spark ETL completes:

```bash
# Run Spark ETL
python etl/spark_etl.py

# Load to warehouse
python etl/warehouse_loader.py --warehouse bigquery --feed-type all
```

### In Prefect Flow

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
def load_to_bigquery():
    load_to_warehouse(
        warehouse_type="bigquery",
        feed_type="all",
        schema_name="nyc_transit",
        mode="append"
    )

@flow
def etl_pipeline():
    run_spark_etl()
    load_to_bigquery()
```

## Warehouse-Specific Notes

### Redshift

- Uses SQLAlchemy for connections
- For large datasets, consider uploading Parquet files to S3 first and using `COPY` command
- Current implementation uses pandas insert (suitable for moderate datasets)

### BigQuery

- Automatically detects schema from Parquet files
- Supports partitioning by timestamp columns
- Uses native BigQuery Parquet loading for best performance

### Snowflake

- Uses Snowflake's native Parquet loading via `write_pandas`
- Automatically handles type conversion
- For very large datasets, consider using Snowflake's staging area and `COPY INTO`

## Troubleshooting

### Authentication Errors

**BigQuery**: Ensure `GOOGLE_APPLICATION_CREDENTIALS` points to valid service account key file.

**Redshift**: Verify connection string format: `postgresql://user:password@host:port/database`

**Snowflake**: Check that account format is correct (usually `account-id` or `account-id.region`)

### Schema Mismatch

If you see schema errors, ensure the Parquet files match the expected schema. You can inspect Parquet schema:

```python
import pyarrow.parquet as pq
schema = pq.read_schema("data/staging/vehicle_positions/line=1/part-0.parquet")
print(schema)
```

### Large Dataset Performance

For datasets with millions of rows:
- **Redshift**: Upload to S3 and use COPY command
- **BigQuery**: Already optimized, but consider partitioning
- **Snowflake**: Use staging area and COPY INTO command

## Verification

After loading, verify data in your warehouse:

### BigQuery

```sql
SELECT COUNT(*) FROM `nyc_transit.vehicle_positions`;
SELECT * FROM `nyc_transit.vehicle_positions` LIMIT 10;
```

### Redshift

```sql
SELECT COUNT(*) FROM nyc_transit.vehicle_positions;
SELECT * FROM nyc_transit.vehicle_positions LIMIT 10;
```

### Snowflake

```sql
SELECT COUNT(*) FROM NYC_TRANSIT.vehicle_positions;
SELECT * FROM NYC_TRANSIT.vehicle_positions LIMIT 10;
```

