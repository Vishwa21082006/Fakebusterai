"""
FakeBuster AI — Health & Readiness Endpoints
Used by Docker health checks and load balancers.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.rate_limiter import get_redis
from app.core.virus_scanner import virus_scanner
from app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Full health check — verifies connectivity to all backing services.
    """
    # Check PostgreSQL
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    # Check Redis
    redis_ok = False
    try:
        redis = get_redis()
        await redis.ping()
        redis_ok = True
    except Exception:
        pass

    # Check ClamAV
    clamav_ok = virus_scanner.is_available()

    overall = "ok" if (db_ok and redis_ok) else "degraded"

    return HealthResponse(
        status=overall,
        db=db_ok,
        redis=redis_ok,
        clamav=clamav_ok,
    )


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness probe — returns 200 only if critical services are up.
    """
    try:
        await db.execute(text("SELECT 1"))
        redis = get_redis()
        await redis.ping()
        return {"ready": True}
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"ready": False, "error": str(e)},
        )
