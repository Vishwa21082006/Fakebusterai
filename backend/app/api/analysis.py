"""
FakeBuster AI — Analysis Endpoints
View analysis results, list user analyses, enterprise detect API.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.analysis import Analysis
from app.schemas.analysis import AnalysisResponse, AnalysisListResponse
from app.core.security import get_current_user

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific analysis by ID. Users can only view their own analyses."""
    try:
        aid = UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID format")

    result = await db.execute(
        select(Analysis).where(
            Analysis.id == aid,
            Analysis.user_id == current_user.id,
        )
    )
    analysis = result.scalar_one_or_none()

    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found",
        )

    return _to_response(analysis)


@router.get("", response_model=AnalysisListResponse)
async def list_analyses(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's analyses with pagination."""
    query = select(Analysis).where(Analysis.user_id == current_user.id)
    count_query = select(func.count()).select_from(Analysis).where(
        Analysis.user_id == current_user.id
    )

    if status_filter:
        query = query.where(Analysis.status == status_filter)
        count_query = count_query.where(Analysis.status == status_filter)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    query = (
        query
        .order_by(Analysis.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    analyses = result.scalars().all()

    return AnalysisListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[_to_response(a) for a in analyses],
    )


def _to_response(analysis: Analysis) -> AnalysisResponse:
    """Convert an Analysis ORM object to an AnalysisResponse."""
    return AnalysisResponse(
        id=str(analysis.id),
        source_type=analysis.source_type,
        media_type=analysis.media_type,
        status=analysis.status,
        result_score=analysis.result_score,
        result_detail=analysis.result_detail,
        model_version=analysis.model_version,
        file_hash=analysis.file_hash,
        error_message=analysis.error_message,
        created_at=analysis.created_at.isoformat() if analysis.created_at else "",
        completed_at=analysis.completed_at.isoformat() if analysis.completed_at else None,
    )
