from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.entities import PatternTrend
from app.schemas.patterns import (
    PatternMiningSummary,
    PrecursorPatternResponse,
    RankedSiteResponse,
)
from app.services.pattern_mining import (
    get_patterns,
    get_ranked_sites,
    run_pattern_mining,
)

router = APIRouter()


# ==============================================================================
# 1. GET /api/patterns — Ranked List of Aggregated Precursor Patterns
# ==============================================================================

@router.get(
    "/",
    response_model=List[PrecursorPatternResponse],
    summary="List Ranked Precursor Patterns",
)
async def list_patterns(
    site_id: Optional[int] = Query(None, description="Filter patterns by Site ID"),
    min_count: int = Query(1, ge=1, description="Minimum occurrence threshold"),
    trend: Optional[PatternTrend] = Query(None, description="Filter by trend (rising, stable, falling)"),
    limit: int = Query(50, ge=1, le=100, description="Max patterns to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns ranked spatio-temporal precursor patterns identified across oilfield assets.
    Ordered by occurrence frequency and recency over rolling operational windows.
    """
    patterns = await get_patterns(
        db=db,
        site_id=site_id,
        min_count=min_count,
        trend=trend,
        limit=limit,
    )
    return [PrecursorPatternResponse.model_validate(p) for p in patterns]


# ==============================================================================
# 2. GET /api/patterns/ranked-sites — Executive Site Ranking by SIF Density
# ==============================================================================

@router.get(
    "/ranked-sites",
    response_model=List[RankedSiteResponse],
    summary="Rank Sites by SIF-Precursor Density & Barrier Severity",
)
async def list_ranked_sites(
    db: AsyncSession = Depends(get_db),
):
    """
    Main Executive Dashboard Ranking:
    Ranks Oil & Gas installations and rigs by total SIF-precursor density
    (ratio of SIF-potential reports / total observations, weighted by barrier failure severity).
    """
    return await get_ranked_sites(db=db)


# ==============================================================================
# 3. POST /api/patterns/refresh — On-Demand Aggregation Trigger
# ==============================================================================

@router.post(
    "/refresh",
    response_model=PatternMiningSummary,
    status_code=status.HTTP_200_OK,
    summary="Trigger On-Demand Pattern Mining Aggregation",
)
async def refresh_pattern_mining(
    db: AsyncSession = Depends(get_db),
):
    """
    Runs the rolling 90-day window aggregation against recent safety logs,
    computes rising/stable/falling trends, and updates the precursor patterns database.
    """
    mined_patterns = await run_pattern_mining(db=db)
    return PatternMiningSummary(
        status="success",
        patterns_mined=len(mined_patterns),
        timestamp=datetime.now(timezone.utc),
        top_patterns=[
            PrecursorPatternResponse.model_validate(p)
            for p in mined_patterns[:10]
        ],
    )
