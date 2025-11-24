"""
Test script for warehouse loader

This script tests the warehouse loader functionality with sample data.
"""

import sys
import os
from pathlib import Path
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_staging_data(staging_path: str = "./data/staging") -> bool:
    """Check if staging Parquet files exist"""
    staging = Path(staging_path)
    
    vp_path = staging / "vehicle_positions"
    tu_path = staging / "trip_updates"
    
    vp_exists = vp_path.exists() and any(vp_path.glob("**/*.parquet"))
    tu_exists = tu_path.exists() and any(tu_path.glob("**/*.parquet"))
    
    logger.info("=" * 60)
    logger.info("Checking Staging Data")
    logger.info("=" * 60)
    
    if vp_exists:
        parquet_files = list(vp_path.glob("**/*.parquet"))
        logger.info(f"✓ Found {len(parquet_files)} vehicle_positions Parquet files")
        logger.info(f"  Location: {vp_path}")
    else:
        logger.warning(f"✗ No vehicle_positions Parquet files found in {vp_path}")
    
    if tu_exists:
        parquet_files = list(tu_path.glob("**/*.parquet"))
        logger.info(f"✓ Found {len(parquet_files)} trip_updates Parquet files")
        logger.info(f"  Location: {tu_path}")
    else:
        logger.warning(f"✗ No trip_updates Parquet files found in {tu_path}")
    
    return vp_exists or tu_exists


def check_warehouse_credentials(warehouse_type: str) -> dict:
    """Check if warehouse credentials are configured"""
    logger.info("=" * 60)
    logger.info(f"Checking {warehouse_type.upper()} Configuration")
    logger.info("=" * 60)
    
    missing = []
    configured = {}
    
    if warehouse_type.lower() == "bigquery":
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        if project:
            logger.info(f"✓ GOOGLE_CLOUD_PROJECT: {project}")
            configured["project_id"] = project
        else:
            logger.warning("✗ GOOGLE_CLOUD_PROJECT not set")
            missing.append("GOOGLE_CLOUD_PROJECT")
        
        if creds:
            if Path(creds).exists():
                logger.info(f"✓ GOOGLE_APPLICATION_CREDENTIALS: {creds}")
                configured["credentials_path"] = creds
            else:
                logger.warning(f"✗ Credentials file not found: {creds}")
                missing.append("GOOGLE_APPLICATION_CREDENTIALS")
        else:
            logger.warning("✗ GOOGLE_APPLICATION_CREDENTIALS not set")
            missing.append("GOOGLE_APPLICATION_CREDENTIALS")
        
        dataset = os.getenv("BIGQUERY_DATASET", "nyc_transit")
        logger.info(f"  Dataset: {dataset} (default)")
        configured["dataset_id"] = dataset
    
    elif warehouse_type.lower() == "redshift":
        conn_string = os.getenv("REDSHIFT_CONNECTION_STRING")
        
        if conn_string:
            # Mask password in output
            masked = conn_string.split("@")[0].split(":")[0] + ":***@" + "@".join(conn_string.split("@")[1:])
            logger.info(f"✓ REDSHIFT_CONNECTION_STRING: {masked}")
            configured["connection_string"] = conn_string
        else:
            logger.warning("✗ REDSHIFT_CONNECTION_STRING not set")
            missing.append("REDSHIFT_CONNECTION_STRING")
        
        s3_bucket = os.getenv("REDSHIFT_S3_BUCKET")
        if s3_bucket:
            logger.info(f"  S3 Bucket: {s3_bucket}")
            configured["s3_bucket"] = s3_bucket
    
    elif warehouse_type.lower() == "snowflake":
        account = os.getenv("SNOWFLAKE_ACCOUNT")
        user = os.getenv("SNOWFLAKE_USER")
        password = os.getenv("SNOWFLAKE_PASSWORD")
        
        if account:
            logger.info(f"✓ SNOWFLAKE_ACCOUNT: {account}")
            configured["account"] = account
        else:
            logger.warning("✗ SNOWFLAKE_ACCOUNT not set")
            missing.append("SNOWFLAKE_ACCOUNT")
        
        if user:
            logger.info(f"✓ SNOWFLAKE_USER: {user}")
            configured["user"] = user
        else:
            logger.warning("✗ SNOWFLAKE_USER not set")
            missing.append("SNOWFLAKE_USER")
        
        if password:
            logger.info("✓ SNOWFLAKE_PASSWORD: ***")
            configured["password"] = password
        else:
            logger.warning("✗ SNOWFLAKE_PASSWORD not set")
            missing.append("SNOWFLAKE_PASSWORD")
        
        warehouse = os.getenv("SNOWFLAKE_WAREHOUSE")
        if warehouse:
            logger.info(f"  Warehouse: {warehouse}")
            configured["warehouse"] = warehouse
    
    else:
        logger.error(f"Unknown warehouse type: {warehouse_type}")
        return {"valid": False, "missing": ["unknown_warehouse"], "configured": {}}
    
    valid = len(missing) == 0
    result = {
        "valid": valid,
        "missing": missing,
        "configured": configured
    }
    
    if valid:
        logger.info("✓ All credentials configured!")
    else:
        logger.warning(f"✗ Missing credentials: {', '.join(missing)}")
    
    return result


def check_dependencies(warehouse_type: str) -> bool:
    """Check if required packages are installed"""
    logger.info("=" * 60)
    logger.info(f"Checking Dependencies for {warehouse_type.upper()}")
    logger.info("=" * 60)
    
    packages = {
        "bigquery": ["google.cloud.bigquery", "pandas", "pyarrow"],
        "redshift": ["sqlalchemy", "psycopg2", "boto3", "pandas", "pyarrow"],
        "snowflake": ["snowflake.connector", "pandas", "pyarrow"],
    }
    
    required = packages.get(warehouse_type.lower(), [])
    missing = []
    
    for package in required:
        try:
            if "." in package:
                # Handle module.submodule imports
                parts = package.split(".")
                __import__(parts[0])
            else:
                __import__(package)
            logger.info(f"✓ {package}")
        except ImportError:
            logger.warning(f"✗ {package} not installed")
            missing.append(package)
    
    if missing:
        logger.warning(f"\nInstall missing packages:")
        if warehouse_type.lower() == "bigquery":
            logger.warning("  pip install google-cloud-bigquery[pandas] pandas pyarrow")
        elif warehouse_type.lower() == "redshift":
            logger.warning("  pip install sqlalchemy psycopg2-binary boto3 pandas pyarrow")
        elif warehouse_type.lower() == "snowflake":
            logger.warning("  pip install snowflake-connector-python[pandas] pandas pyarrow")
        return False
    
    logger.info("✓ All dependencies installed!")
    return True


def test_connection(warehouse_type: str) -> bool:
    """Test connection to warehouse"""
    logger.info("=" * 60)
    logger.info(f"Testing Connection to {warehouse_type.upper()}")
    logger.info("=" * 60)
    
    try:
        from etl.warehouse_loader import create_loader
        
        config_check = check_warehouse_credentials(warehouse_type)
        if not config_check["valid"]:
            logger.error("Cannot test connection - credentials not configured")
            return False
        
        loader = create_loader(warehouse_type, **config_check["configured"])
        
        try:
            loader.connect()
            logger.info("✓ Successfully connected!")
            loader.close()
            return True
        except Exception as e:
            logger.error(f"✗ Connection failed: {e}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Error creating loader: {e}")
        return False


def inspect_parquet_schema(staging_path: str = "./data/staging", feed_type: str = "vehicle_positions"):
    """Inspect Parquet file schema"""
    logger.info("=" * 60)
    logger.info(f"Inspecting {feed_type} Parquet Schema")
    logger.info("=" * 60)
    
    try:
        import pyarrow.parquet as pq
        import pandas as pd
        
        feed_path = Path(staging_path) / feed_type
        parquet_files = list(feed_path.glob("**/*.parquet"))
        
        if not parquet_files:
            logger.warning(f"No Parquet files found in {feed_path}")
            return
        
        # Read first file
        sample_file = parquet_files[0]
        logger.info(f"Sample file: {sample_file}")
        
        # Get schema
        schema = pq.read_schema(sample_file)
        logger.info("\nSchema:")
        for field in schema:
            logger.info(f"  {field.name}: {field.type}")
        
        # Read sample data
        df = pd.read_parquet(sample_file)
        logger.info(f"\nRow count: {len(df)}")
        logger.info(f"\nSample data (first 3 rows):")
        logger.info(df.head(3).to_string())
        
    except ImportError:
        logger.error("pyarrow not installed. Install with: pip install pyarrow pandas")
    except Exception as e:
        logger.error(f"Error inspecting schema: {e}")


def main():
    """Run all tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test warehouse loader")
    parser.add_argument(
        "--warehouse",
        choices=["bigquery", "redshift", "snowflake"],
        help="Warehouse type to test"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check configuration, don't test connection"
    )
    parser.add_argument(
        "--inspect",
        choices=["vehicle_positions", "trip_updates"],
        help="Inspect Parquet schema"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Warehouse Loader Test Suite")
    print("=" * 60)
    print()
    
    # Check staging data
    has_data = check_staging_data()
    print()
    
    if args.inspect:
        inspect_parquet_schema(feed_type=args.inspect)
        print()
    
    if not args.warehouse:
        print("Run with --warehouse [bigquery|redshift|snowflake] to test specific warehouse")
        print("\nExample:")
        print("  python etl/test_warehouse_loader.py --warehouse bigquery")
        return
    
    warehouse_type = args.warehouse.lower()
    
    # Check dependencies
    deps_ok = check_dependencies(warehouse_type)
    print()
    
    if not deps_ok:
        print("⚠️  Install missing dependencies before continuing")
        return
    
    # Check credentials
    config_check = check_warehouse_credentials(warehouse_type)
    print()
    
    if not config_check["valid"]:
        print("⚠️  Configure credentials before testing connection")
        print(f"\nSet environment variables: {', '.join(config_check['missing'])}")
        return
    
    if args.check_only:
        print("✓ Configuration check passed!")
        print("\nTo test connection, run without --check-only:")
        print(f"  python etl/test_warehouse_loader.py --warehouse {warehouse_type}")
        return
    
    # Test connection
    if has_data:
        connection_ok = test_connection(warehouse_type)
        print()
        
        if connection_ok:
            print("=" * 60)
            print("✓ All Tests Passed!")
            print("=" * 60)
            print("\nYou can now load data:")
            print(f"  python etl/warehouse_loader.py --warehouse {warehouse_type} --feed-type all")
        else:
            print("=" * 60)
            print("✗ Connection Test Failed")
            print("=" * 60)
            print("\nCheck your credentials and network connection")
    else:
        print("⚠️  No staging data found. Run Spark ETL first:")
        print("  python etl/spark_etl.py")


if __name__ == "__main__":
    main()

