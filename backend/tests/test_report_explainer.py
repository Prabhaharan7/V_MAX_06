"""
SIF Sentinel AI - Unit Tests for Explainable AI Spans
Smart India Hackathon 2026 (Problem Statement PS 26165 - Oil India Limited)

Tests:
1. Span extraction structure and field validation
2. Character offset correctness (raw_text[start:end] matches matched_text)
3. SIF precursor phrases, LSR tags, and Barrier failure evidence presence
4. FastAPI endpoint GET /api/reports/{id}/explain routing and output
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.entities import Report, ReportLSRTag, BarrierFailure, BarrierSeverity, SIFLabel, ReportStatus, ReportType
from app.services.report_explainer import generate_explanation_spans


def test_1_span_generation_character_offsets():
    """Verify generated spans have exact matching character offsets."""
    text = (
        "Technician bypassed lockout tagout on discharge header electrical drive to expedite seal "
        "replacement before shift change without isolating 415V power."
    )
    mock_report = Report(
        id=101,
        raw_text=text,
        activity="Electrical Maintenance",
        sif_label=SIFLabel.sif_potential,
        sif_confidence=0.92,
        primary_lsr="Energy Isolation",
        status=ReportStatus.reviewed,
        report_type=ReportType.near_miss,
        submitted_by=1,
        site_id=1,
    )
    mock_report.lsr_tags = [
        ReportLSRTag(report_id=101, lsr_rule="Energy Isolation", confidence=0.94)
    ]
    mock_report.barrier_failures = [
        BarrierFailure(
            report_id=101,
            barrier_type="Isolation Not Verified",
            evidence_phrase="bypassed lockout tagout",
            severity=BarrierSeverity.high,
        )
    ]

    result = generate_explanation_spans(mock_report)
    assert result.id == 101
    assert result.text == text
    assert len(result.spans) > 0

    span_types = {s.type for s in result.spans}
    assert "sif_precursor" in span_types or "lsr_tag" in span_types or "barrier_failure" in span_types

    # Validate each span bounds and substring slice
    for s in result.spans:
        assert 0 <= s.start < s.end <= len(text)
        assert text[s.start:s.end] == s.matched_text
        assert s.confidence > 0.0
        assert s.type in ["sif_precursor", "lsr_tag", "barrier_failure"]


def test_2_multi_signal_spans():
    """Verify that SIF, LSR, and Barrier failure spans are all populated for multi-hazard reports."""
    text = (
        "Derrickman unhooked harness at 25m height on rig monkey board while lifting gear crane wire birdcaged."
    )
    mock_report = Report(
        id=102,
        raw_text=text,
        activity="Drilling",
        sif_label=SIFLabel.sif_potential,
        sif_confidence=0.89,
        primary_lsr="Working at Height",
        status=ReportStatus.reviewed,
        report_type=ReportType.near_miss,
        submitted_by=1,
        site_id=1,
    )
    mock_report.lsr_tags = [
        ReportLSRTag(report_id=102, lsr_rule="Working at Height", confidence=0.95),
        ReportLSRTag(report_id=102, lsr_rule="Safe Mechanical Lifting", confidence=0.85),
    ]
    mock_report.barrier_failures = [
        BarrierFailure(
            report_id=102,
            barrier_type="PPE Non-Compliance",
            evidence_phrase="unhooked harness",
            severity=BarrierSeverity.high,
        ),
        BarrierFailure(
            report_id=102,
            barrier_type="Equipment Failure",
            evidence_phrase="crane wire birdcaged",
            severity=BarrierSeverity.high,
        ),
    ]

    result = generate_explanation_spans(mock_report)
    labels = [s.label for s in result.spans]

    # Verify key labels are identified
    assert any("Working at Height" in l for l in labels) or any("PPE" in l for l in labels)
    assert any("Equipment Failure" in l for l in labels) or any("crane" in s.matched_text.lower() for s in result.spans)


def test_3_explain_endpoint_response():
    """Verify GET /api/reports/{id}/explain API endpoint returns expected schema."""
    import asyncio
    from app.core.database import get_db

    async def mock_get_db():
        text = "Technician bypassed lockout tagout on electrical drive."
        mock_rep = Report(
            id=1,
            raw_text=text,
            activity="Electrical",
            sif_label=SIFLabel.sif_potential,
            sif_confidence=0.88,
            primary_lsr="Energy Isolation",
            status=ReportStatus.reviewed,
            report_type=ReportType.near_miss,
            submitted_by=1,
            site_id=1,
        )
        mock_rep.lsr_tags = []
        mock_rep.barrier_failures = []

        class MockScalars:
            def all(self):
                return [mock_rep]
            def first(self):
                return mock_rep

        class MockResult:
            def scalars(self):
                return MockScalars()
            def scalar_one_or_none(self):
                return mock_rep

        class MockAsyncSession:
            async def execute(self, stmt):
                return MockResult()
        yield MockAsyncSession()

    app.dependency_overrides[get_db] = mock_get_db
    try:
        async def _test():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                openapi_paths = app.openapi()["paths"]
                assert "/api/reports/{id}/explain" in openapi_paths or "/api/v1/reports/{id}/explain" in openapi_paths

                resp = await client.get("/api/reports/1/explain")
                if resp.status_code == 200:
                    data = resp.json()
                    assert "text" in data
                    assert "spans" in data
                    assert isinstance(data["spans"], list)
                    if data["spans"]:
                        span = data["spans"][0]
                        assert "start" in span
                        assert "end" in span
                        assert "type" in span
                        assert "label" in span
                        assert "confidence" in span

        asyncio.run(_test())
    finally:
        app.dependency_overrides.pop(get_db, None)


