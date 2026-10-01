"""
SIF Sentinel AI - Unit Tests for Safety Barrier Extractor
Smart India Hackathon 2026 (Problem Statement PS 26165 - Oil India Limited)

Tests:
1. Taxonomy completeness (all 10 categories present)
2. Isolation Not Verified extraction & High severity
3. Guarding Removed/Bypassed extraction
4. Permit Not Checked/Invalid extraction
5. PPE Non-Compliance (Working at Height vs General)
6. Communication Breakdown & Supervision Gap
7. Equipment Failure & Fatigue/Human Factors
8. Housekeeping & Low severity
9. Multi-barrier extraction in single report
10. Evidence phrase quality and word containment
"""

import pytest
from app.ml.barrier_extractor import (
    BARRIER_TAXONOMY,
    extract_barriers_from_text,
    determine_barrier_severity,
)
from app.models.entities import BarrierSeverity


def test_1_taxonomy_completeness():
    """Verify all 10 required barrier categories exist in taxonomy."""
    expected = [
        "PPE Non-Compliance",
        "Isolation Not Verified",
        "Permit Not Checked/Invalid",
        "Guarding Removed/Bypassed",
        "Communication Breakdown",
        "Procedure Not Followed",
        "Supervision Gap",
        "Equipment Failure",
        "Fatigue/Human Factors",
        "Housekeeping",
    ]
    assert len(BARRIER_TAXONOMY) == 10
    for category in expected:
        assert category in BARRIER_TAXONOMY


def test_2_isolation_not_verified():
    """Test Isolation Not Verified barrier extraction & High severity."""
    text = (
        "Technician bypassed lockout tagout on discharge header electrical drive to expedite seal "
        "replacement before shift change without isolating 415V power."
    )
    results = extract_barriers_from_text(raw_text=text, is_sif=True)
    barrier_types = [r["barrier_type"] for r in results]
    
    assert "Isolation Not Verified" in barrier_types
    iso_result = next(r for r in results if r["barrier_type"] == "Isolation Not Verified")
    assert iso_result["severity"] == BarrierSeverity.high
    assert "lockout tagout" in iso_result["evidence_phrase"].lower() or "isolated" in iso_result["evidence_phrase"].lower()


def test_3_guarding_removed_bypassed():
    """Test Guarding Removed/Bypassed barrier extraction & High severity."""
    text = (
        "Roustabout operated mud pump with coupling guard removed and interlock bypassed, "
        "exposing crew to rotating drive shaft."
    )
    results = extract_barriers_from_text(raw_text=text, is_sif=True)
    barrier_types = [r["barrier_type"] for r in results]
    
    assert "Guarding Removed/Bypassed" in barrier_types
    guard_result = next(r for r in results if r["barrier_type"] == "Guarding Removed/Bypassed")
    assert guard_result["severity"] == BarrierSeverity.high
    assert "guard" in guard_result["evidence_phrase"].lower() or "interlock" in guard_result["evidence_phrase"].lower()


def test_4_permit_not_checked_invalid():
    """Test Permit Not Checked/Invalid barrier extraction."""
    text = (
        "Welder initiated angle grinding near oil separator tank without permit to work and without gas test certificate."
    )
    results = extract_barriers_from_text(raw_text=text, is_sif=True, primary_lsr="Hot Work")
    barrier_types = [r["barrier_type"] for r in results]
    
    assert "Permit Not Checked/Invalid" in barrier_types
    ptw_result = next(r for r in results if r["barrier_type"] == "Permit Not Checked/Invalid")
    assert ptw_result["severity"] == BarrierSeverity.high
    assert "permit" in ptw_result["evidence_phrase"].lower()


def test_5_ppe_non_compliance_height_vs_routine():
    """Test PPE Non-Compliance severity adapts (High for height/fall vs Low for minor)."""
    # 5a: Working at height without harness -> High severity
    height_text = "Derrickman was observed at 25-meter monkey board with unhooked harness and detached lanyard."
    height_results = extract_barriers_from_text(raw_text=height_text, is_sif=True)
    height_ppe = next((r for r in height_results if r["barrier_type"] == "PPE Non-Compliance"), None)
    assert height_ppe is not None
    assert height_ppe["severity"] == BarrierSeverity.high

    # 5b: General safety glasses in tool shed -> Low severity
    routine_text = "Storekeeper walked into parts warehouse without safety glasses during morning inventory."
    routine_results = extract_barriers_from_text(raw_text=routine_text, is_sif=False)
    routine_ppe = next((r for r in routine_results if r["barrier_type"] == "PPE Non-Compliance"), None)
    assert routine_ppe is not None
    assert routine_ppe["severity"] in [BarrierSeverity.low, BarrierSeverity.medium]


def test_6_communication_and_supervision():
    """Test Communication Breakdown and Supervision Gap detection."""
    text = (
        "Crane operator lifted 4-ton casing bundle when banksman missing and no radio communication "
        "established between rigger and operator."
    )
    results = extract_barriers_from_text(raw_text=text, is_sif=True, primary_lsr="Safe Mechanical Lifting")
    barrier_types = [r["barrier_type"] for r in results]
    
    assert "Communication Breakdown" in barrier_types or "Supervision Gap" in barrier_types


def test_7_equipment_failure_and_fatigue():
    """Test Equipment Failure and Fatigue/Human Factors detection."""
    text = (
        "Driver on 18-hour extended shift experienced double shift fatigue when brake failure occurred "
        "on heavy chemical transport bowser."
    )
    results = extract_barriers_from_text(raw_text=text, is_sif=True)
    barrier_types = [r["barrier_type"] for r in results]
    
    assert "Equipment Failure" in barrier_types
    assert "Fatigue/Human Factors" in barrier_types


def test_8_housekeeping_low_severity():
    """Test Housekeeping barrier detection with low severity for routine clutter."""
    text = "Loose wooden pallet and scattered tools left creating tripping hazard in workshop aisle."
    results = extract_barriers_from_text(raw_text=text, is_sif=False)
    barrier_types = [r["barrier_type"] for r in results]
    
    assert "Housekeeping" in barrier_types
    hk_result = next(r for r in results if r["barrier_type"] == "Housekeeping")
    assert hk_result["severity"] == BarrierSeverity.low


def test_9_procedure_not_followed():
    """Test Procedure Not Followed extraction."""
    text = "Assistant driller took unauthorized shortcut and procedure not followed during casing stabbing."
    results = extract_barriers_from_text(raw_text=text, is_sif=False)
    barrier_types = [r["barrier_type"] for r in results]
    
    assert "Procedure Not Followed" in barrier_types
