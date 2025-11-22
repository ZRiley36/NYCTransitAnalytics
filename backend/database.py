"""Database connection utilities"""
import asyncpg
import os
from typing import Optional

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/nyc_transit")

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Get or create database connection pool"""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL)
    return _pool


async def check_connection() -> dict:
    """Test database connection"""
    try:
        pool = await get_pool()
        async with pool.acquire() as connection:
            result = await connection.fetchval("SELECT version()")
            return {
                "status": "connected",
                "database": "postgresql",
                "version": result.split(",")[0] if result else "unknown"
            }
    except Exception as e:
        return {
            "status": "error",
            "database": "postgresql",
            "error": str(e)
        }


async def close_pool():
    """Close database connection pool"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

