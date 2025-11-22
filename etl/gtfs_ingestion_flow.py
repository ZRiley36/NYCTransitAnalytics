"""
Prefect Flow for GTFS-RT Feed Ingestion

This module defines Prefect flows for scheduled ingestion of GTFS-RT feeds
from NYC MTA. It handles both vehicle positions and trip updates with proper
logging and error handling.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

# Verify Prefect is available before proceeding
try:
    from prefect import flow, task, get_run_logger
    from prefect.task_runners import ConcurrentTaskRunner
except ImportError as e:
    import sys
    print("=" * 60)
    print("ERROR: Prefect is not installed in this Python environment!")
    print("=" * 60)
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print("\nTo fix this:")
    print("  1. Install Prefect: py -m pip install prefect")
    print("  2. Or install all dependencies: py -m pip install -r backend/requirements.txt")
    print("  3. Make sure you're using 'py' instead of 'python' on Windows")
    print("=" * 60)
    raise

# Add backend to path for imports
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from gtfs_rt_connector import GTFSRTConnector, FeedType


@task(
    name="ingest_vehicle_positions",
    retries=2,
    retry_delay_seconds=30,
    log_prints=True,
)
async def ingest_vehicle_positions_task(
    storage_path: str = "./data/gtfs_rt",
    api_key: Optional[str] = None,
) -> dict:
    """
    Task to ingest vehicle positions feed
    
    Args:
        storage_path: Path to store feed data
        api_key: MTA API key (or use MTA_API_KEY env var)
        
    Returns:
        Dictionary with ingestion results
    """
    logger = get_run_logger()
    
    try:
        logger.info(f"Starting vehicle positions ingestion at {datetime.utcnow().isoformat()}")
        
        async with GTFSRTConnector(
            api_key=api_key,
            storage_path=storage_path,
            poll_interval=20,
            max_retries=3,
            retry_delay=5.0,
        ) as connector:
            filepath = await connector.fetch_and_save(FeedType.VEHICLE_POSITIONS)
            
            if filepath:
                stats = connector.get_stats()
                logger.info(
                    f"Successfully ingested vehicle positions. "
                    f"File: {filepath}, "
                    f"Stats: {stats['successful_fetches']}/{stats['total_fetches']} successful"
                )
                return {
                    "status": "success",
                    "feed_type": "vehicle_positions",
                    "filepath": filepath,
                    "timestamp": datetime.utcnow().isoformat(),
                    "stats": stats,
                }
            else:
                raise Exception("Failed to fetch or save vehicle positions feed")
                
    except Exception as e:
        error_msg = f"Failed to ingest vehicle positions: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)


@task(
    name="ingest_trip_updates",
    retries=2,
    retry_delay_seconds=30,
    log_prints=True,
)
async def ingest_trip_updates_task(
    storage_path: str = "./data/gtfs_rt",
    api_key: Optional[str] = None,
) -> dict:
    """
    Task to ingest trip updates feed
    
    Args:
        storage_path: Path to store feed data
        api_key: MTA API key (or use MTA_API_KEY env var)
        
    Returns:
        Dictionary with ingestion results
    """
    logger = get_run_logger()
    
    try:
        logger.info(f"Starting trip updates ingestion at {datetime.utcnow().isoformat()}")
        
        async with GTFSRTConnector(
            api_key=api_key,
            storage_path=storage_path,
            poll_interval=20,
            max_retries=3,
            retry_delay=5.0,
        ) as connector:
            filepath = await connector.fetch_and_save(FeedType.TRIP_UPDATES)
            
            if filepath:
                stats = connector.get_stats()
                logger.info(
                    f"Successfully ingested trip updates. "
                    f"File: {filepath}, "
                    f"Stats: {stats['successful_fetches']}/{stats['total_fetches']} successful"
                )
                return {
                    "status": "success",
                    "feed_type": "trip_updates",
                    "filepath": filepath,
                    "timestamp": datetime.utcnow().isoformat(),
                    "stats": stats,
                }
            else:
                raise Exception("Failed to fetch or save trip updates feed")
                
    except Exception as e:
        error_msg = f"Failed to ingest trip updates: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)


@flow(
    name="gtfs_rt_ingestion_flow",
    description="Ingest GTFS-RT feeds (vehicle positions and trip updates) from NYC MTA",
    task_runner=ConcurrentTaskRunner(),
    log_prints=True,
)
async def gtfs_rt_ingestion_flow(
    storage_path: str = "./data/gtfs_rt",
    api_key: Optional[str] = None,
    ingest_both: bool = True,
) -> dict:
    """
    Main Prefect flow for GTFS-RT feed ingestion
    
    This flow orchestrates the ingestion of vehicle positions and trip updates
    feeds. It can run both feeds concurrently or just one based on configuration.
    
    Args:
        storage_path: Path to store feed data
        api_key: MTA API key (or use MTA_API_KEY env var)
        ingest_both: If True, ingest both feeds. If False, only vehicle positions
        
    Returns:
        Dictionary with ingestion results for all feeds
    """
    logger = get_run_logger()
    
    logger.info(f"Starting GTFS-RT ingestion flow at {datetime.utcnow().isoformat()}")
    
    results = {}
    
    try:
        if ingest_both:
            # Run both ingestion tasks concurrently
            vehicle_task = ingest_vehicle_positions_task(
                storage_path=storage_path,
                api_key=api_key,
            )
            trip_task = ingest_trip_updates_task(
                storage_path=storage_path,
                api_key=api_key,
            )
            
            # Wait for both to complete (ConcurrentTaskRunner handles concurrency)
            vehicle_result = await vehicle_task
            trip_result = await trip_task
            
            results["vehicle_positions"] = vehicle_result
            results["trip_updates"] = trip_result
        else:
            # Only ingest vehicle positions
            vehicle_result = await ingest_vehicle_positions_task(
                storage_path=storage_path,
                api_key=api_key,
            )
            results["vehicle_positions"] = vehicle_result
        
        # Log summary
        success_count = sum(
            1 for r in results.values() if r.get("status") == "success"
        )
        total_count = len(results)
        
        logger.info(
            f"Flow completed: {success_count}/{total_count} feeds ingested successfully. "
            f"Completed at {datetime.utcnow().isoformat()}"
        )
        
        results["flow_status"] = "completed"
        results["success_count"] = success_count
        results["total_count"] = total_count
        results["completed_at"] = datetime.utcnow().isoformat()
        
        return results
        
    except Exception as e:
        error_msg = f"Flow failed: {str(e)}"
        logger.error(error_msg)
        results["flow_status"] = "failed"
        results["error"] = str(e)
        results["completed_at"] = datetime.utcnow().isoformat()
        raise


if __name__ == "__main__":
    # For local testing
    import asyncio
    
    api_key = os.getenv("MTA_API_KEY")
    storage_path = os.getenv("GTFS_STORAGE_PATH", "./data/gtfs_rt")
    
    asyncio.run(gtfs_rt_ingestion_flow(
        storage_path=storage_path,
        api_key=api_key,
        ingest_both=True,
    ))

