from datetime import datetime, date
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.models.entities import ReportType, SIFLabel, ReportStatus, BarrierSeverity


# ==============================================================================
# Request Schemas
# ==============================================================================

class ReportCreateRequest(BaseModel):
    report_type: ReportType = Field(default=ReportType.near_miss, description="Report type: UA, UC, near_miss, incident")
    raw_text: str = Field(..., min_length=5, description="Full safety observation narrative or incident report text")
    site_id: int = Field(..., description="ID of the oilfield site/asset")
    activity: str = Field(..., min_length=2, max_length=255, description="Activity: Drilling, Workover, Lifting, Tank Cleaning, etc.")
    language: str = Field(default="en", max_length=10, description="Source language (e.g., en, as, hi)")
    submitted_at: Optional[datetime] = Field(default=None, description="Timestamp of observation")
    submitted_by: Optional[int] = Field(default=None, description="User ID of submitter (auto-populated if authenticated)")


# Legacy schema aliases for backward compatibility
class SafetyReportBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str = Field(...)
    location: str = Field(default="Oil Field Facility")
    report_type: str = Field(default="Near Miss")
    reported_by: Optional[str] = Field(default="Field Safety Engineer")


class SafetyReportCreate(SafetyReportBase):
    pass


# ==============================================================================
# Response Schemas
# ==============================================================================

class ReportLSRTagResponse(BaseModel):
    id: int
    lsr_rule: str
    confidence: float

    class Config:
        from_attributes = True


class BarrierFailureResponse(BaseModel):
    id: int
    barrier_type: str
    evidence_phrase: str
    severity: BarrierSeverity

    class Config:
        from_attributes = True


class HistoricalCaseMatch(BaseModel):
    id: int
    title: str
    summary: str
    incident_year: int
    operation_type: str
    lsr_category: str
    lessons_learned: str
    similarity_score: float

    class Config:
        from_attributes = True


class ReportDetailResponse(BaseModel):
    id: int
    report_type: ReportType
    raw_text: str
    translated_text: Optional[str] = None
    site_id: int
    site_name: Optional[str] = None
    site_region: Optional[str] = None
    activity: str
    submitted_at: datetime
    language: str
    sif_label: Optional[SIFLabel] = None
    sif_confidence: Optional[float] = None
    primary_lsr: Optional[str] = None
    status: ReportStatus
    submitted_by: int
    submitter_name: Optional[str] = None
    lsr_tags: List[ReportLSRTagResponse] = []
    barrier_failures: List[BarrierFailureResponse] = []
    similar_historical_cases: List[HistoricalCaseMatch] = []
    raw_metadata: Optional[Dict[str, Any]] = None
    upload_batch_id: Optional[str] = None
    upload_batch_label: Optional[str] = None
    ground_truth_sif_label: Optional[str] = None
    ground_truth_lsr: Optional[str] = None
    ground_truth_barrier_status: Optional[str] = None
    ground_truth_split: Optional[str] = None

    class Config:
        from_attributes = True


class PaginatedReportsResponse(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int
    items: List[ReportDetailResponse]


# ==============================================================================
# Bulk Upload Schemas
# ==============================================================================

class BulkUploadRowError(BaseModel):
    row: int
    reason: str
    data: Dict[str, Any] = {}


class BulkUploadErrorGroup(BaseModel):
    reason: str
    count: int
    examples: List[Dict[str, Any]] = []


class BulkUploadSummaryResponse(BaseModel):
    total_rows: int
    accepted_count: int
    rejected_count: int
    accepted_report_ids: List[int]
    upload_batch_id: Optional[str] = None
    upload_batch_label: Optional[str] = None
    has_ground_truth: bool = False
    ground_truth_count: int = 0
    accuracy_report_url: Optional[str] = None
    download_csv_url: Optional[str] = None
    report_type_counts: Dict[str, int] = {}
    sif_label_counts: Dict[str, int] = {}
    ground_truth_sif_counts: Dict[str, int] = {}
    rejection_breakdown: List[BulkUploadErrorGroup] = []
    errors: List[BulkUploadRowError] = []


class TargetFieldDefinition(BaseModel):
    key: str
    label: str
    required: bool
    description: str


class ColumnMappingSuggestion(BaseModel):
    detected_column: str
    suggested_target: Optional[str] = None
    confidence: str = "unmapped"  # "high", "medium", "saved_template", "unmapped"
    sample_values: List[Any] = []


class BulkPreviewResponse(BaseModel):
    filename: str
    fingerprint: str
    total_preview_rows: int
    detected_columns: List[str]
    suggested_mappings: Dict[str, Optional[str]]  # detected_column -> target_field
    target_to_column: Dict[str, Optional[str]]  # target_field -> detected_column
    mapping_confidence: Dict[str, str]  # detected_column -> confidence level
    all_required_matched: bool
    matched_template_name: Optional[str] = None
    sample_rows: List[Dict[str, Any]]
    available_target_fields: List[TargetFieldDefinition]


class ConfirmColumnMappingRequest(BaseModel):
    mapping: Dict[str, str]  # target_field -> detected_column or detected_column -> target_field
    source_name: Optional[str] = None
    save_as_template: bool = True



# ==============================================================================
# SIF Analysis & Stats
# ==============================================================================

class SIFAnalysisResult(BaseModel):
    is_sif_precursor: bool
    sif_confidence: float = Field(..., ge=0.0, le=1.0)
    precursor_category: Optional[str] = None
    risk_level: str
    ai_analysis_summary: str
    key_risk_factors: List[str] = []


class SafetyReportResponse(BaseModel):
    id: int
    report_type: ReportType
    raw_text: str
    site_id: int
    activity: str
    submitted_at: datetime
    sif_label: Optional[SIFLabel] = None
    sif_confidence: Optional[float] = None
    status: ReportStatus

    class Config:
        from_attributes = True


class SafetyReportStats(BaseModel):
    total_reports: int
    sif_precursors_detected: int
    high_critical_risk_count: int
    sif_percentage: float


# ==============================================================================
# Explainable AI Highlight Spans Schema
# ==============================================================================

class ExplanationSpan(BaseModel):
    start: int = Field(..., description="0-indexed start character offset in raw text")
    end: int = Field(..., description="0-indexed end character offset in raw text")
    type: str = Field(..., description="Span type: sif_precursor, lsr_tag, or barrier_failure")
    label: str = Field(..., description="Identified category, life-saving rule, or barrier type")
    confidence: float = Field(..., description="Confidence score associated with this matched signal")
    matched_text: Optional[str] = Field(default=None, description="Exact matched substring from raw text")

    class Config:
        from_attributes = True


class ReportExplanationResponse(BaseModel):
    id: int = Field(..., description="Safety Report ID")
    text: str = Field(..., description="Full raw report text")
    spans: List[ExplanationSpan] = Field(default=[], description="List of character-offset explanation spans")

    class Config:
        from_attributes = True


# ==============================================================================
# Similar Incidents & Vector Nearest-Neighbor Schemas
# ==============================================================================

class SimilarIncidentItem(BaseModel):
    id: int = Field(..., description="Record ID in source table")
    source_type: str = Field(..., description="'case_library' for historical fatality or 'past_report' for observation")
    title: str = Field(..., description="Title or summary heading")
    summary: str = Field(..., description="Description or narrative summary")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Cosine similarity score (0.0 to 1.0)")
    operation_type: Optional[str] = Field(default=None, description="Drilling, Workover, Production, etc.")
    lsr_category: Optional[str] = Field(default=None, description="Primary Life-Saving Rule category")
    incident_year: Optional[int] = Field(default=None, description="Year of occurrence (for historical fatalities)")
    lessons_learned: Optional[str] = Field(default=None, description="Lessons learned and corrective recommendations")
    site_name: Optional[str] = Field(default=None, description="Operational site or rig name")
    is_fatality_case: bool = Field(default=False, description="True if this is a historical fatality case from case_library")
    sif_label: Optional[str] = Field(default=None, description="SIF classification label for past reports")

    class Config:
        from_attributes = True


class SimilarIncidentsResponse(BaseModel):
    report_id: int = Field(..., description="Target Report ID")
    report_text: str = Field(..., description="Report narrative text")
    high_similarity_to_past_fatality: bool = Field(
        default=False,
        description="True if any historical fatality case has cosine similarity > 0.75"
    )
    max_fatality_similarity: float = Field(
        default=0.0,
        description="Highest cosine similarity score among historical fatality cases"
    )
    top_similar_cases: List[SimilarIncidentItem] = Field(
        default=[],
        description="Top 5 most similar past incidents/cases merged across all sources"
    )
    historical_fatality_cases: List[SimilarIncidentItem] = Field(
        default=[],
        description="Top matching historical fatality cases from case_library"
    )
    similar_past_reports: List[SimilarIncidentItem] = Field(
        default=[],
        description="Top matching observations from other reports"
    )

    class Config:
        from_attributes = True


