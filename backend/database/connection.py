"""Database connection and session management."""
import os
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session

# Get database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://equities:equities_dev_password@localhost:5432/equities_ai"
)

# Convert to async URL if needed
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Sync engine for migrations and simple operations
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async engine for FastAPI
async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


def get_db_sync() -> Session:
    """Get synchronous database session."""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Caller is responsible for closing


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session for FastAPI dependency injection."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
