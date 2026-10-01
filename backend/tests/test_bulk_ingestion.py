"""
================================================================================
SIF Sentinel AI - Unit Tests for Bulk Spreadsheet Ingestion Parser
Smart India Hackathon 2026 (Problem Statement PS 26165 - Oil India Limited)
================================================================================
"""

import io
import pytest
import pandas as pd
from app.models.entities import ReportType
from app.services.bulk_ingestion import (
    COLUMN_ALIASES,
    match_column_headers,
    normalize_header,
    canonical_alphanumeric,
    parse_report_type,
    read_spreadsheet_dataframe,
    parse_and_validate_bulk_records,
)


def test_1_normalize_header_and_canonical_alpha():
    """Verify robust normalization for whitespace, case, and special characters."""
    assert normalize_header("  Report_Type  ") == "report_type"
    assert normalize_header("REPORT TYPE") == "report_type"
    assert normalize_header("Raw-Text") == "raw_text"
    assert canonical_alphanumeric("Report_Type") == "reporttype"
    assert canonical_alphanumeric("  raw text  ") == "rawtext"


def test_2_reordered_and_aliased_columns_csv():
    """
    Test parsing CSV with reordered/differently-named columns:
    Report_ID, Date, Site, Area, Report_Type, Activity, Equipment, raw_text, Hazard_Energy, SIF_Label
    Ensures raw_text is matched by name and NOT misread from Date or other columns.
    """
    csv_data = """Report_ID,Date,Site,Area,Report_Type,Activity,Equipment,raw_text,Hazard_Energy,SIF_Label
R1001,2026-03-15,OIL Duliajan HQ,Drilling Floor,Near Miss,Rig Maintenance,Top Drive,High pressure mud line flange had loose bolts vibrating during circulation.,Pressurized Mud,sif_potential
R1002,2026-03-16,Digboi Production,Compressor Station,Unsafe Act,Flange Tightening,Gas Compressor,Worker attempted to tighten high pressure flange without isolating compressor discharge line.,Flammable Gas,sif_potential
R1003,2026-03-17,OIL Duliajan HQ,Workshop,Unsafe Condition,Welding,Oxygen Cylinder,Damaged flash back arrestor detected on oxy-acetylene cylinder cart in workshop.,Fire/Explosion,non_sif
"""
    df = pd.read_csv(io.StringIO(csv_data))
    site_names_map = {
        "oil_duliajan_hq": 1,
        "oilduliajanhq": 1,
        "digboi_production": 2,
        "digboiproduction": 2,
    }
    existing_site_ids = {1, 2}

    reports, summary = parse_and_validate_bulk_records(
        df=df,
        existing_sites_by_id=existing_site_ids,
        site_names_map=site_names_map,
        default_user_id=1,
    )

    assert summary.total_rows == 3
    assert summary.accepted_count == 3
    assert summary.rejected_count == 0
    assert len(reports) == 3

    # Check first report
    r1 = reports[0]
    assert r1.site_id == 1
    assert r1.report_type == ReportType.near_miss
    assert r1.activity == "Rig Maintenance"
    assert "High pressure mud line flange" in r1.raw_text
    assert r1.raw_text != "2026-03-15"  # Ensure Date column wasn't mistakenly used
    assert r1.raw_metadata is not None
    assert r1.raw_metadata.get("Report_ID") == "R1001"
    assert r1.raw_metadata.get("Area") == "Drilling Floor"
    assert r1.raw_metadata.get("Equipment") == "Top Drive"
    assert r1.raw_metadata.get("Hazard_Energy") == "Pressurized Mud"
    assert r1.raw_metadata.get("SIF_Label") == "sif_potential"

    # Check second report
    r2 = reports[1]
    assert r2.site_id == 2
    assert r2.report_type == ReportType.UA
    assert r2.activity == "Flange Tightening"
    assert "Worker attempted to tighten" in r2.raw_text


def test_3_header_aliases_and_case_insensitivity():
    """Verify various aliases like narrative, observation_type, location, work_activity match correctly."""
    columns = ["Observation_ID", "TIMESTAMP", "Location", "Observation_Type", "Work_Activity", "Narrative", "LSR_Rule"]
    mapped, extra = match_column_headers(columns)

    assert mapped["raw_text"] == "Narrative"
    assert mapped["report_type"] == "Observation_Type"
    assert mapped["site_id"] == "Location"
    assert mapped["activity"] == "Work_Activity"
    assert mapped["submitted_at"] == "TIMESTAMP"
    assert "Observation_ID" in extra
    assert "LSR_Rule" in extra


def test_4_row_validation_raw_text_length():
    """Verify only rows where raw_text < 10 chars or empty are rejected."""
    csv_data = """site_id,report_type,activity,raw_text,extra_info
1,near_miss,Drilling,Valid observation narrative about overhead crane hook latch.,Extra1
1,near_miss,Drilling,Short,Extra2
1,near_miss,Drilling,,Extra3
1,near_miss,Drilling,NaN,Extra4
1,UA,Lifting,Rig technician bypassed secondary safety sling during pipe haul.,Extra5
"""
    df = pd.read_csv(io.StringIO(csv_data))
    reports, summary = parse_and_validate_bulk_records(
        df=df,
        existing_sites_by_id={1},
        site_names_map={"site_1": 1},
    )

    assert summary.total_rows == 5
    assert summary.accepted_count == 2
    assert summary.rejected_count == 3
    assert len(summary.rejection_breakdown) == 1
    assert "raw_text" in summary.rejection_breakdown[0].reason
    assert summary.rejection_breakdown[0].count == 3


def test_5_fast_fail_on_missing_required_columns():
    """Verify whole upload fails fast if a required column (e.g. raw_text) is missing."""
    csv_data = """Date,Site_ID,Activity,Report_Type,Equipment
2026-03-15,1,Maintenance,near_miss,Pump A
2026-03-16,1,Drilling,UA,Rig B
"""
    df = pd.read_csv(io.StringIO(csv_data))
    with pytest.raises(ValueError) as exc_info:
        parse_and_validate_bulk_records(
            df=df,
            existing_sites_by_id={1},
            site_names_map={},
        )

    assert "Missing required column(s): 'raw_text'" in str(exc_info.value)


def test_6_grouped_rejections_and_max_20_examples():
    """Verify rejection reasons are grouped and example snippets are capped at 20."""
    rows = []
    # 25 rows with too short raw_text
    for i in range(25):
        rows.append({
            "site_id": 1,
            "report_type": "near_miss",
            "activity": "Drilling",
            "raw_text": f"short{i}",
            "custom_col": f"val_{i}",
        })
    # 5 rows with unknown site
    for i in range(5):
        rows.append({
            "site_id": 9999,
            "report_type": "near_miss",
            "activity": "Drilling",
            "raw_text": "Sufficiently long description of safety event in field.",
            "custom_col": f"val_{i}",
        })

    df = pd.DataFrame(rows)
    reports, summary = parse_and_validate_bulk_records(
        df=df,
        existing_sites_by_id={1},
        site_names_map={},
    )

    assert summary.total_rows == 30
    assert summary.accepted_count == 0
    assert summary.rejected_count == 30
    assert len(summary.rejection_breakdown) == 2

    short_grp = next(g for g in summary.rejection_breakdown if "raw_text" in g.reason)
    assert short_grp.count == 25
    assert len(short_grp.examples) == 20  # Capped at 20 examples

    site_grp = next(g for g in summary.rejection_breakdown if "Site" in g.reason)
    assert site_grp.count == 5
    assert len(site_grp.examples) == 5


def test_7_preview_and_custom_column_mapping():
    """
    Test preview endpoint functionality and applying custom column mapping
    on arbitrary/custom column names.
    """
    from app.services.bulk_ingestion import preview_spreadsheet_mapping

    csv_data = b"""Custom_Log_Number,Incident_Details,Location_Name,Work_Type,Event_Classification
101,Worker stepped on unsecured floor grating over mud pit in Rig 14,Rig 14 (Drilling Moran),Well Maintenance,Near Miss
102,High pressure hose detached during casing pressure testing,Rig 14 (Drilling Moran),Casing,Unsafe Condition
"""
    preview = preview_spreadsheet_mapping(csv_data, "arbitrary_hse_export.csv")
    assert preview.total_preview_rows == 2
    assert len(preview.detected_columns) == 5
    assert "Incident_Details" in preview.detected_columns
    assert len(preview.sample_rows) == 2

    # Now apply explicit custom mapping
    custom_map = {
        "raw_text": "Incident_Details",
        "site_id": "Location_Name",
        "activity": "Work_Type",
        "report_type": "Event_Classification",
    }
    df = pd.read_csv(io.BytesIO(csv_data))
    reports, summary = parse_and_validate_bulk_records(
        df=df,
        existing_sites_by_id={1},
        site_names_map={
            "rig_14_(drilling_moran)": 1,
            "rig14drillingmoran": 1,
        },
        custom_mapping=custom_map,
    )
    assert summary.accepted_count == 2
    assert summary.rejected_count == 0
    assert "Worker stepped on unsecured floor grating" in reports[0].raw_text
    assert reports[0].site_id == 1


