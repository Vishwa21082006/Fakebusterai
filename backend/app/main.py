"""
FakeBuster AI — FastAPI Application Factory
Central entrypoint configuring CORS, exception handlers,
lifespan events (DB + Redis init/shutdown), and all API routes.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.router import api_router
from app.config import get_settings
from app.core.exceptions import FakeBusterError, fakebuster_error_handler
from app.core.rate_limiter import init_redis, close_redis
from app.core.virus_scanner import virus_scanner
from app.database import engine, Base

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("fakebuster")

# Path to the frontend directory (relative to project root)
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager:
    - Startup: create tables, connect Redis, connect ClamAV
    - Shutdown: close Redis, dispose DB engine
    """
    logger.info("═══ FakeBuster AI Starting ═══")

    # Create database tables (dev convenience — use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured")

    # Initialize Redis (optional — rate limiting disabled if unavailable)
    try:
        await init_redis()
        logger.info("Redis connected")
    except Exception as exc:
        logger.warning("Redis unavailable — rate limiting disabled: %s", exc)

    # Connect ClamAV (optional — virus scanning disabled if unavailable)
    try:
        virus_scanner.connect()
    except Exception as exc:
        logger.warning("ClamAV unavailable — virus scanning disabled: %s", exc)

    logger.info("═══ FakeBuster AI Ready ═══")

    yield  # Application runs here

    # Shutdown
    logger.info("═══ FakeBuster AI Shutting Down ═══")
    try:
        await close_redis()
    except Exception:
        pass
    await engine.dispose()
    logger.info("═══ Shutdown Complete ═══")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    application = FastAPI(
        title="FakeBuster AI",
        description=(
            "Deepfake Forensics & Media Trust Platform — "
            "Detect AI-generated human faces in images and videos."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.DEBUG else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception Handlers ──
    application.add_exception_handler(FakeBusterError, fakebuster_error_handler)

    # ── Routes ──
    application.include_router(api_router)

    # ── Serve Frontend ──
    if FRONTEND_DIR.exists():
        @application.get("/", include_in_schema=False)
        async def serve_frontend():
            return FileResponse(str(FRONTEND_DIR / "index.html"))

        application.mount(
            "/",
            StaticFiles(directory=str(FRONTEND_DIR)),
            name="frontend",
        )
        logger.info(f"Serving frontend from {FRONTEND_DIR}")

    return application


# Create the app instance
app = create_app()
