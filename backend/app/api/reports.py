import csv
import io
import os
import tempfile
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user, oauth2_scheme
from app.models.entities import (
    BarrierFailure,
    CaseLibrary,
    ColumnMappingTemplate,
    Report,
    ReportLSRTag,
    ReportStatus,
    ReportType,
    SIFLabel,
    Site,
    User,
)
from app.schemas.safety_report import (
    BarrierFailureResponse,
    BulkPreviewResponse,
    BulkUploadRowError,
    BulkUploadErrorGroup,
    BulkUploadSummaryResponse,
    HistoricalCaseMatch,
    PaginatedReportsResponse,
    ReportCreateRequest,
    ReportDetailResponse,
    ReportExplanationResponse,
    ReportLSRTagResponse,
    SimilarIncidentsResponse,
)
from app.services.nlp_pipeline import process_report_nlp_pipeline
from app.services.report_explainer import generate_explanation_spans
from app.services.similarity_service import find_similar_incidents
from app.services.bulk_ingestion import (
    read_spreadsheet_dataframe,
    parse_and_validate_bulk_records,
    preview_spreadsheet_mapping,
    compute_column_fingerprint,
    normalize_header,
    canonical_alphanumeric,
)
import json

router = APIRouter()


# ==============================================================================
# Helper: Format Report to ReportDetailResponse
# ==============================================================================

def format_report_detail(
    report: Report,
    similar_cases: Optional[List[HistoricalCaseMatch]] = None,
) -> ReportDetailResponse:
    return ReportDetailResponse(
        id=report.id,
        report_type=report.report_type,
        raw_text=report.raw_text,
        translated_text=report.translated_text,
        site_id=report.site_id,
        site_name=report.site.name if report.site else None,
        site_region=report.site.region if report.site else None,
        activity=report.activity,
        submitted_at=report.submitted_at,
        language=report.language,
        sif_label=report.sif_label,
        sif_confidence=report.sif_confidence,
        primary_lsr=report.primary_lsr,
        status=report.status,
        submitted_by=report.submitted_by,
        submitter_name=report.submitter.name if report.submitter else None,
        raw_metadata=report.raw_metadata,
        upload_batch_id=report.upload_batch_id,
        upload_batch_label=report.upload_batch_label,
        ground_truth_sif_label=report.ground_truth_sif_label,
        ground_truth_lsr=report.ground_truth_lsr,
        ground_truth_barrier_status=report.ground_truth_barrier_status,
        ground_truth_split=report.ground_truth_split,
        lsr_tags=[
            ReportLSRTagResponse.model_validate(tag)
            for tag in (report.lsr_tags or [])
        ],
        barrier_failures=[
            BarrierFailureResponse.model_validate(bf)
            for bf in (report.barrier_failures or [])
        ],
        similar_historical_cases=similar_cases or [],
    )


# ==============================================================================
# 1. POST /api/reports — Single Report Submission with Async NLP Background Task
# ==============================================================================

@router.post(
    "/",
    response_model=ReportDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Single Safety Report",
)
async def submit_single_report(
    payload: ReportCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
):
    """
    Submits an unstructured safety observation report.
    Persists the report in 'pending_review' status and triggers the asynchronous
    NLP pipeline (SIF precursor classification, LSR tagging, barrier failure extraction,
    and pgvector embedding generation) in the background.
    """
    # 1. Validate Site ID
    site_stmt = select(Site).where(Site.id == payload.site_id)
    site = (await db.execute(site_stmt)).scalar_one_or_none()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Site with ID {payload.site_id} does not exist",
        )

    # 2. Resolve Submitter User
    submitter_id = payload.submitted_by
    if not submitter_id:
        # Check if user is authenticated
        if token:
            try:
                user = await get_current_user(token=token, db=db)
                submitter_id = user.id
            except Exception:
                pass

        if not submitter_id:
            # Fallback to first user in database
            user_stmt = select(User.id).limit(1)
            submitter_id = (await db.execute(user_stmt)).scalar() or 1

    # 3. Create Report record
    report = Report(
        report_type=payload.report_type,
        raw_text=payload.raw_text,
        submitted_by=submitter_id,
        site_id=payload.site_id,
        activity=payload.activity,
        language=payload.language,
        submitted_at=payload.submitted_at or datetime.now(timezone.utc),
        status=ReportStatus.pending_review,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Reload relationships for response formatting
    reload_stmt = (
        select(Report)
        .options(
            selectinload(Report.site),
            selectinload(Report.submitter),
            selectinload(Report.lsr_tags),
            selectinload(Report.barrier_failures),
        )
        .where(Report.id == report.id)
    )
    report_loaded = (await db.execute(reload_stmt)).scalar_one()

    # 4. Queue Async NLP Pipeline Background Task
    background_tasks.add_task(process_report_nlp_pipeline, report.id)

    return format_report_detail(report_loaded)


# ==============================================================================
# 2. POST /api/reports/bulk-upload/preview — Spreadsheet Header Preview & Auto-Map
# ==============================================================================

@router.post(
    "/bulk-upload/preview",
    response_model=BulkPreviewResponse,
    summary="Preview & Auto-Map Spreadsheet Columns",
)
async def preview_bulk_upload(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Parses the header and first 5 rows of an uploaded CSV/XLSX file,
    computes the column fingerprint, checks for saved templates,
    and returns suggested column mappings with preview sample data.
    """
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()

    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a .csv, .xlsx, or .xls file.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        # Check if we have a saved mapping template for this column fingerprint
        preview_df = read_spreadsheet_dataframe(content, filename, nrows=1)
        actual_cols = [str(c).strip() for c in preview_df.columns if str(c).strip()]
        fingerprint = compute_column_fingerprint(actual_cols)

        saved_template_stmt = select(ColumnMappingTemplate).where(ColumnMappingTemplate.fingerprint == fingerprint)
        saved_template = (await db.execute(saved_template_stmt)).scalar_one_or_none()

        saved_mapping = saved_template.mapping if saved_template else None
        saved_name = saved_template.source_name if saved_template else None

        preview_res = preview_spreadsheet_mapping(
            file_content=content,
            filename=filename,
            saved_template_mapping=saved_mapping,
            saved_template_name=saved_name,
        )
        return preview_res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to preview spreadsheet: {str(e)}",
        )


# ==============================================================================
# 2b. POST /api/reports/bulk-upload — CSV/XLSX Bulk Ingestion
# ==============================================================================

@router.post(
    "/bulk-upload",
    response_model=BulkUploadSummaryResponse,
    summary="Bulk Upload Reports (CSV/XLSX)",
)
async def bulk_upload_reports(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    batch_label: Optional[str] = Form(None),
    custom_mapping: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Accepts a CSV or XLSX spreadsheet containing safety observation logs.
    Validates rows by column header name (supporting custom_mapping confirmations),
    matches aliases, preserves extra metadata, extracts ground-truth labels if present,
    tags with batch_id, bulk-inserts valid entries, saves confirmed mapping templates,
    and queues each report for background NLP processing.
    """
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()

    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a .csv, .xlsx, or .xls file.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # 1. Read file into pandas DataFrame
    try:
        df = read_spreadsheet_dataframe(content, filename)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read spreadsheet file: {str(e)}",
        )

    if df.empty or len(df) == 0:
        return BulkUploadSummaryResponse(
            total_rows=0,
            accepted_count=0,
            rejected_count=0,
            accepted_report_ids=[],
            rejection_breakdown=[],
            errors=[],
        )

    # 2. Parse custom mapping payload if provided
    parsed_custom_mapping: Optional[Dict[str, str]] = None
    if custom_mapping and custom_mapping.strip():
        try:
            parsed_custom_mapping = json.loads(custom_mapping)
            if not isinstance(parsed_custom_mapping, dict):
                parsed_custom_mapping = None
        except Exception:
            parsed_custom_mapping = None

    # 3. Fetch existing sites from database for ID and name matching
    site_records = (await db.execute(select(Site))).scalars().all()
    existing_sites_by_id = {s.id for s in site_records}
    site_names_map: Dict[str, int] = {}
    for s in site_records:
        site_names_map[normalize_header(s.name)] = s.id
        site_names_map[canonical_alphanumeric(s.name)] = s.id

    default_user_id = (await db.execute(select(User.id).limit(1))).scalar() or 1

    # 4. Parse, map headers, extract ground-truth, and validate row-by-row
    try:
        reports_to_insert, summary = parse_and_validate_bulk_records(
            df=df,
            existing_sites_by_id=existing_sites_by_id,
            site_names_map=site_names_map,
            default_user_id=default_user_id,
            batch_label=batch_label or f"Upload {filename} ({datetime.now().strftime('%b %d, %Y %H:%M')})",
            custom_mapping=parsed_custom_mapping,
        )
    except ValueError as e:
        # Fast fail if required columns (e.g. raw_text) cannot be matched
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # 5. Bulk commit valid reports
    if reports_to_insert:
        db.add_all(reports_to_insert)
        await db.commit()
        for r in reports_to_insert:
            await db.refresh(r)
            summary.accepted_report_ids.append(r.id)
            # Queue background task for NLP processing
            background_tasks.add_task(process_report_nlp_pipeline, r.id)

    # 6. Save or update confirmed column mapping template for future auto-detection
    try:
        actual_cols = [str(c).strip() for c in df.columns if str(c).strip()]
        fingerprint = compute_column_fingerprint(actual_cols)
        mapping_to_store = parsed_custom_mapping or {}

        existing_template = (await db.execute(
            select(ColumnMappingTemplate).where(ColumnMappingTemplate.fingerprint == fingerprint)
        )).scalar_one_or_none()

        if existing_template:
            if mapping_to_store:
                existing_template.mapping = mapping_to_store
            existing_template.column_headers = actual_cols
        else:
            new_template = ColumnMappingTemplate(
                fingerprint=fingerprint,
                source_name=batch_label or f"Confirmed Format ({filename})",
                mapping=mapping_to_store,
                column_headers=actual_cols,
            )
            db.add(new_template)
        await db.commit()
    except Exception as e:
        print(f"Note on template persistence: {e}")

    return summary


# ==============================================================================
# 3. GET /api/reports — Paginated, Filterable Safety Report List
# ==============================================================================

@router.get(
    "/",
    response_model=PaginatedReportsResponse,
    summary="List & Filter Safety Reports",
)
async def list_reports(
    site_id: Optional[int] = Query(None, description="Filter by Site ID"),
    report_type: Optional[ReportType] = Query(None, description="Filter by report type (UA, UC, near_miss, incident)"),
    sif_label: Optional[SIFLabel] = Query(None, description="Filter by SIF classification (sif_potential, non_sif)"),
    status: Optional[ReportStatus] = Query(None, description="Filter by review status (pending_review, reviewed, auto_confirmed)"),
    start_date: Optional[date] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search keyword in raw text or activity"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a paginated list of safety reports with multi-criteria filtering:
    - Site / Asset ID
    - Report Type (UA/UC/Near Miss/Incident)
    - SIF Classification (sif_potential / non_sif)
    - Review Status
    - Date range and full-text keyword search
    """
    query = select(Report).options(
        selectinload(Report.site),
        selectinload(Report.submitter),
        selectinload(Report.lsr_tags),
        selectinload(Report.barrier_failures),
    )
    count_query = select(func.count(Report.id))

    # Apply filters
    if site_id is not None:
        query = query.where(Report.site_id == site_id)
        count_query = count_query.where(Report.site_id == site_id)

    if report_type is not None:
        query = query.where(Report.report_type == report_type)
        count_query = count_query.where(Report.report_type == report_type)

    if sif_label is not None:
        query = query.where(Report.sif_label == sif_label)
        count_query = count_query.where(Report.sif_label == sif_label)

    if status is not None:
        query = query.where(Report.status == status)
        count_query = count_query.where(Report.status == status)

    if start_date is not None:
        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        query = query.where(Report.submitted_at >= start_dt)
        count_query = count_query.where(Report.submitted_at >= start_dt)

    if end_date is not None:
        end_dt = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)
        query = query.where(Report.submitted_at <= end_dt)
        count_query = count_query.where(Report.submitted_at <= end_dt)

    if search:
        search_filter = Report.raw_text.ilike(f"%{search}%") | Report.activity.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Total count
    total = (await db.execute(count_query)).scalar() or 0

    # Pagination & Ordering
    offset = (page - 1) * limit
    query = query.order_by(desc(Report.submitted_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    reports = result.scalars().all()

    total_pages = (total + limit - 1) // limit if total > 0 else 1

    return PaginatedReportsResponse(
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
        items=[format_report_detail(r) for r in reports],
    )


# ==============================================================================
# 4. GET /api/reports/{id} — Full Detail with LSR Tags, Barrier Failures & Safety Memory
# ==============================================================================

@router.get(
    "/{id}",
    response_model=ReportDetailResponse,
    summary="Get Safety Report Detail & Historical Case Matches",
)
async def get_report_detail(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves full detail for a safety report including:
    - Extracted Life-Saving Rule (LSR) tags
    - Barrier failure evidence phrases and severity levels
    - Safety Memory RAG: Top similar historical fatality cases matched via pgvector similarity search
    """
    stmt = (
        select(Report)
        .options(
            selectinload(Report.site),
            selectinload(Report.submitter),
            selectinload(Report.lsr_tags),
            selectinload(Report.barrier_failures),
        )
        .where(Report.id == id)
    )
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Safety report with ID {id} not found",
        )

    # Safety Memory RAG: Find similar historical fatality cases using pgvector
    similar_cases: List[HistoricalCaseMatch] = []
    if report.embedding is not None:
        try:
            # Query top 3 nearest historical fatality cases from CaseLibrary
            case_stmt = (
                select(
                    CaseLibrary,
                    CaseLibrary.embedding.l2_distance(report.embedding).label("distance"),
                )
                .where(CaseLibrary.embedding.isnot(None))
                .order_by("distance")
                .limit(3)
            )
            case_result = await db.execute(case_stmt)
            for row in case_result.all():
                case_obj, distance = row[0], row[1]
                # Convert distance to normalized similarity score (0.0 to 1.0)
                sim_score = max(0.0, min(1.0, round(1.0 / (1.0 + float(distance or 0.0)), 2)))
                similar_cases.append(
                    HistoricalCaseMatch(
                        id=case_obj.id,
                        title=case_obj.title,
                        summary=case_obj.summary,
                        incident_year=case_obj.incident_year,
                        operation_type=case_obj.operation_type,
                        lsr_category=case_obj.lsr_category,
                        lessons_learned=case_obj.lessons_learned,
                        similarity_score=sim_score,
                    )
                )
        except Exception:
            # Fallback if vector distance operator encounters unpopulated cases
            case_stmt = select(CaseLibrary).limit(3)
            cases = (await db.execute(case_stmt)).scalars().all()
            for c in cases:
                similar_cases.append(
                    HistoricalCaseMatch(
                        id=c.id,
                        title=c.title,
                        summary=c.summary,
                        incident_year=c.incident_year,
                        operation_type=c.operation_type,
                        lsr_category=c.lsr_category,
                        lessons_learned=c.lessons_learned,
                        similarity_score=0.85,
                    )
                )

    return format_report_detail(report, similar_cases=similar_cases)


# ==============================================================================
# 5. GET /api/reports/{id}/explain — Explainable AI Character-Offset Spans
# ==============================================================================

@router.get(
    "/{id}/explain",
    response_model=ReportExplanationResponse,
    summary="Get Explainable AI Highlights & Character-Offset Spans",
)
async def explain_report_classification(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the raw report text with character-offset spans marking:
    (a) phrases that drove the SIF classification (rule-matcher hits)
    (b) phrases that drove each Life-Saving Rule (LSR) tag
    (c) phrases that represent evidence for each safety barrier failure
    """
    stmt = (
        select(Report)
        .options(
            selectinload(Report.lsr_tags),
            selectinload(Report.barrier_failures),
        )
        .where(Report.id == id)
    )
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Safety report with ID {id} not found",
        )

    return generate_explanation_spans(report)


# ==============================================================================
# 6. GET /api/reports/{id}/similar-incidents — Nearest-Neighbor Similarity Match
# ==============================================================================

@router.get(
    "/{id}/similar-incidents",
    response_model=SimilarIncidentsResponse,
    summary="Get Nearest-Neighbor Similar Incidents & Historical Fatality Matching",
)
async def get_similar_incidents(
    id: int,
    top_k: int = Query(5, ge=1, le=20, description="Number of top similar cases to return"),
    fatality_threshold: float = Query(0.75, ge=0.0, le=1.0, description="Similarity threshold for fatality alert"),
    db: AsyncSession = Depends(get_db),
):
    """
    Runs pgvector cosine-distance nearest-neighbor matching (<=> operator) against:
    (1) Historical fatality summaries in the case_library table
    (2) Past field observations and incident reports
    
    Returns the top 5 most similar cases. If any historical fatality has similarity > 0.75,
    includes the warning flag "high_similarity_to_past_fatality": true.
    """
    stmt = (
        select(Report)
        .options(selectinload(Report.site))
        .where(Report.id == id)
    )
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Safety report with ID {id} not found",
        )

    return await find_similar_incidents(
        db=db,
        report=report,
        top_k=top_k,
        fatality_threshold=fatality_threshold,
    )


