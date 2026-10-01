"""
Unit Tests for SIF Sentinel AI Hybrid SIF-Potential Classifier
Testing spaCy Rule Layer, Semantic Embedding Layer, Hybrid Fusion, and Review Queue Routing.
"""

import pytest
import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.entities import SIFLabel, ReportStatus
from app.ml.sif_classifier import (
    classify_text,
    evaluate_rule_layer,
    embedder,
)


def test_1_clear_sif_energy_isolation():
    """
    Test Case 1: Clear SIF Precursor (Energy Isolation / LOTO failure)
    Expected: sif_potential label, confidence > 0.60, Energy Isolation category, 384-dim vector.
    """
    raw_text = (
        "Electrician was unbolting 415V MCC motor breaker without lockout tagout LOTO padlock "
        "while energy not isolated and live bus nearby."
    )
    activity = "Electrical Maintenance"

    result = classify_text(raw_text=raw_text, activity=activity)

    assert result["is_sif_precursor"] is True, "Expected SIF precursor classification"
    assert result["sif_label"] == SIFLabel.sif_potential, "Expected sif_potential label"
    assert result["sif_confidence"] > 0.60, f"Expected confidence > 0.60, got {result['sif_confidence']}"
    assert result["precursor_category"] == "Energy Isolation", f"Expected Energy Isolation, got {result['precursor_category']}"
    assert len(result["embedding"]) == 384, f"Expected 384-dim embedding vector, got {len(result['embedding'])}"
    assert result["is_ambiguous"] is False, "Clear SIF should not be marked ambiguous"


def test_2_clear_sif_confined_space_and_suspended_load():
    """
    Test Case 2: Clear SIF Precursor (Confined Space & Suspended Load)
    Expected: sif_potential label, confidence > 0.60, high-risk rule match.
    """
    raw_text = (
        "Contractor entered confined space without permit while crane hoist wire snapped "
        "and worked under suspended load with catastrophic near miss."
    )
    activity = "Tank Cleaning & Lifting"

    result = classify_text(raw_text=raw_text, activity=activity)

    assert result["is_sif_precursor"] is True
    assert result["sif_label"] == SIFLabel.sif_potential
    assert result["sif_confidence"] > 0.60
    assert result["precursor_category"] in ["Confined Space Entry", "Safe Mechanical Lifting"]
    assert len(result["evidence_phrases"]) >= 1


def test_3_clear_non_sif_housekeeping():
    """
    Test Case 3: Clear Non-SIF (Routine Housekeeping)
    Expected: non_sif label, confidence < 0.40, auto_confirmed status.
    """
    raw_text = (
        "Empty plastic water bottles, biscuit wrappers, and tea cups discarded on gravel "
        "beside mechanical tool container. Housekeeping instructed to site helper crew."
    )
    activity = "Routine Housekeeping"

    result = classify_text(raw_text=raw_text, activity=activity)

    assert result["is_sif_precursor"] is False, "Housekeeping should not be classified as SIF"
    assert result["sif_label"] == SIFLabel.non_sif, "Expected non_sif label"
    assert result["sif_confidence"] < 0.40, f"Expected confidence < 0.40, got {result['sif_confidence']}"
    assert result["status"] == ReportStatus.auto_confirmed, f"Expected auto_confirmed, got {result['status']}"
    assert result["is_ambiguous"] is False


def test_4_clear_non_sif_ppe_and_lighting():
    """
    Test Case 4: Clear Non-SIF (Minor PPE & Administrative Note)
    Expected: non_sif label, confidence < 0.40, auto_confirmed status.
    """
    raw_text = (
        "Helper in warehouse material yard observed using torn cotton gloves with exposed fingers. "
        "Overhead fluorescent bulb flickering in store room."
    )
    activity = "Warehouse Inspection"

    result = classify_text(raw_text=raw_text, activity=activity)

    assert result["is_sif_precursor"] is False
    assert result["sif_label"] == SIFLabel.non_sif
    assert result["sif_confidence"] < 0.40
    assert result["status"] == ReportStatus.auto_confirmed


def test_5_ambiguous_borderline_report_review_queue():
    """
    Test Case 5: Ambiguous / Borderline Report
    Expected: confidence between 0.40 and 0.60, is_ambiguous=True, status='pending_review'
    for Human-in-the-Loop review queue routing.
    """
    raw_text = (
        "Faint sulfur smell noted near test separator manifold during afternoon, "
        "pipe vibration and flange soap bubble test was inconclusive with slight dampness."
    )
    activity = "Production Walkthrough"

    result = classify_text(raw_text=raw_text, activity=activity)

    assert 0.40 <= result["sif_confidence"] <= 0.60, (
        f"Expected confidence in ambiguous range [0.40, 0.60], got {result['sif_confidence']}"
    )
    assert result["is_ambiguous"] is True, "Expected is_ambiguous=True for borderline score"
    assert result["status"] == ReportStatus.pending_review, (
        f"Expected status pending_review for review queue, got {result['status']}"
    )
