"""GTFS-RT Feed Connector for NYC MTA"""
import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum

import httpx
from google.transit import gtfs_realtime_pb2


class FeedType(str, Enum):
    """GTFS-RT Feed types"""
    VEHICLE_POSITIONS = "vehicle_positions"
    TRIP_UPDATES = "trip_updates"
    ALERTS = "alerts"


class GTFSRTConnector:
    """Connector for GTFS-RT feeds from NYC MTA"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        storage_path: str = "./data/gtfs_rt",
        poll_interval: int = 20,
        max_retries: int = 3,
        retry_delay: float = 5.0,
    ):
        """
        Initialize GTFS-RT Connector
        
        Args:
            api_key: MTA API key (or use MTA_API_KEY env var)
            storage_path: Local storage path for raw feeds
            poll_interval: Polling interval in seconds (10-30s)
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.api_key = api_key or os.getenv("MTA_API_KEY", "")
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.poll_interval = max(10, min(30, poll_interval))  # Clamp to 10-30s
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # NYC MTA GTFS-RT Feed URLs (requires API key)
        # Using subway feeds - can be extended for other lines
        self.feed_urls = {
            FeedType.VEHICLE_POSITIONS: "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
            FeedType.TRIP_UPDATES: "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
        }
        
        self.client: Optional[httpx.AsyncClient] = None
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.stats = {
            "total_fetches": 0,
            "successful_fetches": 0,
            "failed_fetches": 0,
            "last_fetch_time": None,
            "last_error": None,
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"x-api-key": self.api_key} if self.api_key else {}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()
        if self.client:
            await self.client.aclose()
    
    async def fetch_feed(
        self,
        feed_type: FeedType = FeedType.VEHICLE_POSITIONS,
    ) -> Optional[bytes]:
        """
        Fetch GTFS-RT feed with retries
        
        Args:
            feed_type: Type of feed to fetch
            
        Returns:
            Raw feed bytes or None if failed
        """
        if not self.client:
            raise RuntimeError("Connector not initialized. Use async context manager")
        
        url = self.feed_urls.get(feed_type)
        if not url:
            raise ValueError(f"Unknown feed type: {feed_type}")
        
        for attempt in range(self.max_retries):
            try:
                self.stats["total_fetches"] += 1
                
                response = await self.client.get(
                    self.feed_urls[feed_type],
                    headers={"x-api-key": self.api_key} if self.api_key else {}
                )
                response.raise_for_status()
                
                self.stats["successful_fetches"] += 1
                self.stats["last_fetch_time"] = datetime.utcnow().isoformat()
                self.stats["last_error"] = None
                
                return response.content
                
            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                self.stats["last_error"] = error_msg
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    self.stats["failed_fetches"] += 1
                    raise
                    
            except (httpx.RequestError, Exception) as e:
                error_msg = str(e)
                self.stats["last_error"] = error_msg
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    self.stats["failed_fetches"] += 1
                    raise
    
    def parse_feed(self, feed_data: bytes, feed_type: FeedType = FeedType.VEHICLE_POSITIONS) -> Dict[str, Any]:
        """
        Parse GTFS-RT Protocol Buffer feed to JSON
        
        Args:
            feed_data: Raw Protocol Buffer feed data
            feed_type: Type of feed being parsed
            
        Returns:
            Parsed feed as dictionary
        """
        try:
            if feed_type == FeedType.VEHICLE_POSITIONS:
                feed = gtfs_realtime_pb2.FeedMessage()
                feed.ParseFromString(feed_data)
                
                vehicles = []
                for entity in feed.entity:
                    if entity.HasField("vehicle"):
                        vehicle = {
                            "id": entity.id,
                            "vehicle_id": entity.vehicle.vehicle.id if entity.vehicle.HasField("vehicle") else None,
                            "trip_id": entity.vehicle.trip.trip_id if entity.vehicle.HasField("trip") else None,
                            "route_id": entity.vehicle.trip.route_id if entity.vehicle.HasField("trip") else None,
                            "position": {
                                "latitude": entity.vehicle.position.latitude if entity.vehicle.HasField("position") else None,
                                "longitude": entity.vehicle.position.longitude if entity.vehicle.HasField("position") else None,
                                "bearing": entity.vehicle.position.bearing if entity.vehicle.HasField("position") else None,
                                "speed": entity.vehicle.position.speed if entity.vehicle.HasField("position") else None,
                            },
                            "timestamp": entity.vehicle.timestamp if entity.vehicle.HasField("timestamp") else None,
                            "current_stop_sequence": entity.vehicle.current_stop_sequence if entity.vehicle.HasField("current_stop_sequence") else None,
                            "stop_id": entity.vehicle.current_status if entity.vehicle.HasField("current_status") else None,
                        }
                        vehicles.append(vehicle)
                
                return {
                    "header": {
                        "gtfs_realtime_version": feed.header.gtfs_realtime_version,
                        "timestamp": feed.header.timestamp,
                    },
                    "vehicle_count": len(vehicles),
                    "vehicles": vehicles,
                }
            
            elif feed_type == FeedType.TRIP_UPDATES:
                feed = gtfs_realtime_pb2.FeedMessage()
                feed.ParseFromString(feed_data)
                
                trips = []
                for entity in feed.entity:
                    if entity.HasField("trip_update"):
                        trip_update = entity.trip_update
                        trip = {
                            "id": entity.id,
                            "trip_id": trip_update.trip.trip_id if trip_update.HasField("trip") else None,
                            "route_id": trip_update.trip.route_id if trip_update.HasField("trip") else None,
                            "stop_time_updates": [],
                            "timestamp": trip_update.timestamp if trip_update.HasField("timestamp") else None,
                        }
                        
                        for stop_time in trip_update.stop_time_update:
                            stop_update = {
                                "stop_sequence": stop_time.stop_sequence if stop_time.HasField("stop_sequence") else None,
                                "stop_id": stop_time.stop_id if stop_time.HasField("stop_id") else None,
                                "arrival": {
                                    "time": stop_time.arrival.time if stop_time.HasField("arrival") else None,
                                    "delay": stop_time.arrival.delay if stop_time.HasField("arrival") else None,
                                } if stop_time.HasField("arrival") else None,
                                "departure": {
                                    "time": stop_time.departure.time if stop_time.HasField("departure") else None,
                                    "delay": stop_time.departure.delay if stop_time.HasField("departure") else None,
                                } if stop_time.HasField("departure") else None,
                            }
                            trip["stop_time_updates"].append(stop_update)
                        
                        trips.append(trip)
                
                return {
                    "header": {
                        "gtfs_realtime_version": feed.header.gtfs_realtime_version,
                        "timestamp": feed.header.timestamp,
                    },
                    "trip_count": len(trips),
                    "trips": trips,
                }
            
            else:
                raise ValueError(f"Parsing not implemented for feed type: {feed_type}")
                
        except Exception as e:
            raise ValueError(f"Failed to parse feed: {str(e)}")
    
    async def save_feed(
        self,
        feed_data: bytes,
        feed_type: FeedType = FeedType.VEHICLE_POSITIONS,
    ) -> str:
        """
        Save raw feed to local storage
        
        Args:
            feed_data: Raw feed bytes
            feed_type: Type of feed
            
        Returns:
            Path to saved file
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{feed_type.value}_{timestamp}.pb"
        filepath = self.storage_path / filename
        
        # Save raw Protocol Buffer
        filepath.write_bytes(feed_data)
        
        # Also save parsed JSON for easier inspection
        try:
            parsed = self.parse_feed(feed_data, feed_type)
            json_filepath = self.storage_path / f"{feed_type.value}_{timestamp}.json"
            json_filepath.write_text(json.dumps(parsed, indent=2))
        except Exception as e:
            # Log but don't fail if parsing fails
            print(f"Warning: Failed to parse feed for JSON export: {e}")
        
        return str(filepath)
    
    async def fetch_and_save(
        self,
        feed_type: FeedType = FeedType.VEHICLE_POSITIONS,
    ) -> Optional[str]:
        """
        Fetch and save a single feed
        
        Args:
            feed_type: Type of feed to fetch
            
        Returns:
            Path to saved file or None if failed
        """
        try:
            feed_data = await self.fetch_feed(feed_type)
            if feed_data:
                filepath = await self.save_feed(feed_data, feed_type)
                return filepath
            return None
        except Exception as e:
            print(f"Error fetching/saving feed: {e}")
            return None
    
    async def _polling_loop(self):
        """Internal polling loop"""
        while self.is_running:
            try:
                # Fetch vehicle positions and trip updates
                await self.fetch_and_save(FeedType.VEHICLE_POSITIONS)
                await asyncio.sleep(2)  # Small delay between fetches
                await self.fetch_and_save(FeedType.TRIP_UPDATES)
            except Exception as e:
                print(f"Error in polling loop: {e}")
            
            await asyncio.sleep(self.poll_interval)
    
    async def start(self):
        """Start continuous polling"""
        if self.is_running:
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._polling_loop())
    
    async def stop(self):
        """Stop continuous polling"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connector statistics"""
        return self.stats.copy()

