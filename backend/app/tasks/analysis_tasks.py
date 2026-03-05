"""
FakeBuster AI — Background Analysis Tasks
Runs ML detection as a background task, updates the Analysis record on completion.
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.analysis import Analysis

# Add project root to path so ml package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from ml.detector_stub import detect  # noqa: E402

logger = logging.getLogger(__name__)


async def run_analysis(analysis_id: str) -> None:
    """
    Background task: run ML detection on the media file associated
    with the given analysis ID.

    Updates the Analysis record with results or error.
    """
    async with async_session_factory() as session:
        try:
            analysis = None
            # Convert string to UUID for proper comparison
            aid = UUID(analysis_id) if isinstance(analysis_id, str) else analysis_id
            # Fetch the analysis record
            result = await session.execute(
                select(Analysis).where(Analysis.id == aid)
            )
            analysis = result.scalar_one_or_none()

            if analysis is None:
                logger.error(f"Analysis {analysis_id} not found")
                return

            # Mark as processing
            analysis.status = "processing"
            await session.commit()

            logger.info(f"Starting detection for analysis {analysis_id}")

            # Run the detector (stub for now)
            detection = detect(analysis.source_ref)

            # Update with results
            analysis.status = "done"
            analysis.result_score = detection.result_score
            analysis.result_detail = detection.result_detail
            analysis.model_version = detection.model_version
            analysis.completed_at = datetime.now(timezone.utc)

            await session.commit()
            logger.info(
                f"Analysis {analysis_id} complete: score={detection.result_score}"
            )

        except Exception as e:
            logger.error(f"Analysis {analysis_id} failed: {e}")
            try:
                if analysis:
                    analysis.status = "failed"
                    analysis.error_message = str(e)
                    analysis.completed_at = datetime.now(timezone.utc)
                    await session.commit()
            except Exception:
                pass
