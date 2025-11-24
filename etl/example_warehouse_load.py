"""
Example: Loading ETL data to warehouse

This script demonstrates how to load Parquet files from Spark ETL
into various data warehouses.
"""

import os
from pathlib import Path
from etl.warehouse_loader import load_to_warehouse, create_loader

def example_load_to_bigquery():
    """Example: Load to BigQuery"""
    print("Loading data to BigQuery...")
    
    load_to_warehouse(
        warehouse_type="bigquery",
        feed_type="vehicle_positions",
        schema_name="nyc_transit",
        staging_path="./data/staging",
        mode="append"
    )


def example_load_to_redshift():
    """Example: Load to Redshift"""
    print("Loading data to Redshift...")
    
    load_to_warehouse(
        warehouse_type="redshift",
        feed_type="vehicle_positions",
        schema_name="nyc_transit",
        staging_path="./data/staging",
        mode="append"
    )


def example_load_to_snowflake():
    """Example: Load to Snowflake"""
    print("Loading data to Snowflake...")
    
    load_to_warehouse(
        warehouse_type="snowflake",
        feed_type="vehicle_positions",
        schema_name="NYC_TRANSIT",
        staging_path="./data/staging",
        mode="append"
    )


def example_advanced_usage():
    """Example: Advanced usage with custom configuration"""
    from etl.warehouse_loader import BigQueryLoader, VEHICLE_POSITIONS_SCHEMA
    
    loader = BigQueryLoader(
        staging_path="./data/staging",
        project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
        dataset_id="nyc_transit",
        location="US"  # BigQuery location
    )
    
    with loader:
        # Create schema
        loader.create_schema("nyc_transit")
        
        # Create table
        loader.create_table(
            "nyc_transit",
            "vehicle_positions",
            VEHICLE_POSITIONS_SCHEMA,
            partition_column="ingestion_timestamp"  # Partition by ingestion time
        )
        
        # Load data
        source_path = Path("./data/staging/vehicle_positions")
        loader.load_data(
            "nyc_transit",
            "vehicle_positions",
            source_path,
            mode="append"
        )


def example_load_all_feeds():
    """Example: Load all feed types to warehouse"""
    warehouse_type = os.getenv("WAREHOUSE_TYPE", "bigquery")
    
    for feed_type in ["vehicle_positions", "trip_updates"]:
        print(f"Loading {feed_type} to {warehouse_type}...")
        load_to_warehouse(
            warehouse_type=warehouse_type,
            feed_type=feed_type,
            schema_name="nyc_transit",
            mode="append"
        )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        warehouse = sys.argv[1].lower()
        
        if warehouse == "bigquery":
            example_load_to_bigquery()
        elif warehouse == "redshift":
            example_load_to_redshift()
        elif warehouse == "snowflake":
            example_load_to_snowflake()
        elif warehouse == "all":
            example_load_all_feeds()
        elif warehouse == "advanced":
            example_advanced_usage()
        else:
            print(f"Unknown warehouse: {warehouse}")
            print("Usage: python example_warehouse_load.py [bigquery|redshift|snowflake|all|advanced]")
    else:
        print("Usage: python example_warehouse_load.py [bigquery|redshift|snowflake|all|advanced]")
        print("\nOr set WAREHOUSE_TYPE environment variable and run:")
        print("  python example_warehouse_load.py all")

