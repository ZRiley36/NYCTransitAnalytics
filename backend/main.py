from fastapi import FastAPI
from contextlib import asynccontextmanager
from database import check_connection as check_db, close_pool
from redis_client import check_connection as check_redis, close_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup
    yield
    # Shutdown
    await close_pool()
    await close_client()


app = FastAPI(
    title="NYC Transit Analytics API",
    lifespan=lifespan
)


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


