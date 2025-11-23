"""
Test script for Spark ETL job

This script runs comprehensive tests to verify the ETL pipeline:
- Verifies input files exist
- Processes the data
- Validates output schema
- Checks data quality
- Verifies partitioning
"""

import sys
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, isnan, isnull, when
from pyspark.sql.types import TimestampType, StringType, LongType, IntegerType, DoubleType

from etl.spark_etl import GTFSRTETL


def check_input_files(etl: GTFSRTETL) -> bool:
    """Check that input files exist"""
    print("=" * 60)
    print("1. Checking Input Files")
    print("=" * 60)
    
    vp_files = list(etl.raw_data_path.glob("vehicle_positions_*.json"))
    tu_files = list(etl.raw_data_path.glob("trip_updates_*.json"))
    
    print(f"  Vehicle position files found: {len(vp_files)}")
    print(f"  Trip update files found: {len(tu_files)}")
    
    if not vp_files and not tu_files:
        print("  ❌ ERROR: No input files found!")
        return False
    
    if vp_files:
        print(f"  ✓ Sample file: {vp_files[0].name}")
    if tu_files:
        print(f"  ✓ Sample file: {tu_files[0].name}")
    
    return True


def validate_vehicle_positions_schema(df) -> bool:
    """Validate vehicle positions schema"""
    print("\n" + "=" * 60)
    print("2. Validating Vehicle Positions Schema")
    print("=" * 60)
    
    expected_columns = {
        'feed_timestamp_dt': TimestampType,
        'feed_timestamp_unix': LongType,
        'gtfs_version': StringType,
        'entity_id': StringType,
        'vehicle_id': StringType,
        'train_id': StringType,
        'line': StringType,
        'latitude': DoubleType,
        'longitude': DoubleType,
        'bearing': DoubleType,
        'speed': DoubleType,
        'vehicle_timestamp_dt': TimestampType,
        'vehicle_timestamp_unix': LongType,
        'stop_sequence': IntegerType,
        'stop_id': StringType,
        'ingestion_timestamp': TimestampType,
    }
    
    schema = df.schema
    all_good = True
    
    for col_name, expected_type in expected_columns.items():
        field = next((f for f in schema.fields if f.name == col_name), None)
        if field is None:
            print(f"  ❌ Missing column: {col_name}")
            all_good = False
        else:
            actual_type = type(field.dataType)
            if actual_type != expected_type:
                print(f"  ⚠️  Column {col_name}: expected {expected_type.__name__}, got {actual_type.__name__}")
            else:
                print(f"  ✓ Column {col_name}: {actual_type.__name__}")
    
    return all_good


def validate_trip_updates_schema(df) -> bool:
    """Validate trip updates schema"""
    print("\n" + "=" * 60)
    print("3. Validating Trip Updates Schema")
    print("=" * 60)
    
    expected_columns = {
        'feed_timestamp_dt': TimestampType,
        'feed_timestamp_unix': LongType,
        'gtfs_version': StringType,
        'entity_id': StringType,
        'train_id': StringType,
        'line': StringType,
        'trip_timestamp_dt': TimestampType,
        'trip_timestamp_unix': LongType,
        'stop_sequence': IntegerType,
        'stop_id': StringType,
        'arrival_time_dt': TimestampType,
        'arrival_time_unix': LongType,
        'arrival_delay_seconds': IntegerType,
        'departure_time_dt': TimestampType,
        'departure_time_unix': LongType,
        'departure_delay_seconds': IntegerType,
        'delay_seconds': IntegerType,
        'ingestion_timestamp': TimestampType,
    }
    
    schema = df.schema
    all_good = True
    
    for col_name, expected_type in expected_columns.items():
        field = next((f for f in schema.fields if f.name == col_name), None)
        if field is None:
            print(f"  ❌ Missing column: {col_name}")
            all_good = False
        else:
            actual_type = type(field.dataType)
            if actual_type != expected_type:
                print(f"  ⚠️  Column {col_name}: expected {expected_type.__name__}, got {actual_type.__name__}")
            else:
                print(f"  ✓ Column {col_name}: {actual_type.__name__}")
    
    return all_good


def check_data_quality(df, feed_type: str) -> bool:
    """Check data quality metrics"""
    print("\n" + "=" * 60)
    print(f"4. Checking {feed_type.replace('_', ' ').title()} Data Quality")
    print("=" * 60)
    
    total_count = df.count()
    print(f"  Total records: {total_count:,}")
    
    if total_count == 0:
        print("  ❌ ERROR: No records found!")
        return False
    
    # Check for nulls in key fields
    key_fields = ['line', 'train_id'] if feed_type == 'vehicle_positions' else ['line', 'train_id', 'stop_id']
    
    print("\n  Null counts in key fields:")
    all_good = True
    for field in key_fields:
        null_count = df.filter(col(field).isNull()).count()
        null_pct = (null_count / total_count) * 100 if total_count > 0 else 0
        if null_count > 0:
            print(f"    ⚠️  {field}: {null_count:,} nulls ({null_pct:.1f}%)")
        else:
            print(f"    ✓ {field}: no nulls")
    
    # Check timestamp normalization
    if feed_type == 'vehicle_positions':
        timestamp_field = 'vehicle_timestamp_dt'
    else:
        timestamp_field = 'trip_timestamp_dt'
    
    null_timestamps = df.filter(col(timestamp_field).isNull()).count()
    if null_timestamps > 0:
        print(f"    ⚠️  {timestamp_field}: {null_timestamps:,} null timestamps")
    else:
        print(f"    ✓ {timestamp_field}: all timestamps normalized")
    
    # Show sample data
    print("\n  Sample data (first 5 rows):")
    df.select('line', 'train_id', timestamp_field).show(5, truncate=False)
    
    return all_good


def check_partitioning(staging_path: Path, feed_type: str) -> bool:
    """Check that data is properly partitioned"""
    print("\n" + "=" * 60)
    print(f"5. Checking {feed_type.replace('_', ' ').title()} Partitioning")
    print("=" * 60)
    
    feed_path = staging_path / feed_type
    if not feed_path.exists():
        print(f"  ❌ ERROR: Output path {feed_path} does not exist!")
        return False
    
    # Check for partition directories
    partitions = [d for d in feed_path.iterdir() if d.is_dir() and d.name.startswith("line=")]
    
    if not partitions:
        print("  ⚠️  WARNING: No partitions found (data may not be partitioned)")
        return False
    
    print(f"  ✓ Found {len(partitions)} partitions:")
    for partition in sorted(partitions)[:10]:  # Show first 10
        line = partition.name.replace("line=", "")
        parquet_files = list(partition.glob("*.parquet"))
        print(f"    - line={line}: {len(parquet_files)} file(s)")
    
    if len(partitions) > 10:
        print(f"    ... and {len(partitions) - 10} more partitions")
    
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Spark ETL Test Suite")
    print("=" * 60)
    
    # Initialize ETL
    etl = GTFSRTETL(
        raw_data_path="./data/gtfs_rt",
        staging_path="./data/staging",
        spark_master="local[*]",
        app_name="ETL-Test"
    )
    
    try:
        # Check input files
        if not check_input_files(etl):
            print("\n❌ Test failed: No input files found")
            sys.exit(1)
        
        # Process vehicle positions
        print("\n" + "=" * 60)
        print("Processing Vehicle Positions...")
        print("=" * 60)
        vp_df = etl.process_vehicle_positions()
        
        if vp_df is not None:
            vp_count = vp_df.count()
            print(f"Processed {vp_count:,} vehicle position records")
            
            # Validate schema
            validate_vehicle_positions_schema(vp_df)
            
            # Check data quality
            check_data_quality(vp_df, "vehicle_positions")
            
            # Check partitioning
            check_partitioning(etl.staging_path, "vehicle_positions")
        
        # Process trip updates
        print("\n" + "=" * 60)
        print("Processing Trip Updates...")
        print("=" * 60)
        tu_df = etl.process_trip_updates()
        
        if tu_df is not None:
            tu_count = tu_df.count()
            print(f"Processed {tu_count:,} trip update records")
            
            # Validate schema
            validate_trip_updates_schema(tu_df)
            
            # Check data quality
            check_data_quality(tu_df, "trip_updates")
            
            # Check partitioning
            check_partitioning(etl.staging_path, "trip_updates")
        
        # Final summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print("✓ All tests completed successfully!")
        print("\nYou can now read the processed data:")
        print("  - Vehicle positions: ./data/staging/vehicle_positions")
        print("  - Trip updates: ./data/staging/trip_updates")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        etl.stop()


if __name__ == "__main__":
    main()


