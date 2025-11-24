"""
Warehouse Loading Module

Loads Parquet files from Spark ETL staging area into data warehouses:
- Amazon Redshift
- Google BigQuery
- Snowflake

Supports both incremental and full loads.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WarehouseType(Enum):
    """Supported warehouse types"""
    REDSHIFT = "redshift"
    BIGQUERY = "bigquery"
    SNOWFLAKE = "snowflake"


class WarehouseLoader:
    """Base class for warehouse loaders"""
    
    def __init__(
        self,
        warehouse_type: WarehouseType,
        staging_path: str = "./data/staging",
        **config
    ):
        """
        Initialize warehouse loader
        
        Args:
            warehouse_type: Type of warehouse (REDSHIFT, BIGQUERY, SNOWFLAKE)
            staging_path: Path to staging Parquet files
            **config: Warehouse-specific configuration
        """
        self.warehouse_type = warehouse_type
        self.staging_path = Path(staging_path)
        self.config = config
        self._connection = None
    
    def connect(self):
        """Establish connection to warehouse"""
        raise NotImplementedError
    
    def create_schema(self, schema_name: str):
        """Create schema/database if it doesn't exist"""
        raise NotImplementedError
    
    def create_table(
        self,
        schema_name: str,
        table_name: str,
        schema: Dict[str, str],
        partition_column: Optional[str] = None
    ):
        """Create table with given schema"""
        raise NotImplementedError
    
    def load_data(
        self,
        schema_name: str,
        table_name: str,
        source_path: Path,
        mode: str = "append"
    ):
        """
        Load data from Parquet files into warehouse table
        
        Args:
            schema_name: Schema/database name
            table_name: Table name
            source_path: Path to Parquet files (can be directory or single file)
            mode: Load mode - "append", "overwrite", or "upsert"
        """
        raise NotImplementedError
    
    def close(self):
        """Close connection"""
        if self._connection:
            try:
                self._connection.close()
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class RedshiftLoader(WarehouseLoader):
    """Amazon Redshift loader"""
    
    def __init__(self, staging_path: str = "./data/staging", **config):
        super().__init__(WarehouseType.REDSHIFT, staging_path, **config)
        try:
            import boto3
            from sqlalchemy import create_engine
            self.boto3 = boto3
            self.create_engine = create_engine
        except ImportError:
            raise ImportError(
                "Redshift loader requires: pip install sqlalchemy psycopg2-binary boto3"
            )
        
        self.connection_string = config.get(
            "connection_string",
            os.getenv("REDSHIFT_CONNECTION_STRING")
        )
        
        if not self.connection_string:
            raise ValueError(
                "Redshift connection string required. "
                "Set REDSHIFT_CONNECTION_STRING environment variable or pass connection_string in config"
            )
        
        self.s3_bucket = config.get("s3_bucket", os.getenv("REDSHIFT_S3_BUCKET"))
        self.s3_prefix = config.get("s3_prefix", os.getenv("REDSHIFT_S3_PREFIX", "staging/"))
        self.iam_role = config.get("iam_role", os.getenv("REDSHIFT_IAM_ROLE"))
    
    def connect(self):
        """Connect to Redshift"""
        from sqlalchemy import create_engine
        self.engine = create_engine(self.connection_string)
        self._connection = self.engine.connect()
        logger.info("Connected to Redshift")
    
    def create_schema(self, schema_name: str):
        """Create schema if it doesn't exist"""
        with self.engine.begin() as conn:
            conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
        logger.info(f"Created schema: {schema_name}")
    
    def create_table(self, schema_name: str, table_name: str, schema: Dict[str, str], partition_column: Optional[str] = None):
        """Create table with given schema"""
        columns = ", ".join([f"{col} {dtype}" for col, dtype in schema.items()])
        full_table_name = f"{schema_name}.{table_name}"
        
        with self.engine.begin() as conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {full_table_name} (
                    {columns}
                )
            """)
        logger.info(f"Created table: {full_table_name}")
    
    def load_data(self, schema_name: str, table_name: str, source_path: Path, mode: str = "append"):
        """
        Load data from Parquet files to Redshift via S3
        
        Requires data to be uploaded to S3 first, then uses COPY command
        """
        import pandas as pd
        import pyarrow.parquet as pq
        
        # Read Parquet files
        parquet_files = list(source_path.glob("**/*.parquet"))
        if not parquet_files:
            logger.warning(f"No Parquet files found in {source_path}")
            return
        
        logger.info(f"Loading {len(parquet_files)} Parquet files to Redshift...")
        
        # For now, use pandas + SQL insert (for small datasets)
        # For production, should upload to S3 and use COPY command
        full_table_name = f"{schema_name}.{table_name}"
        
        # Read all Parquet files
        dfs = []
        for parquet_file in parquet_files:
            df = pd.read_parquet(parquet_file)
            dfs.append(df)
        
        combined_df = pd.concat(dfs, ignore_index=True)
        
        if mode == "overwrite":
            with self.engine.begin() as conn:
                conn.execute(f"TRUNCATE TABLE {full_table_name}")
        
        # Insert data
        combined_df.to_sql(
            table_name,
            self.engine,
            schema=schema_name,
            if_exists="append" if mode == "append" else "replace",
            index=False,
            method="multi",
            chunksize=10000
        )
        
        logger.info(f"Loaded {len(combined_df)} rows into {full_table_name}")


class BigQueryLoader(WarehouseLoader):
    """Google BigQuery loader"""
    
    def __init__(self, staging_path: str = "./data/staging", **config):
        super().__init__(WarehouseType.BIGQUERY, staging_path, **config)
        try:
            from google.cloud import bigquery
            self.bigquery = bigquery
        except ImportError:
            raise ImportError(
                "BigQuery loader requires: pip install google-cloud-bigquery[pandas] pyarrow"
            )
        
        self.project_id = config.get("project_id", os.getenv("GOOGLE_CLOUD_PROJECT"))
        self.dataset_id = config.get("dataset_id", os.getenv("BIGQUERY_DATASET", "nyc_transit"))
        
        if not self.project_id:
            raise ValueError(
                "BigQuery project ID required. "
                "Set GOOGLE_CLOUD_PROJECT environment variable or pass project_id in config"
            )
        
        credentials_path = config.get("credentials_path", os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    
    def connect(self):
        """Connect to BigQuery"""
        self.client = self.bigquery.Client(project=self.project_id)
        self._connection = self.client
        logger.info(f"Connected to BigQuery project: {self.project_id}")
    
    def create_schema(self, schema_name: str):
        """Create dataset if it doesn't exist"""
        dataset_ref = self.bigquery.Dataset(f"{self.project_id}.{schema_name}")
        dataset = self.bigquery.Dataset(dataset_ref)
        dataset.location = self.config.get("location", "US")
        
        try:
            self.client.create_dataset(dataset, exists_ok=True)
            logger.info(f"Created dataset: {schema_name}")
        except Exception as e:
            logger.info(f"Dataset {schema_name} already exists or error: {e}")
    
    def create_table(self, schema_name: str, table_name: str, schema: Dict[str, str], partition_column: Optional[str] = None):
        """Create table with given schema"""
        from google.cloud.bigquery import SchemaField
        
        table_id = f"{self.project_id}.{schema_name}.{table_name}"
        
        # Convert schema to BigQuery schema fields
        bq_schema = []
        for col_name, col_type in schema.items():
            bq_type = self._convert_type_to_bigquery(col_type)
            bq_schema.append(SchemaField(col_name, bq_type))
        
        table = self.bigquery.Table(table_id, schema=bq_schema)
        
        # Add partitioning if specified
        if partition_column:
            table.time_partitioning = self.bigquery.TimePartitioning(
                field=partition_column,
                type_=self.bigquery.TimePartitioningType.DAY
            )
        
        table = self.client.create_table(table, exists_ok=True)
        logger.info(f"Created table: {table_id}")
    
    def _convert_type_to_bigquery(self, dtype: str) -> str:
        """Convert Python/SQL type to BigQuery type"""
        type_mapping = {
            "string": "STRING",
            "int": "INTEGER",
            "integer": "INTEGER",
            "bigint": "INTEGER",
            "long": "INTEGER",
            "double": "FLOAT",
            "float": "FLOAT",
            "boolean": "BOOLEAN",
            "date": "DATE",
            "timestamp": "TIMESTAMP",
            "datetime": "TIMESTAMP",
        }
        dtype_lower = dtype.lower()
        return type_mapping.get(dtype_lower, "STRING")
    
    def load_data(self, schema_name: str, table_name: str, source_path: Path, mode: str = "append"):
        """Load data from Parquet files to BigQuery"""
        import pandas as pd
        
        table_id = f"{self.project_id}.{schema_name}.{table_name}"
        
        # Read all Parquet files
        parquet_files = list(source_path.glob("**/*.parquet"))
        if not parquet_files:
            logger.warning(f"No Parquet files found in {source_path}")
            return
        
        logger.info(f"Loading {len(parquet_files)} Parquet files to BigQuery...")
        
        job_config = self.bigquery.LoadJobConfig(
            source_format=self.bigquery.SourceFormat.PARQUET,
            write_disposition="WRITE_APPEND" if mode == "append" else "WRITE_TRUNCATE",
        )
        
        # Load each Parquet file
        for parquet_file in parquet_files:
            with open(parquet_file, "rb") as source_file:
                job = self.client.load_table_from_file(
                    source_file, table_id, job_config=job_config
                )
                job.result()  # Wait for job to complete
        
        table = self.client.get_table(table_id)
        logger.info(f"Loaded {table.num_rows} rows into {table_id}")


class SnowflakeLoader(WarehouseLoader):
    """Snowflake loader"""
    
    def __init__(self, staging_path: str = "./data/staging", **config):
        super().__init__(WarehouseType.SNOWFLAKE, staging_path, **config)
        try:
            import snowflake.connector
            from snowflake.connector.pandas_tools import write_pandas
            self.snowflake = snowflake.connector
            self.write_pandas = write_pandas
        except ImportError:
            raise ImportError(
                "Snowflake loader requires: pip install snowflake-connector-python[pandas] pyarrow"
            )
        
        self.account = config.get("account", os.getenv("SNOWFLAKE_ACCOUNT"))
        self.user = config.get("user", os.getenv("SNOWFLAKE_USER"))
        self.password = config.get("password", os.getenv("SNOWFLAKE_PASSWORD"))
        self.warehouse = config.get("warehouse", os.getenv("SNOWFLAKE_WAREHOUSE"))
        self.database = config.get("database", os.getenv("SNOWFLAKE_DATABASE", "NYC_TRANSIT"))
        
        if not all([self.account, self.user, self.password]):
            raise ValueError(
                "Snowflake credentials required. "
                "Set SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD environment variables"
            )
    
    def connect(self):
        """Connect to Snowflake"""
        self._connection = self.snowflake.connect(
            account=self.account,
            user=self.user,
            password=self.password,
            warehouse=self.warehouse,
            database=self.database,
        )
        logger.info(f"Connected to Snowflake account: {self.account}")
    
    def create_schema(self, schema_name: str):
        """Create schema if it doesn't exist"""
        cursor = self._connection.cursor()
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
        cursor.close()
        logger.info(f"Created schema: {schema_name}")
    
    def create_table(self, schema_name: str, table_name: str, schema: Dict[str, str], partition_column: Optional[str] = None):
        """Create table with given schema"""
        columns = ", ".join([f"{col} {self._convert_type_to_snowflake(dtype)}" for col, dtype in schema.items()])
        full_table_name = f"{schema_name}.{table_name}"
        
        cursor = self._connection.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {full_table_name} (
                {columns}
            )
        """)
        cursor.close()
        logger.info(f"Created table: {full_table_name}")
    
    def _convert_type_to_snowflake(self, dtype: str) -> str:
        """Convert Python/SQL type to Snowflake type"""
        type_mapping = {
            "string": "VARCHAR",
            "int": "INTEGER",
            "integer": "INTEGER",
            "bigint": "NUMBER",
            "long": "NUMBER",
            "double": "FLOAT",
            "float": "DOUBLE",
            "boolean": "BOOLEAN",
            "date": "DATE",
            "timestamp": "TIMESTAMP_NTZ",
            "datetime": "TIMESTAMP_NTZ",
        }
        dtype_lower = dtype.lower()
        return type_mapping.get(dtype_lower, "VARCHAR")
    
    def load_data(self, schema_name: str, table_name: str, source_path: Path, mode: str = "append"):
        """Load data from Parquet files to Snowflake"""
        import pandas as pd
        
        full_table_name = f"{schema_name}.{table_name}"
        
        # Read all Parquet files
        parquet_files = list(source_path.glob("**/*.parquet"))
        if not parquet_files:
            logger.warning(f"No Parquet files found in {source_path}")
            return
        
        logger.info(f"Loading {len(parquet_files)} Parquet files to Snowflake...")
        
        # Read and combine all Parquet files
        dfs = []
        for parquet_file in parquet_files:
            df = pd.read_parquet(parquet_file)
            dfs.append(df)
        
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Write to Snowflake
        success, nchunks, nrows, _ = self.write_pandas(
            self._connection,
            combined_df,
            table_name.upper(),
            schema=schema_name.upper(),
            overwrite=(mode == "overwrite")
        )
        
        if success:
            logger.info(f"Loaded {nrows} rows into {full_table_name}")
        else:
            logger.error(f"Failed to load data into {full_table_name}")


def create_loader(
    warehouse_type: str,
    staging_path: str = "./data/staging",
    **config
) -> WarehouseLoader:
    """
    Factory function to create warehouse loader
    
    Args:
        warehouse_type: One of "redshift", "bigquery", "snowflake"
        staging_path: Path to staging Parquet files
        **config: Warehouse-specific configuration
        
    Returns:
        WarehouseLoader instance
    """
    warehouse_type_enum = WarehouseType(warehouse_type.lower())
    
    if warehouse_type_enum == WarehouseType.REDSHIFT:
        return RedshiftLoader(staging_path, **config)
    elif warehouse_type_enum == WarehouseType.BIGQUERY:
        return BigQueryLoader(staging_path, **config)
    elif warehouse_type_enum == WarehouseType.SNOWFLAKE:
        return SnowflakeLoader(staging_path, **config)
    else:
        raise ValueError(f"Unsupported warehouse type: {warehouse_type}")


# Schema definitions for vehicle_positions and trip_updates
VEHICLE_POSITIONS_SCHEMA = {
    "feed_timestamp_dt": "timestamp",
    "feed_timestamp_unix": "bigint",
    "gtfs_version": "string",
    "entity_id": "string",
    "vehicle_id": "string",
    "train_id": "string",
    "line": "string",
    "latitude": "double",
    "longitude": "double",
    "bearing": "double",
    "speed": "double",
    "vehicle_timestamp_dt": "timestamp",
    "vehicle_timestamp_unix": "bigint",
    "stop_sequence": "integer",
    "stop_id": "string",
    "ingestion_timestamp": "timestamp",
}

TRIP_UPDATES_SCHEMA = {
    "feed_timestamp_dt": "timestamp",
    "feed_timestamp_unix": "bigint",
    "gtfs_version": "string",
    "entity_id": "string",
    "train_id": "string",
    "line": "string",
    "trip_timestamp_dt": "timestamp",
    "trip_timestamp_unix": "bigint",
    "stop_sequence": "integer",
    "stop_id": "string",
    "arrival_time_dt": "timestamp",
    "arrival_time_unix": "bigint",
    "arrival_delay_seconds": "integer",
    "departure_time_dt": "timestamp",
    "departure_time_unix": "bigint",
    "departure_delay_seconds": "integer",
    "delay_seconds": "integer",
    "ingestion_timestamp": "timestamp",
}


def load_to_warehouse(
    warehouse_type: str,
    feed_type: str,
    schema_name: str = "nyc_transit",
    staging_path: str = "./data/staging",
    mode: str = "append",
    **warehouse_config
):
    """
    Convenience function to load feed data to warehouse
    
    Args:
        warehouse_type: "redshift", "bigquery", or "snowflake"
        feed_type: "vehicle_positions" or "trip_updates"
        schema_name: Schema/dataset name in warehouse
        staging_path: Path to staging Parquet files
        mode: "append" or "overwrite"
        **warehouse_config: Warehouse-specific configuration
    """
    loader = create_loader(warehouse_type, staging_path, **warehouse_config)
    
    try:
        loader.connect()
        loader.create_schema(schema_name)
        
        if feed_type == "vehicle_positions":
            table_name = "vehicle_positions"
            schema = VEHICLE_POSITIONS_SCHEMA
            source_path = Path(staging_path) / "vehicle_positions"
        elif feed_type == "trip_updates":
            table_name = "trip_updates"
            schema = TRIP_UPDATES_SCHEMA
            source_path = Path(staging_path) / "trip_updates"
        else:
            raise ValueError(f"Unknown feed type: {feed_type}")
        
        loader.create_table(schema_name, table_name, schema)
        loader.load_data(schema_name, table_name, source_path, mode=mode)
        
        logger.info(f"Successfully loaded {feed_type} to {warehouse_type}")
        
    finally:
        loader.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Load ETL data to warehouse")
    parser.add_argument("--warehouse", required=True, choices=["redshift", "bigquery", "snowflake"],
                       help="Warehouse type")
    parser.add_argument("--feed-type", required=True, choices=["vehicle_positions", "trip_updates", "all"],
                       help="Feed type to load")
    parser.add_argument("--schema", default="nyc_transit", help="Schema/dataset name")
    parser.add_argument("--staging-path", default="./data/staging", help="Path to staging Parquet files")
    parser.add_argument("--mode", default="append", choices=["append", "overwrite"],
                       help="Load mode")
    
    args = parser.parse_args()
    
    feed_types = ["vehicle_positions", "trip_updates"] if args.feed_type == "all" else [args.feed_type]
    
    for feed_type in feed_types:
        logger.info(f"Loading {feed_type} to {args.warehouse}...")
        load_to_warehouse(
            warehouse_type=args.warehouse,
            feed_type=feed_type,
            schema_name=args.schema,
            staging_path=args.staging_path,
            mode=args.mode,
        )

