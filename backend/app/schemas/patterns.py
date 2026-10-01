from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.models.entities import PatternTrend


class PrecursorPatternResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activity: str
    location: str
    barrier_type: str
    occurrence_count: int
    last_seen: datetime
    trend: PatternTrend


class RankedSiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int
    site_id: int
    site_name: str
    region: str
    operation_type: str
    location_lat: float
    location_lng: float
    total_reports: int
    sif_reports_count: int
    sif_density: float
    weighted_sif_density: float
    top_barrier_failure: Optional[str] = None
    primary_trend: PatternTrend = PatternTrend.stable


class PatternMiningSummary(BaseModel):
    status: str
    patterns_mined: int
    timestamp: datetime
    top_patterns: List[PrecursorPatternResponse]
