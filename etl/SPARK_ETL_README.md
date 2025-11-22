# Spark ETL Job

This module processes raw GTFS-RT JSON feeds and transforms them into normalized Parquet files for analytics.

## Features

✅ **Reads raw feed** - Processes JSON files from GTFS-RT ingestion  
✅ **Flattens JSON** - Explodes nested arrays and structures  
✅ **Normalizes timestamps** - Converts Unix timestamps to datetime  
✅ **Extracts key fields** - line (route_id), delay, train_id  
✅ **Writes Parquet** - Outputs to staging area partitioned by line  

## Installation

### Prerequisites

- Java 8 or 11 (required for Spark)
- Python 3.11+
- PySpark

### Install Dependencies

```bash
pip install -r etl/requirements-spark.txt
```

Or install PySpark separately:

```bash
pip install pyspark==3.5.0 pyarrow==14.0.1
```

## Usage

### Basic Usage

Process all feed types:

```bash
python etl/spark_etl.py
```

### Process Specific Feed Type

```bash
# Vehicle positions only
python etl/spark_etl.py --feed-type vehicle_positions

# Trip updates only
python etl/spark_etl.py --feed-type trip_updates
```

### Custom Paths

```bash
python etl/spark_etl.py \
    --raw-path ./data/gtfs_rt \
    --staging-path ./data/staging
```

### Environment Variables

```bash
export GTFS_RAW_PATH=./data/gtfs_rt
export GTFS_STAGING_PATH=./data/staging
export SPARK_MASTER=local[*]

python etl/spark_etl.py
```

## Output Schema

### Vehicle Positions

| Column | Type | Description |
|--------|------|-------------|
| `feed_timestamp_dt` | Timestamp | Feed timestamp (normalized) |
| `feed_timestamp_unix` | Long | Feed timestamp (Unix) |
| `gtfs_version` | String | GTFS-RT version |
| `entity_id` | String | Entity ID |
| `vehicle_id` | String | Vehicle ID |
| `train_id` | String | Trip ID (train identifier) |
| `line` | String | Route ID (subway line) |
| `latitude` | Double | Vehicle latitude |
| `longitude` | Double | Vehicle longitude |
| `bearing` | Double | Vehicle bearing |
| `speed` | Double | Vehicle speed |
| `vehicle_timestamp_dt` | Timestamp | Vehicle timestamp (normalized) |
| `vehicle_timestamp_unix` | Long | Vehicle timestamp (Unix) |
| `stop_sequence` | Integer | Current stop sequence |
| `stop_id` | String | Current stop ID |
| `ingestion_timestamp` | Timestamp | When record was ingested |

### Trip Updates

| Column | Type | Description |
|--------|------|-------------|
| `feed_timestamp_dt` | Timestamp | Feed timestamp (normalized) |
| `feed_timestamp_unix` | Long | Feed timestamp (Unix) |
| `gtfs_version` | String | GTFS-RT version |
| `entity_id` | String | Entity ID |
| `train_id` | String | Trip ID (train identifier) |
| `line` | String | Route ID (subway line) |
| `trip_timestamp_dt` | Timestamp | Trip timestamp (normalized) |
| `trip_timestamp_unix` | Long | Trip timestamp (Unix) |
| `stop_sequence` | Integer | Stop sequence |
| `stop_id` | String | Stop ID |
| `arrival_time_dt` | Timestamp | Arrival time (normalized) |
| `arrival_time_unix` | Long | Arrival time (Unix) |
| `arrival_delay_seconds` | Integer | Arrival delay in seconds |
| `departure_time_dt` | Timestamp | Departure time (normalized) |
| `departure_time_unix` | Long | Departure time (Unix) |
| `departure_delay_seconds` | Integer | Departure delay in seconds |
| `delay_seconds` | Integer | Delay (departure or arrival) |
| `ingestion_timestamp` | Timestamp | When record was ingested |

## Output Structure

Parquet files are written to the staging area, partitioned by `line` (route_id):

```
data/staging/
├── vehicle_positions/
│   ├── line=1/
│   │   └── part-*.parquet
│   ├── line=2/
│   │   └── part-*.parquet
│   └── ...
└── trip_updates/
    ├── line=1/
    │   └── part-*.parquet
    ├── line=2/
    │   └── part-*.parquet
    └── ...
```

## Reading Parquet Files

### Using PySpark

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("ReadStaging").getOrCreate()

# Read vehicle positions
df = spark.read.parquet("./data/staging/vehicle_positions")

# Filter by line
df.filter(col("line") == "1").show()

# Query with SQL
df.createOrReplaceTempView("vehicle_positions")
spark.sql("SELECT * FROM vehicle_positions WHERE line = '1'").show()
```

### Using Pandas

```python
import pandas as pd
import pyarrow.parquet as pq

# Read all partitions
df = pd.read_parquet("./data/staging/vehicle_positions")

# Read specific partition
df = pd.read_parquet("./data/staging/vehicle_positions/line=1")
```

## Integration with Prefect

You can integrate the Spark ETL job into your Prefect flows:

```python
from prefect import task, flow
from etl.spark_etl import GTFSRTETL

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

@flow
def etl_pipeline():
    run_spark_etl()
```

## Performance Tips

1. **Partitioning**: Data is partitioned by `line` for efficient filtering
2. **Adaptive Query Execution**: Enabled by default for better performance
3. **Memory**: Adjust Spark memory if processing large datasets:
   ```bash
   export SPARK_DRIVER_MEMORY=4g
   export SPARK_EXECUTOR_MEMORY=4g
   ```

## Troubleshooting

### Java Not Found

Install Java 8 or 11:
```bash
# Ubuntu/Debian
sudo apt install openjdk-11-jdk

# macOS
brew install openjdk@11
```

### Out of Memory

Increase Spark memory:
```bash
export SPARK_DRIVER_MEMORY=8g
export SPARK_EXECUTOR_MEMORY=8g
```

### No Files Found

Check that raw JSON files exist:
```bash
ls -la ./data/gtfs_rt/*.json
```

## Checklist

- ✅ PySpark job reads raw feed
- ✅ Transforms into normalized DataFrame
- ✅ Flattens JSON structures
- ✅ Normalizes timestamps
- ✅ Extracts line, delay, train_id
- ✅ Writes Parquet to staging area

