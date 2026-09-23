import asyncpg
import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
import google.auth
from google.auth.transport.requests import Request

from config import settings

logger = logging.getLogger("workkbot.db")

_pool: Optional[asyncpg.Pool] = None


async def get_db_password() -> str:
    """Returns IAM auth token or configured password."""
    if settings.DB_USE_IAM_AUTH:
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/sqlservice.admin"]
        )
        credentials.refresh(Request())
        return credentials.token
    return settings.DB_PASSWORD


async def init_db_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        password = await get_db_password()
        ssl_arg = False if settings.DB_SSL_MODE == "disable" else None
        
        logger.info(
            "Initializing database connection pool to %s:%s/%s (IAM Auth: %s)",
            settings.DB_HOST,
            settings.DB_PORT,
            settings.DB_NAME,
            settings.DB_USE_IAM_AUTH
        )
        
        _pool = await asyncpg.create_pool(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=password,
            database=settings.DB_NAME,
            min_size=2,
            max_size=20,
            ssl=ssl_arg,
            command_timeout=30.0
        )
    return _pool


async def close_db_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed.")


def get_pool() -> Optional[asyncpg.Pool]:
    return _pool


@asynccontextmanager
async def get_connection(user_id: Optional[str] = None) -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Acquires a connection and enforces tenant isolation via Row-Level Security.
    If user_id is provided, executes 'SET LOCAL app.current_user_id' within a transaction.
    """
    pool = get_pool()
    if pool is None:
        raise RuntimeError("Database pool has not been initialized.")

    async with pool.acquire() as conn:
        if user_id:
            async with conn.transaction():
                # SET LOCAL ensures the setting is strictly scoped to this transaction
                await conn.execute("SELECT set_config('app.current_user_id', $1, true)", user_id)
                yield conn
        else:
            yield conn
