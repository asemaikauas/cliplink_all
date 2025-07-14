"""
Database configuration and session management for Cliplink Backend

This module handles PostgreSQL database connections using SQLAlchemy
with async support via asyncpg.
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator

from dotenv import load_dotenv
load_dotenv()


# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    pool_pre_ping=True,
    pool_recycle=300,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base for SQLAlchemy models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session for FastAPI endpoints
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_db_session() -> AsyncSession:
    """
    Get a database session for background tasks
    """
    return AsyncSessionLocal()


async def init_db():
    """
    Initialize database tables
    """
    async with engine.begin() as conn:
        # Import models to ensure they're registered
        from .models import Base
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """
    Close database connections
    """
    await engine.dispose() 