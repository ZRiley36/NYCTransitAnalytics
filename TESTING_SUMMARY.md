# Testing Warehouse Loader - Quick Reference

## Quick Tests (No Warehouse Setup Required)

### 1. Check Staging Data Exists

```bash
# Check if Parquet files are ready for loading
python etl/test_warehouse_loader.py --inspect vehicle_positions
```

This shows:
- ✅ Number of Parquet files found
- ✅ File locations
- ✅ Schema of the data
- ✅ Sample rows

### 2. Inspect Data Schema

```bash
# Inspect vehicle positions schema
python etl/test_warehouse_loader.py --inspect vehicle_positions

# Inspect trip updates schema  
python etl/test_warehouse_loader.py --inspect trip_updates
```

## Full Warehouse Testing

### Step 1: Install Dependencies

```bash
# BigQuery
py -m pip install google-cloud-bigquery[pandas] pandas pyarrow

# Redshift
py -m pip install sqlalchemy psycopg2-binary boto3 pandas pyarrow

# Snowflake
py -m pip install snowflake-connector-python[pandas] pandas pyarrow
```

### Step 2: Set Credentials

**BigQuery:**
```powershell
$env:GOOGLE_CLOUD_PROJECT = "your-project-id"
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\path\to\service-account-key.json"
```

**Redshift:**
```powershell
$env:REDSHIFT_CONNECTION_STRING = "postgresql://user:password@host:5439/database"
```

**Snowflake:**
```powershell
$env:SNOWFLAKE_ACCOUNT = "your-account"
$env:SNOWFLAKE_USER = "your-user"
$env:SNOWFLAKE_PASSWORD = "your-password"
```

### Step 3: Run Tests

```bash
# Test BigQuery configuration and connection
python etl/test_warehouse_loader.py --warehouse bigquery

# Test Redshift
python etl/test_warehouse_loader.py --warehouse redshift

# Test Snowflake
python etl/test_warehouse_loader.py --warehouse snowflake

# Configuration check only (no connection test)
python etl/test_warehouse_loader.py --warehouse bigquery --check-only
```

## Load Test Data

### Small Test Load

```bash
# Load just one feed type
python etl/warehouse_loader.py \
    --warehouse bigquery \
    --feed-type vehicle_positions \
    --mode append

# Or load all feeds
python etl/warehouse_loader.py \
    --warehouse bigquery \
    --feed-type all \
    --mode append
```

### Verify Data Loaded

After loading, query your warehouse:

**BigQuery:**
```sql
SELECT COUNT(*) FROM `nyc_transit.vehicle_positions`;
SELECT * FROM `nyc_transit.vehicle_positions` LIMIT 10;
```

**Redshift/Snowflake:**
```sql
SELECT COUNT(*) FROM nyc_transit.vehicle_positions;
SELECT * FROM nyc_transit.vehicle_positions LIMIT 10;
```

## Complete Test Workflow

```bash
# 1. Check staging data (no warehouse needed)
python etl/test_warehouse_loader.py --inspect vehicle_positions

# 2. Test warehouse setup
python etl/test_warehouse_loader.py --warehouse bigquery

# 3. Load data (if tests pass)
python etl/warehouse_loader.py --warehouse bigquery --feed-type all

# 4. Verify in warehouse (query directly)
# SELECT COUNT(*) FROM `nyc_transit.vehicle_positions`;
```

## What Each Test Checks

The test script verifies:

1. **Staging Data**: ✅ Parquet files exist
2. **Dependencies**: ✅ Required packages installed
3. **Credentials**: ✅ Environment variables set
4. **Connection**: ✅ Can connect to warehouse
5. **Schema**: ✅ Parquet schema inspection

## Troubleshooting

See `docs/TESTING_WAREHOUSE_LOADER.md` for detailed troubleshooting guide.

## Acceptance Criteria

✅ **Data is queryable in warehouse**: After successful load, you can run SQL queries directly in your warehouse.

Test this by:
```sql
SELECT COUNT(*) FROM nyc_transit.vehicle_positions;
SELECT line, COUNT(*) as count 
FROM nyc_transit.vehicle_positions 
GROUP BY line;
```

