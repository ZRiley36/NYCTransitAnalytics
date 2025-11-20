"""
Example Usage of GTFS-RT Ingestion Flow

This script demonstrates how to use the Prefect flow for GTFS-RT feed ingestion.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from gtfs_ingestion_flow import gtfs_rt_ingestion_flow


async def main():
    """Example: Run the ingestion flow once"""
    print("Running GTFS-RT ingestion flow...")
    
    # Get configuration from environment
    api_key = os.getenv("MTA_API_KEY")
    storage_path = os.getenv("GTFS_STORAGE_PATH", "./data/gtfs_rt")
    
    if not api_key:
        print("Warning: MTA_API_KEY environment variable not set")
    
    # Run the flow
    results = await gtfs_rt_ingestion_flow(
        storage_path=storage_path,
        api_key=api_key,
        ingest_both=True,
    )
    
    print("\nFlow completed!")
    print(f"Status: {results.get('flow_status')}")
    print(f"Success count: {results.get('success_count', 0)}/{results.get('total_count', 0)}")
    
    if "vehicle_positions" in results:
        vp_result = results["vehicle_positions"]
        print(f"\nVehicle Positions: {vp_result.get('status')}")
        if vp_result.get('status') == 'success':
            print(f"  File: {vp_result.get('filepath')}")
    
    if "trip_updates" in results:
        tu_result = results["trip_updates"]
        print(f"\nTrip Updates: {tu_result.get('status')}")
        if tu_result.get('status') == 'success':
            print(f"  File: {tu_result.get('filepath')}")
    
    if "error" in results:
        print(f"\nError: {results['error']}")


if __name__ == "__main__":
    asyncio.run(main())



