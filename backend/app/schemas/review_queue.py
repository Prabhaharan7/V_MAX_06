from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from app.schemas.safety_report import BarrierFailureResponse, ReportLSRTagResponse


class ReviewQueueItem(BaseModel):
    id: int = Field(..., description="Review Queue item ID")
    report_id: int = Field(..., description="Safety report ID")
    report_snippet: str = Field(..., description="Short snippet of narrative text")
    raw_text: str = Field(..., description="Full observation narrative text")
    current_ai_label: Optional[str] = Field(default=None, description="Current predicted label: sif_potential, non_sif, or pending")
    confidence: Optional[float] = Field(default=None, description="Confidence score of AI classification")
    reason: str = Field(..., description="Trigger reason why this observation was flagged for human triage")
    activity: Optional[str] = Field(default=None, description="Field activity")
    site_name: Optional[str] = Field(default=None, description="Site or rig name")
    site_region: Optional[str] = Field(default=None, description="Region")
    submitted_at: datetime = Field(..., description="Observation submission timestamp")
    primary_lsr: Optional[str] = Field(default=None, description="Primary Life-Saving Rule identified")
    resolved: bool = Field(default=False, description="Whether this triage case is resolved")
    corrected_label: Optional[str] = Field(default=None, description="HSE officer confirmed label")
    corrected_lsr: Optional[str] = Field(default=None, description="HSE officer confirmed Life-Saving Rule(s)")
    lsr_tags: List[ReportLSRTagResponse] = Field(default=[], description="Extracted LSR tags")
    barrier_failures: List[BarrierFailureResponse] = Field(default=[], description="Extracted barrier failures")

    class Config:
        from_attributes = True


class ReviewQueueResolveRequest(BaseModel):
    corrected_label: str = Field(..., description="Corrected/confirmed label: 'sif_potential' or 'non_sif'")
    corrected_lsr: Optional[Union[List[str], str]] = Field(default=None, description="Corrected Life-Saving Rule(s)")
    notes: Optional[str] = Field(default=None, description="HSE supervisor triage justification / rationale")


class ReviewQueueResolveResponse(BaseModel):
    success: bool = True
    queue_id: int
    report_id: int
    corrected_label: str
    corrected_lsr: Optional[str] = None
    resolved_at: datetime
    message: str


class AccuracyTrendPoint(BaseModel):
    date: str
    accuracy: float
    reviews_count: int
    corrections_count: int


class ModelFeedbackStatsResponse(BaseModel):
    current_accuracy: float = Field(..., description="Current calibrated model accuracy percentage (0.0 to 100.0)")
    baseline_accuracy: float = Field(default=78.5, description="Pre-active learning baseline accuracy")
    accuracy_delta: float = Field(default=12.9, description="Accuracy percentage increase from active learning")
    total_feedback_logged: int = Field(..., description="Total triage decisions logged")
    total_corrections: int = Field(..., description="Total model label overrides")
    total_agreements: int = Field(..., description="Total model label confirmations")
    active_learning_cycle: str = Field(default="Cycle 4 (Post-Retraining)", description="Active learning pipeline iteration")
    model_version: str = Field(default="v2.4-hybrid-transformer", description="Active classifier engine version")
    accuracy_trend: List[AccuracyTrendPoint] = Field(default=[], description="Historical accuracy trend points for sparkline")
