"""
Deploy Prefect Flow for Scheduled GTFS-RT Ingestion

This script creates a Prefect deployment that runs the GTFS-RT ingestion flow
on a schedule. The deployment can be managed via Prefect UI or CLI.

Usage:
    python deploy_scheduler.py
    
    # Or specify schedule interval (in minutes)
    python deploy_scheduler.py --interval 30
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import timedelta

# Verify Prefect is available
try:
    from prefect import flow, task
except ImportError as e:
    print("=" * 60)
    print("ERROR: Prefect is not installed in this Python environment!")
    print("=" * 60)
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print("\nTo fix this:")
    print("  1. Make sure you're using the correct Python interpreter")
    print("  2. Install Prefect: py -m pip install prefect")
    print("  3. Or install all dependencies: py -m pip install -r backend/requirements.txt")
    print("\nOn Windows, use 'py' instead of 'python':")
    print("  py deploy_scheduler.py")
    print("=" * 60)
    sys.exit(1)

# Add backend to path for imports
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from gtfs_ingestion_flow import gtfs_rt_ingestion_flow


def deploy_flow(
    interval_minutes: int = 30,
    cron_expression: str = None,
    work_queue_name: str = "gtfs-ingestion",
):
    """
    Deploy the GTFS-RT ingestion flow with a schedule using Prefect serve
    
    Args:
        interval_minutes: Interval between runs in minutes (default: 30)
        cron_expression: Cron expression (e.g., "*/30 * * * *" for every 30 minutes)
        work_queue_name: Name of the work queue for agents
    """
    # Get configuration from environment
    api_key = os.getenv("MTA_API_KEY")
    storage_path = os.getenv("GTFS_STORAGE_PATH", "./data/gtfs_rt")
    
    # Clamp interval to reasonable values (between 1 min and 24 hours)
    interval_minutes = max(1, min(interval_minutes, 1440))
    
    print(f"Deploying GTFS-RT ingestion flow:")
    print(f"  Schedule: {'Cron: ' + cron_expression if cron_expression else f'Interval: {interval_minutes} minutes'}")
    print(f"  Work queue: {work_queue_name}")
    print(f"  Storage path: {storage_path}")
    print(f"\nStarting server... Use Ctrl+C to stop")
    
    # Use serve to create a deployment and start the server
    # Note: work_queue_name parameter removed as it's not supported in Prefect 3.4.0 serve()
    if cron_expression:
        gtfs_rt_ingestion_flow.serve(
            name="gtfs-rt-ingestion-scheduled",
            description="Scheduled GTFS-RT feed ingestion from NYC MTA",
            tags=["gtfs", "ingestion", "scheduled"],
            parameters={
                "storage_path": storage_path,
                "api_key": api_key,
                "ingest_both": True,
            },
            cron=cron_expression,
            timezone="UTC",
            limit=1,  # Only one run at a time
        )
    else:
        gtfs_rt_ingestion_flow.serve(
            name="gtfs-rt-ingestion-scheduled",
            description="Scheduled GTFS-RT feed ingestion from NYC MTA",
            tags=["gtfs", "ingestion", "scheduled"],
            parameters={
                "storage_path": storage_path,
                "api_key": api_key,
                "ingest_both": True,
            },
            interval=timedelta(minutes=interval_minutes),
            limit=1,  # Only one run at a time
        )


def main():
    """Main entry point for deployment script"""
    parser = argparse.ArgumentParser(
        description="Deploy Prefect flow for scheduled GTFS-RT ingestion"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Interval between runs in minutes (default: 30)",
    )
    parser.add_argument(
        "--cron",
        type=str,
        default=None,
        help="Cron expression (e.g., '*/30 * * * *'). If provided, overrides --interval",
    )
    parser.add_argument(
        "--work-queue",
        type=str,
        default="gtfs-ingestion",
        help="Name of the work queue (default: gtfs-ingestion)",
    )
    
    args = parser.parse_args()
    
    deploy_flow(
        interval_minutes=args.interval,
        cron_expression=args.cron,
        work_queue_name=args.work_queue,
    )


if __name__ == "__main__":
    main()

