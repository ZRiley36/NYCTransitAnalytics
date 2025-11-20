"""
Run Prefect Agent for Scheduled GTFS-RT Ingestion

This script starts a Prefect agent that will execute scheduled deployments
for the GTFS-RT ingestion flow. The agent listens to a work queue and
runs flows when they are scheduled.

Usage:
    # Start agent (default work queue)
    python run_scheduler.py
    
    # Or specify work queue name
    python run_scheduler.py --work-queue gtfs-ingestion
    
Before running:
    1. Make sure Prefect server is running: prefect server start
    2. Deploy the flow: python deploy_scheduler.py (in a separate terminal)
    3. Run this agent: python run_scheduler.py
    
Alternatively, use Prefect CLI:
    prefect agent start -q gtfs-ingestion
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_agent(work_queue_name: str = "gtfs-ingestion"):
    """
    Start a Prefect agent to run scheduled flows
    
    This uses the Prefect CLI to start an agent that monitors the work queue
    and executes scheduled flow runs.
    
    Args:
        work_queue_name: Name of the work queue to monitor
    """
    print(f"Starting Prefect agent for work queue: {work_queue_name}")
    print("Press Ctrl+C to stop the agent")
    print("\nThe agent will monitor for scheduled flow runs...")
    
    try:
        # Start Prefect agent using CLI
        subprocess.run(
            ["prefect", "agent", "start", "-q", work_queue_name],
            check=True,
        )
    except KeyboardInterrupt:
        print("\n\nStopping agent...")
    except subprocess.CalledProcessError as e:
        print(f"\nError starting agent: {e}")
        print("\nMake sure Prefect is installed and Prefect server is running:")
        print("  pip install prefect")
        print("  prefect server start")
        sys.exit(1)
    except FileNotFoundError:
        print("\nError: Prefect CLI not found. Make sure Prefect is installed:")
        print("  pip install prefect")
        sys.exit(1)


def main():
    """Main entry point for scheduler agent"""
    parser = argparse.ArgumentParser(
        description="Run Prefect agent for scheduled GTFS-RT ingestion"
    )
    parser.add_argument(
        "--work-queue",
        type=str,
        default="gtfs-ingestion",
        help="Name of the work queue to monitor (default: gtfs-ingestion)",
    )
    
    args = parser.parse_args()
    
    run_agent(work_queue_name=args.work_queue)


if __name__ == "__main__":
    main()

