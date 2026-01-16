"""Health check endpoints for monitoring and orchestration."""
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from backend.database import get_db

logger = structlog.get_logger()
router = APIRouter()


async def check_database(db: AsyncSession) -> dict:
    """Check database connectivity."""
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        return {"status": "healthy", "latency_ms": None}
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return {"status": "unhealthy", "error": str(e)}


async def check_redis() -> dict:
    """Check Redis connectivity."""
    try:
        import redis.asyncio as redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        client = redis.from_url(redis_url)
        await client.ping()
        await client.close()
        return {"status": "healthy"}
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return {"status": "unhealthy", "error": str(e)}


@router.get("/health")
async def health_check() -> dict:
    """
    Basic health check - returns 200 if service is running.
    Use this for simple liveness probes.
    """
    return {
        "status": "healthy",
        "service": "equities-ai",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/live")
async def liveness_probe() -> dict:
    """
    Kubernetes liveness probe.
    Returns 200 if the application is running.
    """
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_probe(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Kubernetes readiness probe.
    Checks all dependencies (database, Redis, etc.) are available.
    Returns 200 only if all dependencies are healthy.
    """
    checks = {}
    overall_healthy = True

    # Check database
    db_check = await check_database(db)
    checks["database"] = db_check
    if db_check["status"] != "healthy":
        overall_healthy = False

    # Check Redis
    redis_check = await check_redis()
    checks["redis"] = redis_check
    if redis_check["status"] != "healthy":
        overall_healthy = False

    return {
        "status": "ready" if overall_healthy else "not_ready",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/detailed")
async def detailed_health(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Detailed health check with all system information.
    Useful for debugging and monitoring dashboards.
    """
    checks = {}

    # Database check
    db_check = await check_database(db)
    checks["database"] = db_check

    # Redis check
    redis_check = await check_redis()
    checks["redis"] = redis_check

    # Calculate overall status
    all_healthy = all(
        check.get("status") == "healthy"
        for check in checks.values()
    )

    return {
        "status": "healthy" if all_healthy else "degraded",
        "service": "equities-ai",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
