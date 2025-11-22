"""
Example usage of Spark ETL job

This script demonstrates how to use the Spark ETL job programmatically.
"""

from etl.spark_etl import GTFSRTETL

def main():
    # Initialize ETL job
    etl = GTFSRTETL(
        raw_data_path="./data/gtfs_rt",
        staging_path="./data/staging",
        spark_master="local[*]"
    )
    
    try:
        # Process all feed types
        print("Processing all feeds...")
        etl.process_all()
        
        # Or process specific feed types
        # etl.process_vehicle_positions()
        # etl.process_trip_updates()
        
        # Read back the processed data
        print("\nReading processed vehicle positions...")
        vehicle_df = etl.spark.read.parquet("./data/staging/vehicle_positions")
        print(f"Total vehicle positions: {vehicle_df.count()}")
        print("\nSample data:")
        vehicle_df.select("line", "train_id", "vehicle_timestamp_dt", "latitude", "longitude").show(10)
        
        print("\nReading processed trip updates...")
        trip_df = etl.spark.read.parquet("./data/staging/trip_updates")
        print(f"Total trip update records: {trip_df.count()}")
        print("\nSample data:")
        trip_df.select("line", "train_id", "stop_id", "delay_seconds", "departure_time_dt").show(10)
        
        # Example: Find delays by line
        print("\nDelays by line:")
        trip_df.groupBy("line") \
            .agg({"delay_seconds": "avg", "delay_seconds": "max"}) \
            .withColumnRenamed("avg(delay_seconds)", "avg_delay") \
            .withColumnRenamed("max(delay_seconds)", "max_delay") \
            .orderBy("avg_delay", ascending=False) \
            .show()
        
    finally:
        etl.stop()

if __name__ == "__main__":
    main()

