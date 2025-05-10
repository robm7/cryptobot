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
def _get_database_url():
    """Get database URL with proper validation and test support."""
    url = os.getenv("DATABASE_URL")
    
    # Handle test environment
    if os.getenv("TESTING") == "1":
        return "sqlite+aiosqlite:///:memory:"
    
    # Default to SQLite if no URL provided
    if not url:
        db_path = Path('database/cryptobot.db').absolute()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite+aiosqlite:///{db_path}"
    
    # Validate database URLs
    protocol_pattern = r'^(?P<protocol>sqlite\+?aiosqlite?|postgres(ql)?|mysql(\+pymysql)?)://'
    if not re.match(protocol_pattern, url, re.IGNORECASE):
        raise ValueError(
            f"Invalid database URL format - must use one of these protocols:\n"
            f"- SQLite: sqlite:///path or sqlite+aiosqlite:///path\n"
            f"- PostgreSQL: postgresql:// or postgres://\n"
            f"- MySQL: mysql:// or mysql+pymysql://"
        )
        
    # Special handling for SQLite paths
    if url.lower().startswith(("sqlite:///", "sqlite+aiosqlite:///")) and not url.lower().startswith("sqlite:///:memory:"):
        path_part = url.split("///")[-1]
        path_obj = Path(path_part)
        
        # Convert relative paths to absolute based on project root
        if not path_obj.is_absolute():
            path_obj = Path(__file__).parent.parent / path_part
            
        # Validate path exists or can be created
        if path_obj.exists():
            if not path_obj.is_file():
                raise ValueError(f"Database path exists but is not a file: {path_obj}")
        else:
            try:
                path_obj.parent.mkdir(parents=True, exist_ok=True)
                path_obj.touch(exist_ok=True)
            except (OSError, PermissionError) as e:
                raise ValueError(f"Invalid database path: {str(e)}") from e
                
        # Normalize path for cross-platform compatibility
        normalized_path = str(path_obj.resolve())
        url = f"sqlite+aiosqlite:///{normalized_path}"
    
    return url

DATABASE_URL = _get_database_url()

Base = declarative_base()

def verify_db_connection():
    """Verify database connectivity by establishing a test connection."""
    try:
        if DATABASE_URL.startswith("sqlite"):
            # For SQLite, just check if we can create the engine
            test_engine = create_async_engine(DATABASE_URL)
            test_engine.connect()
        else:
            # For other databases, actually test a connection
            test_engine = create_async_engine(
                DATABASE_URL,
                poolclass=NullPool,
                connect_args={"connect_timeout": 5}
            )
            async def _test_conn():
                async with test_engine.connect() as conn:
                    await conn.execute("SELECT 1")
            import asyncio
            asyncio.run(_test_conn())
    except Exception as e:
        raise ConnectionError(f"Failed to connect to database: {str(e)}") from e
    finally:
        if 'test_engine' in locals():
            test_engine.sync_engine.dispose()

# Async engine and session
# Configure engine based on database type
if DATABASE_URL.startswith("sqlite"):
    # SQLite/aiosqlite doesn't support connection pooling
    engine: AsyncEngine = create_async_engine(
        DATABASE_URL,
        echo=True,
        poolclass=NullPool,
        connect_args={"check_same_thread": False}
    )
else:
    # Other databases support connection pooling
    engine: AsyncEngine = create_async_engine(
        DATABASE_URL,
        echo=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False}
    )

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
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
    async with async_session() as session:
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

def init_db(app=None) -> None:
    """Initialize database tables."""
    # Only initialize async tables here - sync tables are handled by Flask-SQLAlchemy
    async def _init_async_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    import asyncio
    asyncio.run(_init_async_db())

__all__ = [
    'Base',
    'db',
    'engine',
    'async_session',
    'get_db',
    'get_sync_db',
    'init_db',
    'SessionLocal',
    'verify_db_connection'
]