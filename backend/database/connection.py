import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import aiomysql

from backend.config import settings

logger = logging.getLogger(__name__)

pool: Optional[aiomysql.Pool] = None

async def create_pool() -> None:
    global pool
    try:
        pool = await aiomysql.create_pool(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            db=settings.db_name,
            charset="utf8mb4",
            autocommit=False,
            minsize=1,
            maxsize=10
        )
        logger.info(f"MySQL pool created: {settings.db_user}@{settings.db_host}:{settings.db_port}/{settings.db_name}")
    except Exception as e:
        raise RuntimeError(f"Database connection failed: {e}")

async def close_pool() -> None:
    global pool
    if pool is not None:
        pool.close()
        await pool.wait_closed()
        pool = None

@asynccontextmanager
async def get_connection() -> AsyncGenerator[aiomysql.Connection, None]:
    global pool
    if pool is None:
        raise RuntimeError("Database pool not initialized. Call create_pool() first.")
    
    async with pool.acquire() as conn:
        yield conn

async def get_cursor(conn: aiomysql.Connection, dict_cursor: bool = True):
    if dict_cursor:
        return await conn.cursor(aiomysql.DictCursor)
    return await conn.cursor()
