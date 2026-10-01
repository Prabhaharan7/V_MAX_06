"""
================================================================================
SIF Sentinel AI - Unit Tests for Dataset Accuracy & Model Benchmark
Smart India Hackathon 2026 (Problem Statement PS 26165 - Oil India Limited)
================================================================================
"""

import io
import pytest
import pandas as pd
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import AsyncSessionLocal
from app.models.entities import Report, ReportType, ReportStatus, SIFLabel
from app.services.bulk_ingestion import parse_and_validate_bulk_records
from app.services.evaluation_service import (
    compute_sif_metrics,
    match_lsr_rule,
    evaluate_batch_accuracy,
    list_all_batches,
)


def test_1_compute_sif_metrics_calculations():
    """Verify standard classification metrics (Accuracy, Precision, Recall, F1, Specificity)."""
    metrics = compute_sif_metrics(tp=90, fp=10, fn=10, tn=90)
    assert metrics.total_evaluated == 200
    assert metrics.accuracy == 0.90
    assert metrics.precision == 0.90
    assert metrics.recall == 0.90
    assert metrics.f1_score == 0.90
    assert metrics.specificity == 0.90
    assert metrics.sif_count == 100
    assert metrics.non_sif_count == 100


def test_2_match_lsr_rule_fuzzy_matching():
    """Verify LSR rule matching against primary rule or secondary tags."""
    assert match_lsr_rule("Bypassing Safety Controls", "Bypassing Safety Controls", [])
    assert match_lsr_rule("bypassing_safety_controls", "Bypassing Safety Controls", [])
    assert match_lsr_rule("Energy Isolation", "Energy Isolation", [])
    assert match_lsr_rule("Work Authorisation", "Work Authorization", [])
    assert match_lsr_rule("Line of Fire", None, ["Line of Fire", "Energy Isolation"])
    assert not match_lsr_rule("Confined Space", "Working at Height", ["Hot Work"])


def test_3_ground_truth_parsing_and_batch_tagging():
    """
    Verify parser captures SIF_Label, Life_Saving_Rule, Barrier_Status, and Split
    into dedicated Report model columns and assigns batch_id and batch_label.
    """
    csv_data = """Date,Site,Report_Type,Activity,raw_text,SIF_Label,Life_Saving_Rule,Barrier_Status,Split
2026-03-01,OIL Duliajan HQ,near_miss,Rig Maintenance,High pressure manifold valve leaking toxic sour gas near crew cabins.,sif_potential,Toxic Gas,Failed,test
2026-03-02,OIL Duliajan HQ,near_miss,Housekeeping,Slight tripping hazard on gravel pathway outside office building.,non_sif,Housekeeping,Effective,train
2026-03-03,OIL Duliajan HQ,UA,Lifting,Crane rigger did not inspect tag lines prior to lift over live pipeline.,sif_potential,Line of Fire,Degraded,test
"""
    df = pd.read_csv(io.StringIO(csv_data))
    reports, summary = parse_and_validate_bulk_records(
        df=df,
        existing_sites_by_id={1},
        site_names_map={"oil_duliajan_hq": 1},
        batch_id="test_batch_001",
        batch_label="Test Benchmark Batch v1",
    )

    assert summary.total_rows == 3
    assert summary.accepted_count == 3
    assert summary.has_ground_truth is True
    assert summary.ground_truth_count == 3
    assert summary.upload_batch_id == "test_batch_001"
    assert summary.upload_batch_label == "Test Benchmark Batch v1"
    assert summary.accuracy_report_url == "/api/datasets/test_batch_001/accuracy-report"

    # Report 1
    r1 = reports[0]
    assert r1.upload_batch_id == "test_batch_001"
    assert r1.ground_truth_sif_label == "sif_potential"
    assert r1.ground_truth_lsr == "Toxic Gas"
    assert r1.ground_truth_barrier_status == "Failed"
    assert r1.ground_truth_split == "test"

    # Report 2
    r2 = reports[1]
    assert r2.ground_truth_sif_label == "non_sif"
    assert r2.ground_truth_split == "train"


@pytest.mark.anyio
async def test_4_evaluate_batch_accuracy():
    """
    Verify accuracy report calculates confusion matrix, SIF metrics,
    and split breakdowns (Train vs Test) from database records.
    """
    import uuid
    batch_id = f"eval_batch_{uuid.uuid4().hex[:8]}"

    async with AsyncSessionLocal() as session:
        # Insert test reports with model predictions and ground-truth
        r1 = Report(
            report_type=ReportType.near_miss,
            raw_text="Heavy casing pipe swung near drillers when secondary winch cable snapped.",
            submitted_by=1,
            site_id=1,
            activity="Drilling",
            submitted_at=datetime.now(timezone.utc),
            status=ReportStatus.reviewed,
            sif_label=SIFLabel.sif_potential,
            primary_lsr="Line of Fire",
            upload_batch_id=batch_id,
            upload_batch_label="Evaluation Test Batch",
            ground_truth_sif_label="sif_potential",  # TP
            ground_truth_lsr="Line of Fire",         # Correct LSR
            ground_truth_split="test",
        )
        r2 = Report(
            report_type=ReportType.UC,
            raw_text="Empty sample bottles stored loosely on metal shelf in warehouse.",
            submitted_by=1,
            site_id=1,
            activity="Storage",
            submitted_at=datetime.now(timezone.utc),
            status=ReportStatus.reviewed,
            sif_label=SIFLabel.non_sif,
            primary_lsr="Housekeeping",
            upload_batch_id=batch_id,
            upload_batch_label="Evaluation Test Batch",
            ground_truth_sif_label="non_sif",        # TN
            ground_truth_lsr="Housekeeping",         # Correct LSR
            ground_truth_split="test",
        )
        r3 = Report(
            report_type=ReportType.UA,
            raw_text="Electrician worked on low voltage 24V DC sensor panel without leather gloves.",
            submitted_by=1,
            site_id=1,
            activity="Electrical",
            submitted_at=datetime.now(timezone.utc),
            status=ReportStatus.reviewed,
            sif_label=SIFLabel.sif_potential,        # FP
            primary_lsr="Energy Isolation",
            upload_batch_id=batch_id,
            upload_batch_label="Evaluation Test Batch",
            ground_truth_sif_label="non_sif",
            ground_truth_lsr="Energy Isolation",
            ground_truth_split="train",
        )

        session.add_all([r1, r2, r3])
        await session.commit()

        report = await evaluate_batch_accuracy(session, batch_id=batch_id)

        assert report.total_reports == 3
        assert report.labeled_reports_count == 3
        assert report.confusion_matrix.true_positives == 1
        assert report.confusion_matrix.true_negatives == 1
        assert report.confusion_matrix.false_positives == 1
        assert report.confusion_matrix.false_negatives == 0
        assert report.overall_sif_accuracy == round(2 / 3, 4)

        # Test split evaluation
        assert "test" in report.splits_breakdown
        assert "train" in report.splits_breakdown
        assert report.splits_breakdown["test"].sif_metrics.accuracy == 1.0
        assert report.splits_breakdown["test"].sample_count == 2
        assert report.splits_breakdown["train"].sample_count == 1

        # LSR Accuracy
        assert len(report.lsr_rule_accuracies) >= 2
        assert report.lsr_macro_accuracy == 1.0


@pytest.mark.anyio
async def test_5_list_all_batches():
    """Verify batch listing returns distinct batches with metadata and accuracy."""
    import uuid
    batch_id = f"list_batch_{uuid.uuid4().hex[:8]}"

    async with AsyncSessionLocal() as session:
        r = Report(
            report_type=ReportType.near_miss,
            raw_text="Test description for batch listing test case.",
            submitted_by=1,
            site_id=1,
            activity="Drilling",
            submitted_at=datetime.now(timezone.utc),
            status=ReportStatus.reviewed,
            sif_label=SIFLabel.sif_potential,
            primary_lsr="Line of Fire",
            upload_batch_id=batch_id,
            upload_batch_label="List Test Batch",
            ground_truth_sif_label="sif_potential",
            ground_truth_lsr="Line of Fire",
            ground_truth_split="test",
        )
        session.add(r)
        await session.commit()

        batches_res = await list_all_batches(session)
        assert batches_res.total_batches >= 1
        batch_item = next((b for b in batches_res.batches if b.batch_id == batch_id), None)
        assert batch_item is not None
        assert batch_item.total_reports == 1
        assert batch_item.labeled_reports == 1
        assert "test" in batch_item.splits


@pytest.mark.anyio
async def test_6_api_endpoint_accuracy_report():
    """Test GET /api/datasets/{upload_batch_id}/accuracy-report endpoint."""
    import uuid
    batch_id = f"api_batch_{uuid.uuid4().hex[:8]}"

    async with AsyncSessionLocal() as session:
        r1 = Report(
            report_type=ReportType.near_miss,
            raw_text="Heavy casing pipe swung near drillers when secondary winch cable snapped.",
            submitted_by=1,
            site_id=1,
            activity="Drilling",
            submitted_at=datetime.now(timezone.utc),
            status=ReportStatus.reviewed,
            sif_label=SIFLabel.sif_potential,
            primary_lsr="Line of Fire",
            upload_batch_id=batch_id,
            upload_batch_label="API Test Batch",
            ground_truth_sif_label="sif_potential",
            ground_truth_lsr="Line of Fire",
            ground_truth_split="test",
        )
        session.add(r1)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test specific batch report
        res = await client.get(f"/api/datasets/{batch_id}/accuracy-report")
        assert res.status_code == 200
        data = res.json()
        assert data["batch_id"] == batch_id
        assert data["overall_sif_accuracy"] == 1.0
        assert "splits_breakdown" in data
        assert "test" in data["splits_breakdown"]
        assert data["splits_breakdown"]["test"]["sif_metrics"]["accuracy"] == 1.0

        # Test batch listing
        list_res = await client.get("/api/datasets/batches")
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert list_data["total_batches"] >= 1
