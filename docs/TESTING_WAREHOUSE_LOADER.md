# Testing Warehouse Loader

This guide shows you how to test the warehouse loader step-by-step.

## Quick Test (No Warehouse Required)

### 1. Check Staging Data

First, verify you have Parquet files from the Spark ETL:

```bash
# Check if staging data exists
python etl/test_warehouse_loader.py --inspect vehicle_positions

# This will show:
# - Parquet file locations
# - Schema of the data
# - Sample rows
```

Expected output:
```
✓ Found X vehicle_positions Parquet files
  Location: ./data/staging/vehicle_positions

Schema:
  feed_timestamp_dt: timestamp[us]
  vehicle_id: string
  line: string
  ...
```

### 2. Inspect Parquet Files

View the schema and sample data:

```bash
# Inspect vehicle positions
python etl/test_warehouse_loader.py --inspect vehicle_positions

# Inspect trip updates
python etl/test_warehouse_loader.py --inspect trip_updates
```

## Testing with Warehouse

### Step 1: Install Dependencies

```bash
# For BigQuery
py -m pip install google-cloud-bigquery[pandas] pandas pyarrow

# For Redshift  
py -m pip install sqlalchemy psycopg2-binary boto3 pandas pyarrow

# For Snowflake
py -m pip install snowflake-connector-python[pandas] pandas pyarrow
```

### Step 2: Configure Credentials

Set environment variables for your warehouse:

#### BigQuery
```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

#### Redshift
```bash
export REDSHIFT_CONNECTION_STRING="postgresql://user:password@host:5439/database"
```

#### Snowflake
```bash
export SNOWFLAKE_ACCOUNT="your-account"
export SNOWFLAKE_USER="your-user"
export SNOWFLAKE_PASSWORD="your-password"
```

### Step 3: Run Tests

```bash
# Test BigQuery configuration and connection
python etl/test_warehouse_loader.py --warehouse bigquery

# Test Redshift
python etl/test_warehouse_loader.py --warehouse redshift

# Test Snowflake
python etl/test_warehouse_loader.py --warehouse snowflake
```

The test will check:
- ✅ Staging Parquet files exist
- ✅ Dependencies are installed
- ✅ Credentials are configured
- ✅ Connection to warehouse works

### Step 4: Load Test Data (Small Sample)

Before loading all data, test with a small subset:

```python
# Create a test script: test_load.py
from etl.warehouse_loader import create_loader, VEHICLE_POSITIONS_SCHEMA
from pathlib import Path
import os

# Use BigQuery as example
loader = create_loader(
    "bigquery",
    staging_path="./data/staging"
)

with loader:
    # Create test schema
    loader.create_schema("nyc_transit_test")
    
    # Create table
    loader.create_table(
        "nyc_transit_test",
        "vehicle_positions_test",
        VEHICLE_POSITIONS_SCHEMA
    )
    
    # Load just one partition (smaller dataset)
    test_path = Path("./data/staging/vehicle_positions/line=1")
    if test_path.exists():
        loader.load_data(
            "nyc_transit_test",
            "vehicle_positions_test",
            test_path,
            mode="append"
        )
        print("✓ Test load successful!")
    else:
        print("No test data found in line=1 partition")
```

Run the test:
```bash
python test_load.py
```

### Step 5: Verify Data in Warehouse

After loading, query your warehouse to verify:

#### BigQuery
```bash
bq query --use_legacy_sql=false \
  "SELECT COUNT(*) as row_count FROM \`nyc_transit_test.vehicle_positions_test\`"
```

Or in Python:
```python
from google.cloud import bigquery

client = bigquery.Client()
query = "SELECT COUNT(*) as row_count FROM `nyc_transit_test.vehicle_positions_test`"
results = client.query(query)
for row in results:
    print(f"Rows: {row.row_count}")
```

#### Redshift
```sql
SELECT COUNT(*) FROM nyc_transit_test.vehicle_positions_test;
SELECT * FROM nyc_transit_test.vehicle_positions_test LIMIT 5;
```

#### Snowflake
```sql
SELECT COUNT(*) FROM NYC_TRANSIT_TEST.VEHICLE_POSITIONS_TEST;
SELECT * FROM NYC_TRANSIT_TEST.VEHICLE_POSITIONS_TEST LIMIT 5;
```

## Full Test Workflow

```bash
# 1. Ensure Spark ETL has run
python etl/spark_etl.py

# 2. Check staging data
python etl/test_warehouse_loader.py --inspect vehicle_positions

# 3. Test warehouse configuration
python etl/test_warehouse_loader.py --warehouse bigquery

# 4. Load test data (small sample)
python test_load.py  # Or use the example script above

# 5. Verify in warehouse
# (Query warehouse directly)

# 6. Load full dataset
python etl/warehouse_loader.py --warehouse bigquery --feed-type all --mode append
```

## Troubleshooting Tests

### "No staging data found"

Run Spark ETL first:
```bash
python etl/spark_etl.py
```

### "Dependencies not installed"

Install missing packages:
```bash
# Check which packages are missing from test output
pip install <missing-package>
```

### "Credentials not configured"

Set environment variables. On Windows PowerShell:
```powershell
$env:GOOGLE_CLOUD_PROJECT = "your-project-id"
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\path\to\key.json"
```

On Linux/Mac:
```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
```

### "Connection failed"

- **BigQuery**: Verify service account key file path and permissions
- **Redshift**: Check connection string format and network access
- **Snowflake**: Verify account format (may need `.region` suffix)

### "Schema mismatch"

Inspect Parquet schema to see what's actually in the files:
```bash
python etl/test_warehouse_loader.py --inspect vehicle_positions
```

Compare with expected schema in `warehouse_loader.py` (VEHICLE_POSITIONS_SCHEMA).

## Acceptance Testing

To verify the warehouse loader works end-to-end:

1. ✅ **Staging data exists**: Check passes
2. ✅ **Credentials configured**: Check passes  
3. ✅ **Connection successful**: Connection test passes
4. ✅ **Data loads successfully**: Load completes without errors
5. ✅ **Data is queryable**: Can run SELECT queries in warehouse

```bash
# Run full test suite
python etl/test_warehouse_loader.py --warehouse bigquery

# If all checks pass, load data
python etl/warehouse_loader.py --warehouse bigquery --feed-type vehicle_positions

# Verify data is queryable
# (Query warehouse directly with SQL)
```

## Next Steps

After testing successfully:
- Set up scheduled loading (via Prefect or cron)
- Create views for common queries
- Set up monitoring and alerting
- Optimize for your data volume

