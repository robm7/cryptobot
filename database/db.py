"""Database configuration and session management for the cryptobot application."""

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    AsyncEngine
)
from sqlalchemy.orm import sessionmaker, declarative_base, scoped_session
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import create_engine

load_dotenv()

# Flask-SQLAlchemy setup for sync operations
db = SQLAlchemy()

# Async SQLAlchemy setup
DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@localhost:5432/cryptobot_db'

# The _get_database_url function is no longer needed as DATABASE_URL is set directly.
# If you need dynamic URL generation or SQLite fallback, this section would need to be adjusted.

Base = declarative_base()

async def verify_db_connection():
    """Verify database connectivity by establishing a test connection."""
    test_engine = None  # Initialize to ensure it's defined in finally
    try:
        # For PostgreSQL, test a connection
        test_engine = create_async_engine(
            DATABASE_URL,
            poolclass=NullPool,
            connect_args={"connect_timeout": 5} # Standard for asyncpg
        )
        async def _test_conn_inner(): # Renamed to avoid conflict if verify_db_connection itself is called _test_conn
            async with test_engine.connect() as conn:
                await conn.execute("SELECT 1") # Standard SQL test query
        
        await _test_conn_inner() # Directly await the async function

    except Exception as e:
        raise ConnectionError(f"Failed to connect to database: {str(e)}") from e
    finally:
        if test_engine and hasattr(test_engine, 'dispose'): # Check if test_engine was successfully created and has dispose
            await test_engine.dispose() # Use await for async dispose

# Async engine and session
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=True, # Adjust echo based on existing config or best practice
    # PostgreSQL specific pool settings (can be adjusted)
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False, # Common default, adjust if project has specific needs
    autocommit=False,
    autoflush=False,
)

# Sync engine for tests
def _get_sync_db_url():
    """Get sync database URL with test support."""
    if os.getenv("TESTING") == "1":
        test_db = os.getenv("TEST_DB_PATH")
        if test_db:
            return f"sqlite:///{Path(test_db).absolute()}"
        return "sqlite:///:memory:"
    return os.getenv("SYNC_DATABASE_URL", f"sqlite:///{Path('database/cryptobot.db').absolute()}")

sync_db_url = _get_sync_db_url()
if sync_db_url.startswith("sqlite"):
    # SQLite doesn't support connection pooling
    sync_engine = create_engine(
        sync_db_url,
        echo=True,
        poolclass=NullPool
    )
else:
    # Other databases support connection pooling
    sync_engine = create_engine(
        sync_db_url,
        echo=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True
    )
SessionLocal = sessionmaker(bind=sync_engine)

@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session with transaction handling.
    
    Yields:
        AsyncSession: Database session
        
    Example:
        async with get_db() as db:
            # Use db session
            await db.commit()
    """
    async with AsyncSessionLocal() as session: # Use new AsyncSessionLocal
        try:
            yield session
            await session.commit()
        except SQLAlchemyError:
            await session.rollback()
            raise
        finally:
            await session.close()

@contextmanager
def get_sync_db() -> Generator[scoped_session, None, None]:
    """
    Dependency for getting sync database session for tests.
    
    Yields:
        scoped_session: Database session
    """
    session = scoped_session(SessionLocal)
    try:
        yield session
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        session.remove()

async def init_db(app=None) -> None: # Make init_db async
    """Initialize database tables."""
    # Only initialize async tables here - sync tables are handled by Flask-SQLAlchemy
    async def _init_async_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    await _init_async_db() # Await the inner async function

__all__ = [
    'Base',
    'db', # Retained for Flask-SQLAlchemy sync parts if still used elsewhere
    'engine',
    'AsyncSessionLocal', # Changed from 'async_session'
    'get_db',
    'get_sync_db',
    'init_db',
    'SessionLocal',
    'verify_db_connection'
]