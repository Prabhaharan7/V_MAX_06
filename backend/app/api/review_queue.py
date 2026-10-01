from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user, oauth2_scheme
from app.models.entities import (
    ModelFeedbackLog,
    Report,
    ReportLSRTag,
    ReportStatus,
    ReviewQueue,
    SIFLabel,
    User,
)
from app.schemas.review_queue import (
    ReviewQueueItem,
    ReviewQueueResolveRequest,
    ReviewQueueResolveResponse,
)
from app.schemas.safety_report import BarrierFailureResponse, ReportLSRTagResponse

router = APIRouter()


# ==============================================================================
# Helper to convert ReviewQueue / Report to ReviewQueueItem
# ==============================================================================

def format_queue_item(rq: ReviewQueue) -> ReviewQueueItem:
    report = rq.report
    raw = report.raw_text if report else ""
    snippet = raw[:140] + ("..." if len(raw) > 140 else "")

    return ReviewQueueItem(
        id=rq.id,
        report_id=report.id if report else rq.report_id,
        report_snippet=snippet,
        raw_text=raw,
        current_ai_label=report.sif_label.value if report and report.sif_label else "sif_potential",
        confidence=report.sif_confidence if report else 0.52,
        reason=rq.reason or "Confidence in active learning triage threshold (40% - 60%)",
        activity=report.activity if report else "Field Operations",
        site_name=report.site.name if report and report.site else "Oil India Asset",
        site_region=report.site.region if report and report.site else "Assam Basin",
        submitted_at=report.submitted_at if report else datetime.now(timezone.utc),
        primary_lsr=report.primary_lsr if report else None,
        resolved=rq.resolved,
        corrected_label=rq.corrected_label,
        corrected_lsr=rq.corrected_lsr,
        lsr_tags=[
            ReportLSRTagResponse.model_validate(tag)
            for tag in (report.lsr_tags if report else [])
        ],
        barrier_failures=[
            BarrierFailureResponse.model_validate(bf)
            for bf in (report.barrier_failures if report else [])
        ],
    )


# ==============================================================================
# 1. GET /api/review-queue — Human-in-the-Loop Active Learning Triage Queue
# ==============================================================================

@router.get(
    "/",
    response_model=List[ReviewQueueItem],
    summary="List Active Learning Review Queue Items",
)
async def get_review_queue(
    resolved: Optional[bool] = Query(False, description="Filter by resolution state (default unresolved)"),
    limit: int = Query(50, ge=1, le=100, description="Max items to retrieve"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns safety observations flagged for human verification:
    - Ambiguous or borderline confidence predictions (0.40 - 0.60)
    - Conflicting NLP signals between rule triggers and embedding similarity
    - Unseen domain vocabulary or high-consequence severity amplifiers
    """
    stmt = (
        select(ReviewQueue)
        .options(
            selectinload(ReviewQueue.report).selectinload(Report.site),
            selectinload(ReviewQueue.report).selectinload(Report.lsr_tags),
            selectinload(ReviewQueue.report).selectinload(Report.barrier_failures),
        )
        .where(ReviewQueue.resolved == resolved)
        .order_by(desc(ReviewQueue.id))
        .limit(limit)
    )
    result = await db.execute(stmt)
    queue_entries = result.scalars().all()

    # If no explicit ReviewQueue rows exist, populate from pending_review reports dynamically
    if not queue_entries and not resolved:
        rep_stmt = (
            select(Report)
            .options(
                selectinload(Report.site),
                selectinload(Report.lsr_tags),
                selectinload(Report.barrier_failures),
            )
            .where(Report.status == ReportStatus.pending_review)
            .order_by(desc(Report.submitted_at))
            .limit(limit)
        )
        reports = (await db.execute(rep_stmt)).scalars().all()
        items: List[ReviewQueueItem] = []
        for idx, r in enumerate(reports, start=1):
            raw = r.raw_text or ""
            items.append(
                ReviewQueueItem(
                    id=idx,
                    report_id=r.id,
                    report_snippet=raw[:140] + ("..." if len(raw) > 140 else ""),
                    raw_text=raw,
                    current_ai_label=r.sif_label.value if r.sif_label else "sif_potential",
                    confidence=r.sif_confidence or 0.54,
                    reason="Borderline classifier confidence requires HSE expert calibration",
                    activity=r.activity or "Operational Activity",
                    site_name=r.site.name if r.site else "Asset",
                    site_region=r.site.region if r.site else "Region",
                    submitted_at=r.submitted_at,
                    primary_lsr=r.primary_lsr,
                    resolved=False,
                    corrected_label=None,
                    corrected_lsr=None,
                    lsr_tags=[ReportLSRTagResponse.model_validate(t) for t in (r.lsr_tags or [])],
                    barrier_failures=[BarrierFailureResponse.model_validate(b) for b in (r.barrier_failures or [])],
                )
            )
        return items

    return [format_queue_item(rq) for rq in queue_entries]


# ==============================================================================
# 2. POST /api/review-queue/{id}/resolve — Submit HSE Officer Triage Decision
# ==============================================================================

@router.post(
    "/{id}/resolve",
    response_model=ReviewQueueResolveResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve Triage Item with Corrected Label & LSR",
)
async def resolve_review_queue_item(
    id: int,
    payload: ReviewQueueResolveRequest,
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
):
    """
    Submits HSE officer human feedback:
    1. Updates the ReviewQueue entry to resolved
    2. Updates the Report record with confirmed SIF label, reviewed status, and corrected LSR
    3. Persists human correction into ModelFeedbackLog for active learning retraining
    """
    # 1. Resolve ReviewQueue entry (or search by report_id fallback)
    rq_stmt = (
        select(ReviewQueue)
        .options(selectinload(ReviewQueue.report))
        .where(ReviewQueue.id == id)
    )
    rq = (await db.execute(rq_stmt)).scalar_one_or_none()

    report_obj: Optional[Report] = None

    if rq:
        report_obj = rq.report
    else:
        # Fallback: treat id as report_id
        rep_stmt = (
            select(Report)
            .options(selectinload(Report.lsr_tags))
            .where(Report.id == id)
        )
        report_obj = (await db.execute(rep_stmt)).scalar_one_or_none()
        if not report_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review queue entry or Report #{id} not found",
            )

    # 2. Resolve submitter user
    user_id = 1
    if token:
        try:
            current_user = await get_current_user(token=token, db=db)
            user_id = current_user.id
        except Exception:
            pass

    # Normalize corrected LSR string
    lsr_str: Optional[str] = None
    if payload.corrected_lsr:
        if isinstance(payload.corrected_lsr, list):
            lsr_str = ", ".join(payload.corrected_lsr)
        else:
            lsr_str = str(payload.corrected_lsr)

    # Normalize corrected label
    label_val = payload.corrected_label.lower().strip()
    new_sif = SIFLabel.sif_potential if "sif" in label_val and "non" not in label_val else SIFLabel.non_sif

    # 3. Update Report
    orig_label = report_obj.sif_label.value if report_obj.sif_label else "unlabeled"
    report_obj.sif_label = new_sif
    report_obj.status = ReportStatus.reviewed
    if lsr_str:
        report_obj.primary_lsr = lsr_str.split(",")[0].strip()

    # 4. Update ReviewQueue record
    if rq:
        rq.resolved = True
        rq.corrected_label = new_sif.value
        rq.corrected_lsr = lsr_str
    else:
        # Create completed queue entry for audit trail
        rq = ReviewQueue(
            report_id=report_obj.id,
            reason=payload.notes or "HSE manual triage resolution",
            assigned_to=user_id,
            resolved=True,
            corrected_label=new_sif.value,
            corrected_lsr=lsr_str,
        )
        db.add(rq)

    # 5. Log ModelFeedbackLog for active learning calibration
    feedback_log = ModelFeedbackLog(
        report_id=report_obj.id,
        original_label=orig_label,
        corrected_label=new_sif.value,
        corrected_by=user_id,
    )
    db.add(feedback_log)

    await db.commit()
    await db.refresh(rq)

    return ReviewQueueResolveResponse(
        success=True,
        queue_id=rq.id,
        report_id=report_obj.id,
        corrected_label=new_sif.value,
        corrected_lsr=lsr_str,
        resolved_at=datetime.now(timezone.utc),
        message=f"Triage decision saved. Report #{report_obj.id} calibrated as {new_sif.value.upper()}.",
    )
