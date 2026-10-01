"""
SIF Sentinel AI - Vector Similarity & Safety Memory Nearest-Neighbor Service
Smart India Hackathon 2026 (Problem Statement PS 26165 - Oil India Limited)

Performs pgvector cosine-distance (<=> operator) nearest neighbor matching against:
1. Historical fatality case summaries (case_library table)
2. Historical safety observation reports (reports table)

Calculates cosine similarity scores and flags high-similarity fatality matches (> 0.75)
for immediate control-room warnings.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ml.sif_classifier import embedder
from app.models.entities import CaseLibrary, Report, Site
from app.schemas.safety_report import SimilarIncidentItem, SimilarIncidentsResponse

logger = logging.getLogger("sif_sentinel.similarity_service")


def _to_numpy_vector(vec_data: Any) -> Optional[np.ndarray]:
    """Converts a database vector (list, json string, or ndarray) to a normalized float32 numpy array."""
    if vec_data is None:
        return None
    if isinstance(vec_data, np.ndarray):
        arr = vec_data.astype(np.float32)
    elif isinstance(vec_data, (list, tuple)):
        arr = np.array(vec_data, dtype=np.float32)
    elif isinstance(vec_data, str):
        try:
            parsed = json.loads(vec_data)
            arr = np.array(parsed, dtype=np.float32)
        except Exception:
            return None
    else:
        return None

    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm
    return arr


def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Calculates cosine similarity between two normalized vectors."""
    dot = float(np.dot(vec_a, vec_b))
    return max(0.0, min(1.0, round(dot, 4)))


async def find_similar_incidents(
    db: AsyncSession,
    report: Report,
    top_k: int = 5,
    fatality_threshold: float = 0.75,
) -> SimilarIncidentsResponse:
    """
    Finds the top nearest-neighbor incidents and fatality cases matching the target report
    using pgvector cosine distance (<=> operator) with robust fallback.
    """
    # 1. Obtain or generate 384-dimensional dense embedding
    target_vec = _to_numpy_vector(report.embedding)
    if target_vec is None:
        target_vec = embedder.embed_text(f"{report.activity or ''} {report.raw_text}")
        norm = np.linalg.norm(target_vec)
        if norm > 0:
            target_vec = target_vec / norm

    fatality_items: List[SimilarIncidentItem] = []
    report_items: List[SimilarIncidentItem] = []

    # --------------------------------------------------------------------------
    # 2. Query CaseLibrary (Historical Fatalities)
    # --------------------------------------------------------------------------
    used_sql_vector = False
    try:
        from app.core.database import is_sqlite
        if not is_sqlite:
            # Try pgvector SQL cosine distance operator <=>
            case_stmt = (
                select(
                    CaseLibrary,
                    CaseLibrary.embedding.cosine_distance(target_vec.tolist()).label("distance"),
                )
                .where(CaseLibrary.embedding.isnot(None))
                .order_by("distance")
                .limit(top_k)
            )
            case_res = await db.execute(case_stmt)
            rows = case_res.all()
            if rows:
                for row in rows:
                    case_obj, distance = row[0], row[1]
                    sim = max(0.0, min(1.0, round(1.0 - float(distance or 0.0), 3)))
                    fatality_items.append(
                        SimilarIncidentItem(
                            id=case_obj.id,
                            source_type="case_library",
                            title=case_obj.title,
                            summary=case_obj.summary,
                            similarity_score=sim,
                            operation_type=case_obj.operation_type,
                            lsr_category=case_obj.lsr_category,
                            incident_year=case_obj.incident_year,
                            lessons_learned=case_obj.lessons_learned,
                            is_fatality_case=True,
                        )
                    )
                used_sql_vector = True
    except Exception as e:
        logger.debug(f"pgvector SQL query for CaseLibrary not available ({e}), using in-memory cosine fallback.")

    if not used_sql_vector:
        # Fallback: Load cases and calculate cosine similarity in Python
        case_stmt = select(CaseLibrary).where(CaseLibrary.embedding.isnot(None))
        cases = (await db.execute(case_stmt)).scalars().all()
        scored_cases = []
        for c in cases:
            c_vec = _to_numpy_vector(c.embedding)
            if c_vec is not None:
                sim = _cosine_similarity(target_vec, c_vec)
            else:
                # Generate embedding on the fly if needed
                c_vec = embedder.embed_text(f"{c.title} {c.summary} {c.lessons_learned}")
                sim = _cosine_similarity(target_vec, c_vec)
            scored_cases.append((sim, c))

        scored_cases.sort(key=lambda x: x[0], reverse=True)
        for sim, c in scored_cases[:top_k]:
            fatality_items.append(
                SimilarIncidentItem(
                    id=c.id,
                    source_type="case_library",
                    title=c.title,
                    summary=c.summary,
                    similarity_score=round(sim, 3),
                    operation_type=c.operation_type,
                    lsr_category=c.lsr_category,
                    incident_year=c.incident_year,
                    lessons_learned=c.lessons_learned,
                    is_fatality_case=True,
                )
            )

    # --------------------------------------------------------------------------
    # 3. Query Other Reports
    # --------------------------------------------------------------------------
    used_sql_reports = False
    try:
        from app.core.database import is_sqlite
        if not is_sqlite:
            rep_stmt = (
                select(
                    Report,
                    Report.embedding.cosine_distance(target_vec.tolist()).label("distance"),
                )
                .options(selectinload(Report.site))
                .where(Report.id != report.id, Report.embedding.isnot(None))
                .order_by("distance")
                .limit(top_k)
            )
            rep_res = await db.execute(rep_stmt)
            rows = rep_res.all()
            if rows:
                for row in rows:
                    rep_obj, distance = row[0], row[1]
                    sim = max(0.0, min(1.0, round(1.0 - float(distance or 0.0), 3)))
                    report_items.append(
                        SimilarIncidentItem(
                            id=rep_obj.id,
                            source_type="past_report",
                            title=f"Report #{rep_obj.id}: {rep_obj.activity}",
                            summary=rep_obj.raw_text,
                            similarity_score=sim,
                            operation_type=rep_obj.activity,
                            lsr_category=rep_obj.primary_lsr,
                            site_name=rep_obj.site.name if rep_obj.site else None,
                            is_fatality_case=False,
                            sif_label=rep_obj.sif_label.value if rep_obj.sif_label else None,
                        )
                    )
                used_sql_reports = True
    except Exception as e:
        logger.debug(f"pgvector SQL query for Reports not available ({e}), using in-memory cosine fallback.")

    if not used_sql_reports:
        # Fallback: Load reports and calculate cosine similarity in Python
        rep_stmt = select(Report).options(selectinload(Report.site)).where(Report.id != report.id)
        other_reports = (await db.execute(rep_stmt)).scalars().all()
        scored_reports = []
        for r in other_reports:
            r_vec = _to_numpy_vector(r.embedding)
            if r_vec is not None:
                sim = _cosine_similarity(target_vec, r_vec)
            else:
                r_vec = embedder.embed_text(f"{r.activity or ''} {r.raw_text}")
                sim = _cosine_similarity(target_vec, r_vec)
            scored_reports.append((sim, r))

        scored_reports.sort(key=lambda x: x[0], reverse=True)
        for sim, r in scored_reports[:top_k]:
            report_items.append(
                SimilarIncidentItem(
                    id=r.id,
                    source_type="past_report",
                    title=f"Report #{r.id}: {r.activity}",
                    summary=r.raw_text,
                    similarity_score=round(sim, 3),
                    operation_type=r.activity,
                    lsr_category=r.primary_lsr,
                    site_name=r.site.name if r.site else None,
                    is_fatality_case=False,
                    sif_label=r.sif_label.value if r.sif_label else None,
                )
            )

    # --------------------------------------------------------------------------
    # 4. Combine Top 5 Similar Cases & Compute High Similarity Flag
    # --------------------------------------------------------------------------
    combined_all = fatality_items + report_items
    combined_all.sort(key=lambda x: x.similarity_score, reverse=True)
    top_5_similar = combined_all[:top_k]

    max_fatality_sim = max((item.similarity_score for item in fatality_items), default=0.0)
    high_sim_flag = (max_fatality_sim > fatality_threshold)

    return SimilarIncidentsResponse(
        report_id=report.id,
        report_text=report.raw_text,
        high_similarity_to_past_fatality=high_sim_flag,
        max_fatality_similarity=round(max_fatality_sim, 3),
        top_similar_cases=top_5_similar,
        historical_fatality_cases=fatality_items[:top_k],
        similar_past_reports=report_items[:top_k],
    )
