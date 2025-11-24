"""
Cloud Run service for GTFS-RT ingestion
Triggers GTFS-RT data collection and uploads to Cloud Storage
"""

import os
import asyncio
import json
from flask import Flask, request
from datetime import datetime
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from gtfs_rt_connector import GTFSRTConnector, FeedType
from cloud_storage import CloudStorageManager

app = Flask(__name__)

GCS_BUCKET = os.getenv("GCS_BUCKET_NAME")
MTA_API_KEY = os.getenv("MTA_API_KEY")


async def ingest_feed(connector: GTFSRTConnector, feed_type: FeedType):
    """Ingest a single feed type"""
    async with connector:
        feed_data = await connector.fetch_feed(feed_type)
        if feed_data:
            # Parse and save
            parsed = connector.parse_feed(feed_data, feed_type)
            filepath = await connector.save_feed(feed_data, feed_type)
            return {
                "status": "success",
                "filepath": filepath,
                "count": parsed.get("vehicle_count") or parsed.get("trip_count", 0)
            }
        else:
            return {"status": "failed", "error": "Failed to fetch feed"}


@app.route("/", methods=["GET", "POST"])
def ingest():
    """Main ingestion endpoint"""
    try:
        # Get API key from environment or request
        api_key = MTA_API_KEY or request.headers.get("X-MTA-API-KEY")
        
        if not api_key:
            return {"error": "MTA API key required"}, 400
        
        if not GCS_BUCKET:
            return {"error": "GCS_BUCKET_NAME not configured"}, 500
        
        # Initialize connector with GCS storage
        cloud_storage = CloudStorageManager.from_config(
            storage_type="gcs",
            bucket_name=GCS_BUCKET
        )
        
        connector = GTFSRTConnector(
            api_key=api_key,
            storage_path=f"gs://{GCS_BUCKET}/gtfs_rt",
            cloud_storage=cloud_storage
        )
        
        # Run async ingestion
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        results = {}
        
        # Vehicle positions
        vp_result = loop.run_until_complete(ingest_feed(connector, FeedType.VEHICLE_POSITIONS))
        results["vehicle_positions"] = vp_result
        
        # Trip updates
        tu_result = loop.run_until_complete(ingest_feed(connector, FeedType.TRIP_UPDATES))
        results["trip_updates"] = tu_result
        
        loop.close()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "results": results
        }, 200
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return {"status": "healthy"}, 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)

