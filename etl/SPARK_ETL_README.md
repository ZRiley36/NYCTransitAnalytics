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

**⚠️ IMPORTANT: Java is REQUIRED for PySpark to work!**

- **Java 8 or 11** (required for Spark) - See [Java Installation](#java-installation) below
- Python 3.11+
- PySpark

### Java Installation

**You MUST install Java before running Spark ETL!**

#### Windows Installation

1. **Download Java 11 (LTS)** from Adoptium (recommended):
   - Visit: https://adoptium.net/temurin/releases/?version=11
   - Download the **JDK 11** Windows installer (`.msi` file)
   - Choose: **x64 Windows** → **JDK** → **HotSpot** → **Latest Release**

2. **Install Java**:
   - Run the downloaded `.msi` installer
   - Follow the installation wizard
   - **Important**: Make sure "Add to PATH" is checked during installation
   - Make sure "Set JAVA_HOME variable" is checked

3. **Verify Installation**:
   ```powershell
   java -version
   # Should show: openjdk version "11.0.x"
   
   echo $env:JAVA_HOME
   # Should show: C:\Program Files\Eclipse Adoptium\jdk-11.0.x-hotspot
   ```

4. **If JAVA_HOME is not set automatically**:
   - Open **System Properties** → **Environment Variables**
   - Under **System variables**, click **New**
   - Variable name: `JAVA_HOME`
   - Variable value: `C:\Program Files\Eclipse Adoptium\jdk-11.0.x-hotspot` (adjust version number)
   - Click **OK** and restart your terminal

#### Linux Installation

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install openjdk-11-jdk

# Verify
java -version
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
```

#### macOS Installation

```bash
# Using Homebrew
brew install openjdk@11

# Add to PATH (add to ~/.zshrc or ~/.bash_profile)
export JAVA_HOME=$(/usr/libexec/java_home -v 11)
export PATH="$JAVA_HOME/bin:$PATH"
```

### Install Dependencies

```bash
# On Windows, use py -m pip to avoid launcher issues
py -m pip install -r etl/requirements-spark.txt

# On Linux/Mac, you can use:
# python -m pip install -r etl/requirements-spark.txt
```

### Install Windows Requirements (Windows Only)

**Important for Windows users**: Spark requires `winutils.exe` to write files on Windows:

```powershell
# Download winutils.exe automatically
py etl/download_winutils.py
```

This only needs to be done once. The script will download and set up everything automatically.

Or install PySpark separately:

```bash
# Windows
py -m pip install pyspark==3.5.0 pyarrow>=14.0.1

# Linux/Mac
# python -m pip install pyspark==3.5.0 pyarrow>=14.0.1
```

**Note**: 
- If you're using Python 3.13, PyArrow 14.0.1 doesn't have pre-built wheels and requires building from source (needs CMake). The requirements file uses `pyarrow>=14.0.1` to allow newer versions with Python 3.13 support.
- Pandas is included for the Windows workaround (converting Spark DataFrames to Parquet via PyArrow).

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

### Pip Installation Error

If you get an error like `Fatal error in launcher: Unable to create process`, use the Python module launcher instead:

```bash
# Windows - Use py -m pip instead of pip
py -m pip install -r etl/requirements-spark.txt

# Linux/Mac - Use python -m pip instead of pip
python -m pip install -r etl/requirements-spark.txt
```

This bypasses the pip launcher and uses Python's module execution, which is more reliable across platforms.

### HADOOP_HOME / winutils.exe Error (Windows)

**Error**: `HADOOP_HOME and hadoop.home.dir are unset` or `Did not find winutils.exe` or `Could not locate Hadoop executable: winutils.exe`

**Solution**: Spark on Windows requires `winutils.exe` to write files. Download it automatically:

```powershell
# Automatic download (recommended)
py etl/download_winutils.py
```

This will:
- Create `~/.hadoop/bin/` directory
- Download `winutils.exe` to that location
- Set `HADOOP_HOME` environment variable

**Manual Download** (if automatic download fails):
1. Visit: https://github.com/cdarlint/winutils/tree/master/hadoop-3.3.6/bin
2. Download `winutils.exe`
3. Save it to: `C:\Users\<YourUsername>\.hadoop\bin\winutils.exe`
4. Set environment variable: `$env:HADOOP_HOME = "$env:USERPROFILE\.hadoop"`

**Note**: The ETL code will check for `winutils.exe` and provide clear error messages if it's missing.

### Java Not Found / JAVA_GATEWAY_EXITED Error

**Error**: `Java not found and JAVA_HOME environment variable is not set` or `Java gateway process exited before sending its port number`

**Solution**: Install Java 11 and set JAVA_HOME. See [Java Installation](#java-installation) section above.

**Quick Windows Fix**:
1. Download Java 11 from https://adoptium.net/temurin/releases/?version=11
2. Install the `.msi` file (check "Add to PATH" and "Set JAVA_HOME")
3. Restart your terminal/PowerShell
4. Verify: `java -version` should work

**Manual JAVA_HOME Setup (if automatic setup didn't work)**:
```powershell
# Find Java installation path (usually):
# C:\Program Files\Eclipse Adoptium\jdk-11.0.x-hotspot
# or
# C:\Program Files\Java\jdk-11.0.x

# Set JAVA_HOME in PowerShell (current session)
$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-11.0.x-hotspot"
$env:PATH = "$env:JAVA_HOME\bin;$env:PATH"

# Or set permanently via System Properties → Environment Variables
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

## Testing the ETL

### Quick Test

Run the ETL on your data:

```bash
# Process all feed types
python etl/spark_etl.py

# Or process specific feed type
python etl/spark_etl.py --feed-type vehicle_positions
python etl/spark_etl.py --feed-type trip_updates
```

### Verify Output

Check that Parquet files were created:

```bash
# Windows PowerShell
dir data\staging\vehicle_positions
dir data\staging\trip_updates
dir data\staging\vehicle_positions\line=*

# Linux/Mac
ls -la ./data/staging/vehicle_positions/
ls -la ./data/staging/trip_updates/
ls -la ./data/staging/vehicle_positions/line=*/
```

### Test with Example Script

Use the provided example script to process and read back data:

```bash
python etl/example_spark_etl.py
```

This script will:
- Process all feed types
- Read back the Parquet files
- Display sample data
- Show aggregated statistics

### Manual Verification with PySpark

Start a PySpark REPL to inspect the data:

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("Test").getOrCreate()

# Read vehicle positions
vp_df = spark.read.parquet("./data/staging/vehicle_positions")
print(f"Total vehicle positions: {vp_df.count()}")
vp_df.printSchema()
vp_df.show(10)

# Filter by line
vp_df.filter(col("line") == "1").show(10)

# Read trip updates
tu_df = spark.read.parquet("./data/staging/trip_updates")
print(f"Total trip updates: {tu_df.count()}")
tu_df.printSchema()
tu_df.show(10)

# Check for delays
tu_df.filter(col("delay_seconds") > 0).show(10)
```

### Automated Test Script

Run the comprehensive test script:

```bash
python etl/test_spark_etl.py
```

This will verify:
- ✅ Files are read correctly
- ✅ Schema matches expected structure
- ✅ Timestamps are normalized
- ✅ Data is partitioned correctly
- ✅ No null values in key fields (where applicable)
- ✅ Row counts are reasonable

### What to Check

1. **File Count**: Verify output files exist in staging directory
2. **Schema**: Check that all expected columns are present
3. **Data Types**: Verify timestamps are converted correctly
4. **Partitions**: Ensure data is partitioned by `line`
5. **Data Quality**: Check for null values in critical fields
6. **Record Count**: Compare input JSON records with output Parquet records

### Troubleshooting Tests

**No output files?**
- Check that input JSON files exist:
  - Windows: `dir data\gtfs_rt\*.json`
  - Linux/Mac: `ls ./data/gtfs_rt/*.json`
- Verify file naming matches pattern: `vehicle_positions_*.json` or `trip_updates_*.json`

**Schema mismatch?**
- Review the output schema section above
- Check that JSON structure matches expected format

**Memory errors?**
- Reduce Spark memory or process fewer files at once
- Use `--feed-type` to process one feed type at a time

## Checklist

- ✅ PySpark job reads raw feed
- ✅ Transforms into normalized DataFrame
- ✅ Flattens JSON structures
- ✅ Normalizes timestamps
- ✅ Extracts line, delay, train_id
- ✅ Writes Parquet to staging area

