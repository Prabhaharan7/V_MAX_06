"""
================================================================================
SIF Sentinel AI - Dataset Benchmarks & Model Accuracy API
SIH 2026 Problem Statement PS 26165 (Oil India Limited)
================================================================================
Endpoints for live evaluation of model predictions against ground-truth labels:
- GET /api/datasets/batches: List historical upload batches and evaluation KPIs
- GET /api/datasets/{upload_batch_id}/accuracy-report: Full accuracy benchmark for a batch
- GET /api/datasets/accuracy-report: Global dataset accuracy report across all labeled reports
================================================================================
"""

import csv
import io
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.entities import Report, SIFLabel
from app.schemas.dataset import AccuracyReportResponse, BatchListResponse
from app.services.evaluation_service import evaluate_batch_accuracy, list_all_batches

router = APIRouter()


@router.get(
    "/batches",
    response_model=BatchListResponse,
    summary="List Upload Batches & Benchmark Summaries",
    description="Lists all historical spreadsheet upload batches with total records, labeled counts, and accuracy.",
)
async def get_all_batches(
    db: AsyncSession = Depends(get_db),
):
    return await list_all_batches(db)


@router.get(
    "/accuracy-report",
    response_model=AccuracyReportResponse,
    summary="Global Model Accuracy Benchmark",
    description="Computes system-wide classification accuracy, precision, recall, F1, and LSR accuracy across all labeled reports.",
)
async def get_global_accuracy_report(
    db: AsyncSession = Depends(get_db),
):
    return await evaluate_batch_accuracy(db, batch_id=None)


@router.get(
    "/{upload_batch_id}/accuracy-report",
    response_model=AccuracyReportResponse,
    summary="Batch Model Accuracy & Evaluation Benchmark",
    description="Compares model predictions against ground-truth labels for a specific upload batch, breaking down by Train/Test/Val splits, SIF metrics, confusion matrix, and per-rule LSR accuracy.",
)
async def get_batch_accuracy_report(
    upload_batch_id: str,
    db: AsyncSession = Depends(get_db),
):
    report = await evaluate_batch_accuracy(db, batch_id=upload_batch_id)
    if report.total_reports == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload batch '{upload_batch_id}' not found.",
        )
    return report


@router.get(
    "/{upload_batch_id}/export-csv",
    summary="Download Processed Dataset with Predictions and Ground Truth (CSV)",
    description="Exports all processed reports for an upload batch including original columns, model predictions, and ground-truth comparisons as a downloadable CSV.",
)
async def export_batch_csv(
    upload_batch_id: str,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Report)
        .options(selectinload(Report.site))
        .where(Report.upload_batch_id == upload_batch_id)
        .order_by(Report.id.asc())
    )
    result = await db.execute(query)
    reports = result.scalars().all()

    if not reports:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload batch '{upload_batch_id}' not found.",
        )

    # Collect all unique extra metadata keys across all reports in batch
    meta_keys = set()
    for r in reports:
        if r.raw_metadata and isinstance(r.raw_metadata, dict):
            meta_keys.update(r.raw_metadata.keys())
    sorted_meta_keys = sorted(list(meta_keys))

    output = io.StringIO()
    writer = csv.writer(output)

    # Header columns
    headers = [
        "Report_ID",
        "Date",
        "Site_ID",
        "Site_Name",
        "Report_Type",
        "Activity",
        "Raw_Text",
        "Model_Predicted_SIF",
        "Model_SIF_Confidence",
        "Model_Predicted_LSR",
        "Model_Status",
        "Ground_Truth_SIF",
        "Ground_Truth_LSR",
        "Ground_Truth_Barrier_Status",
        "Ground_Truth_Split",
        "SIF_Prediction_Match",
    ] + sorted_meta_keys
    writer.writerow(headers)

    for r in reports:
        # Check prediction match
        match_str = "N/A"
        if r.ground_truth_sif_label and r.sif_label:
            gt_is_sif = r.ground_truth_sif_label in ["sif_potential", "sif", "1", "true"]
            pred_is_sif = r.sif_label == SIFLabel.sif_potential or (hasattr(r.sif_label, "value") and r.sif_label.value == "sif_potential")
            match_str = "MATCH" if (gt_is_sif == pred_is_sif) else "MISMATCH"

        row = [
            r.id,
            r.submitted_at.isoformat() if r.submitted_at else "",
            r.site_id,
            r.site.name if r.site else "",
            r.report_type.value if hasattr(r.report_type, "value") else str(r.report_type),
            r.activity,
            r.raw_text,
            r.sif_label.value if r.sif_label else "pending",
            f"{r.sif_confidence:.4f}" if r.sif_confidence is not None else "",
            r.primary_lsr or "",
            r.status.value if hasattr(r.status, "value") else str(r.status),
            r.ground_truth_sif_label or "",
            r.ground_truth_lsr or "",
            r.ground_truth_barrier_status or "",
            r.ground_truth_split or "",
            match_str,
        ]

        # Append extra metadata values
        r_meta = r.raw_metadata if (r.raw_metadata and isinstance(r.raw_metadata, dict)) else {}
        for k in sorted_meta_keys:
            row.append(r_meta.get(k, ""))

        writer.writerow(row)

    csv_content = output.getvalue()
    filename = f"processed_dataset_{upload_batch_id}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
