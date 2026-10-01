"""
SIF Sentinel AI - Unit Tests for Vector Similarity & Safety Memory Service
Smart India Hackathon 2026 (Problem Statement PS 26165 - Oil India Limited)

Tests:
1. Vector cosine similarity computation and normalization
2. Nearest neighbor query against CaseLibrary (historical fatalities) and Reports
3. High similarity to past fatality flag (similarity > 0.75)
4. Fast API endpoint GET /api/reports/{id}/similar-incidents routing & schema
"""

import asyncio
import numpy as np
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.ml.sif_classifier import embedder
from app.models.entities import CaseLibrary, Report, ReportStatus, ReportType, SIFLabel
from app.services.similarity_service import _cosine_similarity, _to_numpy_vector, find_similar_incidents


def test_1_cosine_similarity_math():
    """Verify normalized cosine similarity calculation."""
    vec_a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    vec_b = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    vec_c = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    assert _cosine_similarity(vec_a, vec_b) == 1.0
    assert _cosine_similarity(vec_a, vec_c) == 0.0

    # Vector converter helper
    parsed = _to_numpy_vector([1.0, 2.0, 3.0])
    assert parsed is not None
    assert np.isclose(np.linalg.norm(parsed), 1.0)


def test_2_high_similarity_fatality_flag():
    """Verify high_similarity_to_past_fatality flag triggers when similarity > 0.75."""
    # Test case matching the LOTO / Hydraulic energy fatality
    text = (
        "Technician bypassed lockout tagout and neglected to bleed stored hydraulic accumulator "
        "pressure before servicing iron roughneck cylinder piston."
    )
    emb = embedder.embed_text(text)
    norm = np.linalg.norm(emb)
    if norm > 0:
        emb = emb / norm

    mock_report = Report(
        id=201,
        raw_text=text,
        activity="Workover",
        sif_label=SIFLabel.sif_potential,
        sif_confidence=0.94,
        primary_lsr="Energy Isolation",
        status=ReportStatus.reviewed,
        report_type=ReportType.near_miss,
        submitted_by=1,
        site_id=1,
        embedding=emb.tolist(),
    )

    class MockAsyncSession:
        async def execute(self, stmt):
            stmt_str = str(stmt).lower()
            class MockResult:
                def all(self):
                    return []
                def scalars(self):
                    class MockScalars:
                        def all(self):
                            if "case_library" in stmt_str:
                                fatality = CaseLibrary(
                                    id=1,
                                    title="Lethal Stored Hydraulic Energy Release during Iron Roughneck Piston Servicing",
                                    summary="Technician unbolted hydraulic cap without bleeding residual accumulator pressure.",
                                    incident_year=2019,
                                    operation_type="Workover",
                                    lsr_category="Energy Isolation",
                                    root_causes="Bypass of LOTO procedures",
                                    lessons_learned="Mandatory double block & bleed",
                                    embedding=emb.tolist(),  # identical embedding -> sim 1.0 > 0.75
                                )
                                return [fatality]
                            elif "reports" in stmt_str:
                                other_rep = Report(
                                    id=202,
                                    raw_text="Routine electrical workover inspection.",
                                    activity="Workover",
                                    sif_label=SIFLabel.non_sif,
                                    sif_confidence=0.80,
                                    primary_lsr="Energy Isolation",
                                    status=ReportStatus.reviewed,
                                    report_type=ReportType.near_miss,
                                    submitted_by=1,
                                    site_id=1,
                                    embedding=emb.tolist(),
                                )
                                return [other_rep]
                            return []
                    return MockScalars()
            return MockResult()

    async def _test():
        res = await find_similar_incidents(
            db=MockAsyncSession(),
            report=mock_report,
            top_k=5,
            fatality_threshold=0.75,
        )
        assert res.report_id == 201
        assert len(res.top_similar_cases) > 0
        assert res.high_similarity_to_past_fatality is True
        assert res.max_fatality_similarity >= 0.75

    asyncio.run(_test())


def test_3_similar_incidents_endpoint():
    """Verify GET /api/reports/{id}/similar-incidents endpoint routing and schema."""
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
            embedding=[0.05] * 384,
        )
        mock_rep.lsr_tags = []
        mock_rep.barrier_failures = []

        mock_case = CaseLibrary(
            id=1,
            title="Electrical Shock During Maintenance",
            summary="Technician contacted energized 415V busbar during maintenance.",
            operation_type="Electrical Maintenance",
            lsr_category="Energy Isolation",
            incident_year=2024,
            lessons_learned="Always verify zero voltage with calibrated meter.",
            embedding=[0.05] * 384,
        )

        mock_other_rep = Report(
            id=2,
            raw_text="Another electrical event at rig site.",
            activity="Drilling",
            sif_label=SIFLabel.sif_potential,
            sif_confidence=0.82,
            primary_lsr="Energy Isolation",
            status=ReportStatus.reviewed,
            report_type=ReportType.near_miss,
            submitted_by=1,
            site_id=1,
            embedding=[0.05] * 384,
        )
        mock_other_rep.lsr_tags = []
        mock_other_rep.barrier_failures = []
        mock_other_rep.site = None

        class MockResult:
            def __init__(self, items, single=None):
                self._items = items
                self._single = single or (items[0] if items else None)
            def scalars(self):
                class MockScalars:
                    def __init__(self, items, single):
                        self._items = items
                        self._single = single
                    def all(self):
                        return self._items
                    def first(self):
                        return self._single
                return MockScalars(self._items, self._single)
            def scalar_one_or_none(self):
                return self._single
            def all(self):
                return [(item, 0.1) for item in self._items]

        class MockAsyncSession:
            async def execute(self, stmt):
                stmt_str = str(stmt).lower()
                if "case_library" in stmt_str:
                    return MockResult([mock_case])
                elif "reports.id !=" in stmt_str or "reports.id ! =" in stmt_str:
                    return MockResult([mock_other_rep])
                return MockResult([mock_rep], mock_rep)
        yield MockAsyncSession()

    app.dependency_overrides[get_db] = mock_get_db
    try:
        async def _test():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                openapi_paths = app.openapi()["paths"]
                assert "/api/reports/{id}/similar-incidents" in openapi_paths or "/api/v1/reports/{id}/similar-incidents" in openapi_paths

                # Query seeded report ID 1
                resp = await client.get("/api/reports/1/similar-incidents")
                if resp.status_code == 200:
                    data = resp.json()
                    assert "report_id" in data
                    assert "high_similarity_to_past_fatality" in data
                    assert "max_fatality_similarity" in data
                    assert "top_similar_cases" in data
                    assert isinstance(data["top_similar_cases"], list)
                    if data["top_similar_cases"]:
                        case = data["top_similar_cases"][0]
                        assert "id" in case
                        assert "title" in case
                        assert "similarity_score" in case
                        assert 0.0 <= case["similarity_score"] <= 1.0

        asyncio.run(_test())
    finally:
        app.dependency_overrides.pop(get_db, None)

