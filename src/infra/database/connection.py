"""
Database connection management.
"""
import logging
from typing import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import StaticPool

from src.core.config import settings

logger = logging.getLogger(__name__)

# Create declarative base
Base = declarative_base()

# Configure engine based on database type
if "sqlite" in settings.database.url:
    # SQLite specific configuration
    engine = create_engine(
        settings.database.url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.database.echo
    )
    
    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    # PostgreSQL/MySQL configuration
    engine = create_engine(
        settings.database.url,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
        echo=settings.database.echo
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database sessions.
    Use with FastAPI's Depends().
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Use in non-FastAPI contexts.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database tables.
    Call this on application startup.
    """
    # Import models to ensure they're registered with Base
    from src.infra.database import models  # noqa: F401
    
    logger.info(f"Initializing database at: {settings.database.url}")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.")


def drop_db() -> None:
    """
    Drop all database tables.
    USE WITH CAUTION - mainly for testing.
    """
    logger.warning("Dropping all database tables!")
    Base.metadata.drop_all(bind=engine)
