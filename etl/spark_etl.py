"""
Spark ETL Job for GTFS-RT Data

This module processes raw GTFS-RT JSON feeds and transforms them into
normalized Parquet files for analytics.

Features:
- Flattens nested JSON structures
- Normalizes Unix timestamps to datetime
- Extracts key fields: line (route_id), delay, train_id
- Writes to Parquet staging area
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_unixtime, explode, when, isnan, isnull,
    struct, lit, to_timestamp, date_format
)
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, 
    DoubleType, TimestampType, LongType
)


class GTFSRTETL:
    """Spark ETL job for processing GTFS-RT feeds"""
    
    def __init__(
        self,
        raw_data_path: str = "./data/gtfs_rt",
        staging_path: str = "./data/staging",
        spark_master: str = "local[*]",
        app_name: str = "GTFS-RT-ETL"
    ):
        """
        Initialize Spark ETL job
        
        Args:
            raw_data_path: Path to raw JSON feed files
            staging_path: Path to write Parquet staging files
            spark_master: Spark master URL
            app_name: Spark application name
        """
        self.raw_data_path = Path(raw_data_path)
        self.staging_path = Path(staging_path)
        self.staging_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize Spark session
        self.spark = SparkSession.builder \
            .appName(app_name) \
            .master(spark_master) \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
            .getOrCreate()
        
        # Set log level to reduce noise
        self.spark.sparkContext.setLogLevel("WARN")
    
    def normalize_timestamp(self, timestamp_col: str, output_col: str = None):
        """
        Convert Unix timestamp to datetime
        
        Args:
            timestamp_col: Column name with Unix timestamp
            output_col: Output column name (defaults to timestamp_col + '_dt')
        """
        if output_col is None:
            output_col = f"{timestamp_col}_dt"
        
        return from_unixtime(col(timestamp_col)).alias(output_col)
    
    def process_vehicle_positions(self, input_path: Optional[str] = None) -> None:
        """
        Process vehicle positions feed
        
        Transforms:
        - Flattens nested position structure
        - Normalizes timestamps
        - Extracts: line (route_id), train_id (trip_id), vehicle_id
        - Adds ingestion timestamp
        
        Args:
            input_path: Optional path to specific file, otherwise processes all vehicle_positions JSON files
        """
        if input_path:
            json_files = [input_path]
        else:
            # Find all vehicle_positions JSON files
            json_files = list(self.raw_data_path.glob("vehicle_positions_*.json"))
        
        if not json_files:
            print("No vehicle positions files found")
            return
        
        print(f"Processing {len(json_files)} vehicle positions file(s)...")
        
        # Read JSON files
        df = self.spark.read.option("multiline", "true").json([str(f) for f in json_files])
        
        # Explode vehicles array
        vehicles_df = df.select(
            col("header.timestamp").alias("feed_timestamp"),
            col("header.gtfs_realtime_version").alias("gtfs_version"),
            explode(col("vehicles")).alias("vehicle")
        )
        
        # Flatten vehicle structure
        normalized_df = vehicles_df.select(
            # Feed metadata
            self.normalize_timestamp("feed_timestamp", "feed_timestamp_dt"),
            col("feed_timestamp").alias("feed_timestamp_unix"),
            col("gtfs_version"),
            
            # Vehicle identifiers
            col("vehicle.id").alias("entity_id"),
            col("vehicle.vehicle_id").alias("vehicle_id"),
            col("vehicle.trip_id").alias("train_id"),
            col("vehicle.route_id").alias("line"),
            
            # Position data
            col("vehicle.position.latitude").alias("latitude"),
            col("vehicle.position.longitude").alias("longitude"),
            col("vehicle.position.bearing").alias("bearing"),
            col("vehicle.position.speed").alias("speed"),
            
            # Timestamps
            self.normalize_timestamp("vehicle.timestamp", "vehicle_timestamp_dt"),
            col("vehicle.timestamp").alias("vehicle_timestamp_unix"),
            
            # Stop information
            col("vehicle.current_stop_sequence").alias("stop_sequence"),
            col("vehicle.stop_id").alias("stop_id"),
        )
        
        # Add ingestion timestamp
        normalized_df = normalized_df.withColumn(
            "ingestion_timestamp",
            lit(datetime.utcnow()).cast(TimestampType())
        )
        
        # Write to Parquet staging area
        output_path = self.staging_path / "vehicle_positions"
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Partition by date for better query performance
        normalized_df.write \
            .mode("overwrite") \
            .partitionBy("line") \
            .parquet(str(output_path))
        
        print(f"✓ Processed {normalized_df.count()} vehicle positions")
        print(f"✓ Written to: {output_path}")
        
        return normalized_df
    
    def process_trip_updates(self, input_path: Optional[str] = None) -> None:
        """
        Process trip updates feed
        
        Transforms:
        - Explodes stop_time_updates array
        - Normalizes timestamps
        - Extracts: line (route_id), train_id (trip_id), delay
        - Adds ingestion timestamp
        
        Args:
            input_path: Optional path to specific file, otherwise processes all trip_updates JSON files
        """
        if input_path:
            json_files = [input_path]
        else:
            # Find all trip_updates JSON files
            json_files = list(self.raw_data_path.glob("trip_updates_*.json"))
        
        if not json_files:
            print("No trip updates files found")
            return
        
        print(f"Processing {len(json_files)} trip updates file(s)...")
        
        # Read JSON files
        df = self.spark.read.option("multiline", "true").json([str(f) for f in json_files])
        
        # Explode trips array
        trips_df = df.select(
            col("header.timestamp").alias("feed_timestamp"),
            col("header.gtfs_realtime_version").alias("gtfs_version"),
            explode(col("trips")).alias("trip")
        )
        
        # Explode stop_time_updates array
        stops_df = trips_df.select(
            # Feed metadata
            col("feed_timestamp"),
            col("gtfs_version"),
            
            # Trip identifiers
            col("trip.id").alias("entity_id"),
            col("trip.trip_id").alias("train_id"),
            col("trip.route_id").alias("line"),
            col("trip.timestamp").alias("trip_timestamp"),
            
            # Explode stop updates
            explode(col("trip.stop_time_updates")).alias("stop_update")
        )
        
        # Flatten stop update structure
        normalized_df = stops_df.select(
            # Feed metadata
            self.normalize_timestamp("feed_timestamp", "feed_timestamp_dt"),
            col("feed_timestamp").alias("feed_timestamp_unix"),
            col("gtfs_version"),
            
            # Trip identifiers
            col("entity_id"),
            col("train_id"),
            col("line"),
            self.normalize_timestamp("trip_timestamp", "trip_timestamp_dt"),
            col("trip_timestamp").alias("trip_timestamp_unix"),
            
            # Stop update data
            col("stop_update.stop_sequence").alias("stop_sequence"),
            col("stop_update.stop_id").alias("stop_id"),
            
            # Arrival data (may be null)
            when(col("stop_update.arrival").isNotNull(), col("stop_update.arrival.time")).alias("arrival_time_unix"),
            when(
                col("stop_update.arrival").isNotNull(),
                from_unixtime(col("stop_update.arrival.time"))
            ).otherwise(None).alias("arrival_time_dt"),
            when(col("stop_update.arrival").isNotNull(), col("stop_update.arrival.delay")).alias("arrival_delay_seconds"),
            
            # Departure data (may be null)
            when(col("stop_update.departure").isNotNull(), col("stop_update.departure.time")).alias("departure_time_unix"),
            when(
                col("stop_update.departure").isNotNull(),
                from_unixtime(col("stop_update.departure.time"))
            ).otherwise(None).alias("departure_time_dt"),
            when(col("stop_update.departure").isNotNull(), col("stop_update.departure.delay")).alias("departure_delay_seconds"),
        )
        
        # Calculate delay (use departure delay if available, otherwise arrival delay)
        normalized_df = normalized_df.withColumn(
            "delay_seconds",
            when(
                col("departure_delay_seconds").isNotNull(),
                col("departure_delay_seconds")
            ).otherwise(
                col("arrival_delay_seconds")
            )
        )
        
        # Add ingestion timestamp
        normalized_df = normalized_df.withColumn(
            "ingestion_timestamp",
            lit(datetime.utcnow()).cast(TimestampType())
        )
        
        # Write to Parquet staging area
        output_path = self.staging_path / "trip_updates"
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Partition by line for better query performance
        normalized_df.write \
            .mode("overwrite") \
            .partitionBy("line") \
            .parquet(str(output_path))
        
        print(f"✓ Processed {normalized_df.count()} trip update records")
        print(f"✓ Written to: {output_path}")
        
        return normalized_df
    
    def process_all(self, feed_types: Optional[List[str]] = None) -> None:
        """
        Process all feed types
        
        Args:
            feed_types: List of feed types to process (default: ['vehicle_positions', 'trip_updates'])
        """
        if feed_types is None:
            feed_types = ['vehicle_positions', 'trip_updates']
        
        print("=" * 60)
        print("Starting GTFS-RT ETL Job")
        print(f"Raw data path: {self.raw_data_path}")
        print(f"Staging path: {self.staging_path}")
        print("=" * 60)
        
        if 'vehicle_positions' in feed_types:
            print("\n[1/2] Processing vehicle positions...")
            self.process_vehicle_positions()
        
        if 'trip_updates' in feed_types:
            print("\n[2/2] Processing trip updates...")
            self.process_trip_updates()
        
        print("\n" + "=" * 60)
        print("ETL Job Complete!")
        print("=" * 60)
    
    def stop(self):
        """Stop Spark session"""
        if self.spark:
            self.spark.stop()


def main():
    """Main entry point for Spark ETL job"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GTFS-RT Spark ETL Job")
    parser.add_argument(
        "--raw-path",
        type=str,
        default=os.getenv("GTFS_RAW_PATH", "./data/gtfs_rt"),
        help="Path to raw JSON feed files"
    )
    parser.add_argument(
        "--staging-path",
        type=str,
        default=os.getenv("GTFS_STAGING_PATH", "./data/staging"),
        help="Path to write Parquet staging files"
    )
    parser.add_argument(
        "--feed-type",
        type=str,
        choices=['vehicle_positions', 'trip_updates', 'all'],
        default='all',
        help="Feed type to process"
    )
    parser.add_argument(
        "--spark-master",
        type=str,
        default=os.getenv("SPARK_MASTER", "local[*]"),
        help="Spark master URL"
    )
    
    args = parser.parse_args()
    
    # Initialize ETL job
    etl = GTFSRTETL(
        raw_data_path=args.raw_path,
        staging_path=args.staging_path,
        spark_master=args.spark_master
    )
    
    try:
        # Process feeds
        if args.feed_type == 'all':
            etl.process_all()
        elif args.feed_type == 'vehicle_positions':
            etl.process_vehicle_positions()
        elif args.feed_type == 'trip_updates':
            etl.process_trip_updates()
    finally:
        etl.stop()


if __name__ == "__main__":
    main()

