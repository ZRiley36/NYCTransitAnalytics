from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from database import check_connection as check_db, close_pool
from redis_client import check_connection as check_redis, close_client
from gtfs_rt_connector import GTFSRTConnector, FeedType
from gtfs_interpreter import router as gtfs_router


# Global connector instance
gtfs_connector: GTFSRTConnector | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    global gtfs_connector
    
    # Startup
    # Initialize GTFS-RT connector (doesn't start automatically)
    gtfs_connector = GTFSRTConnector(
        storage_path="./data/gtfs_rt",
        poll_interval=20,
        max_retries=3,
        retry_delay=5.0,
    )
    async with gtfs_connector:
        yield
    
    # Shutdown
    if gtfs_connector:
        await gtfs_connector.stop()
    await close_pool()
    await close_client()


app = FastAPI(
    title="NYC Transit Analytics API",
    lifespan=lifespan
)

# Include routers
app.include_router(gtfs_router)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "nyc-transit-analytics"}


@app.get("/health/db")
async def health_db():
    """Database connection health check"""
    result = await check_db()
    return result


@app.get("/health/redis")
async def health_redis():
    """Redis connection health check"""
    result = await check_redis()
    return result


@app.get("/health/all")
async def health_all():
    """Check all services (API, Database, Redis)"""
    db_status = await check_db()
    redis_status = await check_redis()
    
    all_healthy = (
        db_status.get("status") == "connected" and
        redis_status.get("status") == "connected"
    )
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "api": {"status": "healthy"},
        "database": db_status,
        "redis": redis_status
    }


@app.post("/gtfs-rt/start")
async def start_connector():
    """Start GTFS-RT feed polling"""
    global gtfs_connector
    if not gtfs_connector:
        raise HTTPException(status_code=500, detail="Connector not initialized")
    
    if gtfs_connector.is_running:
        return {"status": "already_running", "message": "Connector is already running"}
    
    await gtfs_connector.start()
    return {
        "status": "started",
        "message": "GTFS-RT connector started",
        "poll_interval": gtfs_connector.poll_interval,
    }


@app.post("/gtfs-rt/stop")
async def stop_connector():
    """Stop GTFS-RT feed polling"""
    global gtfs_connector
    if not gtfs_connector:
        raise HTTPException(status_code=500, detail="Connector not initialized")
    
    if not gtfs_connector.is_running:
        return {"status": "already_stopped", "message": "Connector is not running"}
    
    await gtfs_connector.stop()
    return {"status": "stopped", "message": "GTFS-RT connector stopped"}


@app.get("/gtfs-rt/status")
async def connector_status():
    """Get GTFS-RT connector status and statistics"""
    global gtfs_connector
    if not gtfs_connector:
        raise HTTPException(status_code=500, detail="Connector not initialized")
    
    stats = gtfs_connector.get_stats()
    return {
        "is_running": gtfs_connector.is_running,
        "poll_interval": gtfs_connector.poll_interval,
        "storage_path": str(gtfs_connector.storage_path),
        "stats": stats,
    }


@app.post("/gtfs-rt/fetch")
async def fetch_feed_once(feed_type: str = "vehicle_positions"):
    """Manually trigger a single feed fetch"""
    global gtfs_connector
    if not gtfs_connector:
        raise HTTPException(status_code=500, detail="Connector not initialized")
    
    try:
        # Convert string to FeedType enum
        try:
            feed_type_enum = FeedType(feed_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid feed_type. Must be one of: {[ft.value for ft in FeedType]}"
            )
        
        filepath = await gtfs_connector.fetch_and_save(feed_type_enum)
        if filepath:
            return {
                "status": "success",
                "message": "Feed fetched and saved",
                "feed_type": feed_type_enum.value,
                "filepath": filepath,
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to fetch feed")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching feed: {str(e)}")


