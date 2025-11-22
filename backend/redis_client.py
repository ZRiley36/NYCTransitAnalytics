"""Redis connection utilities"""
from redis import asyncio as redis
import os
from typing import Optional

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_client: Optional[redis.Redis] = None


def get_client() -> redis.Redis:
    """Get or create Redis client"""
    global _client
    if _client is None:
        _client = redis.from_url(REDIS_URL)
    return _client


async def check_connection() -> dict:
    """Test Redis connection"""
    try:
        client = get_client()
        pong = await client.ping()
        info = await client.info("server")
        return {
            "status": "connected" if pong else "error",
            "database": "redis",
            "version": info.get("redis_version", "unknown"),
            "connected_clients": info.get("connected_clients", 0)
        }
    except Exception as e:
        return {
            "status": "error",
            "database": "redis",
            "error": str(e)
        }


async def close_client():
    """Close Redis client"""
    global _client
    if _client:
        await _client.close()
        _client = None

