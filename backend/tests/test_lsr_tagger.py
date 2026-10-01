"""
Unit Tests for IOGP Life-Saving Rules (LSR) Multi-Label Tagger
Testing PhraseMatcher, Semantic Canonical Similarity Fallback, Multi-Tagging, and Primary LSR Resolution.
"""

import pytest
import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ml.lsr_tagger import IOGP_LSR_RULES, tag_text


def test_1_energy_isolation_and_work_auth():
    """
    Test Case 1: Multi-label tagging for Energy Isolation + Work Authorisation
    Expected: Primary LSR 'Energy Isolation', tags containing Energy Isolation & Work Authorisation.
    """
    raw_text = (
        "Electrician began unbolting 415V MCC motor panel while energy not isolated and "
        "loto padlock was omitted. The permit to work (PTW) was expired by 2 hours."
    )
    result = tag_text(raw_text=raw_text, activity="Pump Maintenance")

    assert result["primary_lsr"] == "Energy Isolation", f"Expected Energy Isolation, got {result['primary_lsr']}"
    tag_names = [t["lsr_rule"] for t in result["tags"]]
    assert "Energy Isolation" in tag_names, "Energy Isolation tag missing"
    assert "Work Authorisation" in tag_names, "Work Authorisation tag missing"
    assert len(result["tags"]) >= 2, "Expected multi-label tagging with at least 2 rules"


def test_2_working_at_height():
    """
    Test Case 2: Working at Height trigger phrases
    Expected: Primary LSR 'Working at Height'.
    """
    raw_text = "Derrickman was observed with unhooked harness lanyard at 90ft monkey board elevation."
    result = tag_text(raw_text=raw_text, activity="Drilling Tripping")

    assert result["primary_lsr"] == "Working at Height"
    assert any(t["lsr_rule"] == "Working at Height" and t["confidence"] > 0.70 for t in result["tags"])


def test_3_confined_space_entry():
    """
    Test Case 3: Confined Space Entry triggers
    Expected: Primary LSR 'Confined Space Entry'.
    """
    raw_text = "Contractor entered mud tank without permit and atmospheric testing missing at tank manway."
    result = tag_text(raw_text=raw_text, activity="Tank Cleaning")

    assert result["primary_lsr"] == "Confined Space Entry"
    assert any(t["lsr_rule"] == "Confined Space Entry" and t["confidence"] > 0.70 for t in result["tags"])


def test_4_safe_mechanical_lifting():
    """
    Test Case 4: Safe Mechanical Lifting triggers
    Expected: Primary LSR 'Safe Mechanical Lifting'.
    """
    raw_text = "Hydra crane hoist wire rope birdcaging and workers worked under suspended load during BOP stack lift."
    result = tag_text(raw_text=raw_text, activity="Rig Move Lifting")

    assert result["primary_lsr"] == "Safe Mechanical Lifting"
    assert any(t["lsr_rule"] == "Safe Mechanical Lifting" for t in result["tags"])


def test_5_bypassing_safety_controls():
    """
    Test Case 5: Bypassing Safety Controls triggers
    Expected: Primary LSR 'Bypassing Safety Controls'.
    """
    raw_text = "Emergency shutdown ESD trip switch wedged with wooden wedge and gas detector muted on compressor C-101."
    result = tag_text(raw_text=raw_text, activity="Production Operations")

    assert result["primary_lsr"] == "Bypassing Safety Controls"
    assert any(t["lsr_rule"] == "Bypassing Safety Controls" for t in result["tags"])


def test_6_driving_and_line_of_fire():
    """
    Test Case 6: Driving and Line of Fire triggers
    Expected: Correct LSR identification for vehicle / line of fire hazard.
    """
    raw_text = "Near miss with vehicle: crude oil tanker speeding on bund road with rusted spark arrestor open."
    result = tag_text(raw_text=raw_text, activity="Logistics")

    assert result["primary_lsr"] == "Driving"
    assert any(t["lsr_rule"] == "Driving" for t in result["tags"])


def test_7_routine_housekeeping_no_lsr():
    """
    Test Case 7: Routine housekeeping without Life-Saving Rule breach
    Expected: primary_lsr is None, 0 critical tags.
    """
    raw_text = "Empty water bottles and food wrappers discarded on gravel near tool container."
    result = tag_text(raw_text=raw_text, activity="Housekeeping")

    assert result["primary_lsr"] is None
    assert result["total_tags"] == 0
