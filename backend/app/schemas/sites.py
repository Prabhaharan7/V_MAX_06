from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SiteBarrierBreakdown(BaseModel):
    barrier_type: str
    failure_count: int
    severity_weight: float = 1.0
    percentage: float = 0.0


class SiteSIIRankingItem(BaseModel):
    rank: int = Field(..., description="Leaderboard rank (1 is best safety performance)")
    site_id: int = Field(..., description="Operational site ID")
    site_name: str = Field(..., description="Asset or rig name")
    region: str = Field(..., description="Operational geographical sector")
    operation_type: str = Field(..., description="Drilling, Workover, Production, Pipeline, etc.")
    current_sii: float = Field(..., description="Current Safety Improvement Index score (0.0 - 100.0)")
    previous_sii: float = Field(..., description="Previous period Safety Improvement Index score")
    sii_delta: float = Field(..., description="Change in SII score (+ improving, - degrading)")
    sif_density: float = Field(..., description="Ratio of SIF potential reports to total observations")
    total_reports: int = Field(..., description="Total safety observation reports recorded")
    sif_reports_count: int = Field(..., description="Count of verified SIF precursor observations")
    top_barrier_failure: Optional[str] = Field(default=None, description="Primary compromised barrier")
    status_tier: str = Field(..., description="'High Performer', 'Stable', 'Attention Required', 'Critical Risk'")
    trend: str = Field(default="stable", description="'rising', 'stable', 'falling'")
    barrier_breakdown: List[SiteBarrierBreakdown] = Field(default=[], description="Top barrier failures for this site")


class SIITrendPoint(BaseModel):
    period: str = Field(..., description="Month label e.g., 'May 2026'")
    date: str = Field(..., description="ISO period date YYYY-MM-DD")
    sii_score: float = Field(..., description="Safety Improvement Index (0-100)")
    sif_density: float = Field(..., description="SIF precursor density (0.0-1.0)")
    barrier_recurrence_score: float = Field(..., description="Weighted barrier recurrence index")
    total_reports: int = Field(default=0, description="Reports submitted in period")
    sif_count: int = Field(default=0, description="SIF precursors identified in period")


class SiteSIITrendResponse(BaseModel):
    site_id: int
    site_name: str
    region: str
    operation_type: str
    current_sii: float
    trend: List[SIITrendPoint]


class WhatIfBarrierReduction(BaseModel):
    barrier_type: str
    reduction_percent: float = Field(..., ge=0.0, le=100.0, description="Percentage reduction (0 to 100)")


class WhatIfSimulationRequest(BaseModel):
    reductions: Dict[str, float] = Field(
        default={},
        description="Key-value mapping of barrier type to percentage reduction (0-100)"
    )


class BarrierImpactDetail(BaseModel):
    barrier_type: str
    original_failures: int
    reduced_failures: float
    sii_contribution: float


class WhatIfSimulationResponse(BaseModel):
    site_id: int
    site_name: str
    current_sii: float
    projected_sii: float
    sii_gain: float
    current_rank: int
    projected_rank: int
    barrier_impacts: List[BarrierImpactDetail]
    explanation: str
