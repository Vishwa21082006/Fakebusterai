"""
FakeBuster AI — API Router
Aggregates all sub-routers under /api/v1.
"""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.upload import router as upload_router
from app.api.url_ingest import router as url_ingest_router
from app.api.analysis import router as analysis_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(upload_router)
api_router.include_router(url_ingest_router)
api_router.include_router(analysis_router)
