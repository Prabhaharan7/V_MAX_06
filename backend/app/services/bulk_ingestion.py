"""
================================================================================
SIF Sentinel AI - Bulk Spreadsheet Ingestion Parser & Validator
SIH 2026 Problem Statement PS 26165 (Oil India Limited)
================================================================================
Handles CSV and XLSX bulk ingestion for safety observation logs:
1. Reads file with pandas using the first row as headers.
2. Matches required fields by name/alias case-insensitively and whitespace-trimmed.
3. Detects and extracts known ground-truth benchmark columns (SIF_Label, Life_Saving_Rule,
   Barrier_Status, Split, Actual_Outcome) for live accuracy evaluations.
4. Preserves all extra metadata columns in a raw_metadata JSON dictionary.
5. Fails fast if required columns cannot be confidently matched.
6. Performs row-by-row validation (raw_text >= 10 chars, site matching).
7. Tags each upload with a batch_id and batch_label for historical tracking.
8. Returns ingestion summary with rejection reasons grouped by type (max 20 examples).
================================================================================
"""

import hashlib
import io
import re
import uuid
from collections import defaultdict
from datetime import datetime, date, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
import pandas as pd

from app.models.entities import Report, ReportType, ReportStatus
from app.schemas.safety_report import (
    BulkPreviewResponse,
    BulkUploadErrorGroup,
    BulkUploadRowError,
    BulkUploadSummaryResponse,
    ColumnMappingSuggestion,
    TargetFieldDefinition,
)


# ==============================================================================
# 1. Column Alias Mapping Configuration
# ==============================================================================

COLUMN_ALIASES: Dict[str, List[str]] = {
    "raw_text": [
        "raw_text",
        "rawtext",
        "narrative",
        "description",
        "text",
        "observation",
        "observation_text",
        "observationtext",
        "incident_description",
        "incidentdescription",
        "event_description",
        "eventdescription",
        "details",
        "summary",
        "notes",
        "incident_narrative",
        "report_text",
        "reporttext",
    ],
    "report_type": [
        "report_type",
        "reporttype",
        "type",
        "observation_type",
        "observationtype",
        "incident_type",
        "incidenttype",
        "event_type",
        "eventtype",
        "report_category",
        "category",
        "classification",
    ],
    "site_id": [
        "site_id",
        "siteid",
        "site",
        "location",
        "site_name",
        "sitename",
        "installation",
        "facility",
        "plant",
        "unit",
        "site_code",
        "asset",
        "field",
    ],
    "activity": [
        "activity",
        "task",
        "work_activity",
        "workactivity",
        "operation",
        "job_activity",
        "jobactivity",
        "job",
        "process",
        "work_task",
        "worktask",
        "work",
        "operation_type",
    ],
    "submitted_at": [
        "submitted_at",
        "submittedat",
        "date",
        "report_date",
        "reportdate",
        "incident_date",
        "incidentdate",
        "event_date",
        "eventdate",
        "timestamp",
        "datetime",
        "date_time",
        "time",
    ],
    # Ground-truth evaluation columns
    "ground_truth_sif_label": [
        "sif_label",
        "siflabel",
        "ground_truth_sif_label",
        "ground_truth_sif",
        "sif_potential",
        "is_sif",
        "actual_sif",
        "sif",
        "sif_category",
    ],
    "ground_truth_lsr": [
        "life_saving_rule",
        "lifesavingrule",
        "lsr",
        "lsr_rule",
        "primary_lsr",
        "ground_truth_lsr",
        "lsr_category",
        "actual_lsr",
        "safety_rule",
        "rule",
    ],
    "ground_truth_barrier_status": [
        "barrier_status",
        "barrierstatus",
        "ground_truth_barrier_status",
        "barrier_state",
        "barrier_condition",
        "barrier_failed",
        "actual_outcome",
        "outcome",
        "barrier_expected",
    ],
    "ground_truth_split": [
        "split",
        "dataset_split",
        "data_split",
        "train_test_split",
        "subset",
        "fold",
        "split_group",
    ],
}

REQUIRED_TARGET_FIELDS = ["raw_text", "report_type", "site_id", "activity"]
OPTIONAL_TARGET_FIELDS = [
    "submitted_at",
    "ground_truth_sif_label",
    "ground_truth_lsr",
    "ground_truth_barrier_status",
    "ground_truth_split",
]
TARGET_ORDER = REQUIRED_TARGET_FIELDS + OPTIONAL_TARGET_FIELDS

TARGET_FIELD_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "key": "raw_text",
        "label": "Observation Narrative / Description",
        "required": True,
        "description": "Full observation, hazard description, or incident narrative (min 10 characters).",
    },
    {
        "key": "report_type",
        "label": "Report Type",
        "required": True,
        "description": "Classification: Near Miss, Unsafe Act (UA), Unsafe Condition (UC), or Incident.",
    },
    {
        "key": "site_id",
        "label": "Site / Facility ID or Name",
        "required": True,
        "description": "Rig, well pad, pipeline station, compressor station, or offshore base name or integer ID.",
    },
    {
        "key": "activity",
        "label": "Activity / Operation",
        "required": True,
        "description": "Ongoing job task: Workover, Casing, Drilling, High Pressure Fitting, Tank Cleaning, etc.",
    },
    {
        "key": "submitted_at",
        "label": "Date / Time of Observation",
        "required": False,
        "description": "Date or timestamp when observation occurred.",
    },
    {
        "key": "ground_truth_sif_label",
        "label": "Ground-Truth SIF Label",
        "required": False,
        "description": "Annotated benchmark class: SIF-potential, Non-SIF, or Precursor.",
    },
    {
        "key": "ground_truth_lsr",
        "label": "Ground-Truth Life-Saving Rule",
        "required": False,
        "description": "Annotated IOGP Life-Saving Rule category for benchmark validation.",
    },
    {
        "key": "ground_truth_barrier_status",
        "label": "Ground-Truth Barrier Status",
        "required": False,
        "description": "Annotated barrier integrity/failure status.",
    },
    {
        "key": "ground_truth_split",
        "label": "Dataset Split (Train / Test / Val)",
        "required": False,
        "description": "Subset tag (train/test/val) for separate holdout validation.",
    },
]


def compute_column_fingerprint(columns: List[str]) -> str:
    """
    Generates a deterministic fingerprint hash for a set of spreadsheet column headers.
    """
    normalized = sorted([re.sub(r"[\s_\-]+", "_", str(c).strip().lower()).strip("_") for c in columns if str(c).strip()])
    joined = "|".join(normalized)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def normalize_custom_mapping(
    custom_mapping: Dict[str, str],
    actual_columns: List[str],
) -> Dict[str, str]:
    """
    Normalizes a custom column mapping into a standard {target_field: actual_column_name} format.
    Handles both {target_field: detected_col} and {detected_col: target_field}.
    """
    valid_targets = set(TARGET_ORDER)
    actual_cols_set = set(actual_columns)
    actual_cols_lower = {str(c).strip().lower(): str(c).strip() for c in actual_columns}

    resolved: Dict[str, str] = {}

    for k, v in custom_mapping.items():
        if not k or not v or str(v).lower() in ["ignore", "none", "null", ""]:
            continue

        str_k = str(k).strip()
        str_v = str(v).strip()

        # Case 1: key is target_field (e.g. "raw_text": "Observation")
        if str_k in valid_targets:
            if str_v in actual_cols_set:
                resolved[str_k] = str_v
            elif str_v.lower() in actual_cols_lower:
                resolved[str_k] = actual_cols_lower[str_v.lower()]

        # Case 2: value is target_field (e.g. "Observation": "raw_text")
        elif str_v in valid_targets:
            if str_k in actual_cols_set:
                resolved[str_v] = str_k
            elif str_k.lower() in actual_cols_lower:
                resolved[str_v] = actual_cols_lower[str_k.lower()]

    return resolved


def normalize_header(header: Any) -> str:
    """
    Normalizes a header name for robust matching:
    Converts to lowercase, strips leading/trailing spaces and underscores,
    and consolidates multiple spaces/underscores/hyphens to a single underscore.
    """
    if header is None:
        return ""
    text = str(header).strip().lower()
    return re.sub(r"[\s_\-]+", "_", text).strip("_")


def canonical_alphanumeric(header: Any) -> str:
    """
    Removes all non-alphanumeric characters for fuzzy alias matching.
    e.g. 'Report_Type' -> 'reporttype', 'raw text' -> 'rawtext'
    """
    if header is None:
        return ""
    return re.sub(r"[^a-z0-9]", "", str(header).lower())


def match_column_headers(
    actual_columns: List[str],
    custom_mapping: Optional[Dict[str, str]] = None,
) -> Tuple[Dict[str, str], List[str]]:
    """
    Matches the actual columns of a spreadsheet to target fields.
    If custom_mapping is provided, respects confirmed user selections.
    Otherwise, applies rule-based and alias matching.

    Returns:
      - mapped_targets: dict of {target_field: actual_column_name}
      - extra_columns: list of actual column names that are not mapped to target fields
    """
    if custom_mapping:
        resolved = normalize_custom_mapping(custom_mapping, actual_columns)
        mapped_targets = {target: col for target, col in resolved.items() if col in actual_columns}
        core_cols = set(mapped_targets.values())
        extra_columns = [col for col in actual_columns if col not in core_cols]
        return mapped_targets, extra_columns

    mapped_targets: Dict[str, str] = {}
    used_columns: Set[str] = set()

    # Create lookup maps for actual columns
    norm_actual = {col: normalize_header(col) for col in actual_columns}
    alpha_actual = {col: canonical_alphanumeric(col) for col in actual_columns}

    # Match in priority order
    for target in TARGET_ORDER:
        aliases = COLUMN_ALIASES.get(target, [])
        norm_aliases = [normalize_header(a) for a in aliases]
        alpha_aliases = [canonical_alphanumeric(a) for a in aliases]

        matched_col = None

        # 1. Exact normalized match (e.g. 'report_type' == 'report_type')
        for col in actual_columns:
            if col in used_columns:
                continue
            if norm_actual[col] in norm_aliases:
                matched_col = col
                break

        # 2. Alphanumeric match (e.g. 'Report Type' -> 'reporttype')
        if not matched_col:
            for col in actual_columns:
                if col in used_columns:
                    continue
                if alpha_actual[col] in alpha_aliases:
                    matched_col = col
                    break

        # 3. Substring match fallback for targets like raw_text ("narrative", "description")
        if not matched_col and target == "raw_text":
            for col in actual_columns:
                if col in used_columns:
                    continue
                if any(sub in norm_actual[col] for sub in ["raw_text", "narrative", "description", "observation"]):
                    matched_col = col
                    break

        if matched_col:
            mapped_targets[target] = matched_col
            used_columns.add(matched_col)

    # Core required/standard columns
    core_cols = {
        mapped_targets.get("raw_text"),
        mapped_targets.get("report_type"),
        mapped_targets.get("site_id"),
        mapped_targets.get("activity"),
        mapped_targets.get("submitted_at"),
    }
    extra_columns = [col for col in actual_columns if col not in core_cols and col is not None]
    return mapped_targets, extra_columns


def parse_report_type(raw_val: Any) -> ReportType:
    """
    Parses and standardizes report_type string into ReportType enum.
    """
    if raw_val is None:
        return ReportType.near_miss

    val_str = str(raw_val).strip()
    val_clean = normalize_header(val_str)
    val_alpha = canonical_alphanumeric(val_str)

    # Check direct match with enum values
    for r in ReportType:
        if r.value.lower() == val_str.lower() or r.value.lower() == val_clean:
            return r

    # Alias mappings for safety terminology
    if val_alpha in ["ua", "unsafeact", "unsafeaction", "unsafeobservation"]:
        return ReportType.UA
    if val_alpha in ["uc", "unsafecondition", "unsafesituation", "hazard", "hazardouscondition"]:
        return ReportType.UC
    if val_alpha in ["nearmiss", "closecall", "nm"]:
        return ReportType.near_miss
    if val_alpha in ["incident", "accident", "recordable", "injury", "firstaid", "lti"]:
        return ReportType.incident

    return ReportType.near_miss


def normalize_sif_ground_truth(val: Any) -> Optional[str]:
    """
    Standardizes ground truth SIF label to 'sif_potential' or 'non_sif'.
    """
    if val is None or pd.isna(val):
        return None
    val_clean = normalize_header(str(val))
    val_alpha = canonical_alphanumeric(str(val))

    if val_alpha in [
        "sifpotential",
        "sif",
        "potentialsif",
        "yes",
        "true",
        "1",
        "high",
        "critical",
        "fatalpotential",
        "sifp",
    ]:
        return "sif_potential"
    if val_alpha in [
        "nonsif",
        "no",
        "false",
        "0",
        "low",
        "medium",
        "nonpotential",
        "negligible",
        "none",
    ]:
        return "non_sif"

    return val_clean if val_clean else None


def normalize_split_name(val: Any) -> Optional[str]:
    """
    Standardizes dataset split to 'train', 'test', or 'val'.
    """
    if val is None or pd.isna(val):
        return None
    val_alpha = canonical_alphanumeric(str(val))
    if val_alpha in ["train", "training", "trn", "fit"]:
        return "train"
    if val_alpha in ["test", "testing", "tst", "holdout"]:
        return "test"
    if val_alpha in ["val", "validation", "valid", "dev", "eval"]:
        return "val"
    return str(val).strip().lower()


def parse_submitted_date(raw_val: Any) -> datetime:
    """
    Parses various date/datetime representations into UTC datetime.
    """
    if raw_val is None or pd.isna(raw_val):
        return datetime.now(timezone.utc)

    if isinstance(raw_val, datetime):
        if raw_val.tzinfo is None:
            return raw_val.replace(tzinfo=timezone.utc)
        return raw_val

    if isinstance(raw_val, date):
        return datetime.combine(raw_val, datetime.min.time(), tzinfo=timezone.utc)

    val_str = str(raw_val).strip()
    if not val_str or val_str.lower() in ["nan", "none", "nat", "null"]:
        return datetime.now(timezone.utc)

    try:
        parsed = pd.to_datetime(val_str)
        if pd.isna(parsed):
            return datetime.now(timezone.utc)
        dt = parsed.to_pydatetime()
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


def sanitize_meta_value(val: Any) -> Any:
    """
    Ensures metadata values are JSON serializable.
    """
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, (int, float, str, bool)):
        if isinstance(val, float) and (pd.isna(val) or val != val):
            return None
        return val
    return str(val)


# ==============================================================================
# 2. Core Spreadsheet Parser & Validator
# ==============================================================================

def read_spreadsheet_dataframe(file_content: bytes, filename: str, nrows: Optional[int] = None) -> pd.DataFrame:
    """
    Reads CSV or Excel file content into a pandas DataFrame using header row 0.
    Handles multiple encodings for CSV and optional nrows limitation.
    """
    ext = filename.lower().split(".")[-1] if "." in filename else ""

    if ext in ["xlsx", "xls"]:
        return pd.read_excel(io.BytesIO(file_content), header=0, nrows=nrows)

    # For CSV: try utf-8-sig first (handles BOM), then utf-8, then latin1
    for enc in ["utf-8-sig", "utf-8", "latin1", "cp1252"]:
        try:
            return pd.read_csv(io.BytesIO(file_content), header=0, encoding=enc, nrows=nrows)
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue

    # Fallback with error replacement
    return pd.read_csv(io.BytesIO(file_content), header=0, encoding="utf-8", errors="replace", nrows=nrows)


def preview_spreadsheet_mapping(
    file_content: bytes,
    filename: str,
    saved_template_mapping: Optional[Dict[str, str]] = None,
    saved_template_name: Optional[str] = None,
) -> BulkPreviewResponse:
    """
    Parses headers and first 5 data rows of a spreadsheet, computes column fingerprint,
    auto-suggests column mappings using alias rules or saved template, and returns
    preview payload for user confirmation before full ingestion.
    """
    df_preview = read_spreadsheet_dataframe(file_content, filename, nrows=5)
    actual_columns = [str(c).strip() for c in df_preview.columns if str(c).strip()]

    if not actual_columns:
        raise ValueError("The uploaded spreadsheet contains no column headers.")

    fingerprint = compute_column_fingerprint(actual_columns)

    # 1. Match columns (prioritizing saved template if available)
    if saved_template_mapping:
        mapped_targets, _ = match_column_headers(actual_columns, custom_mapping=saved_template_mapping)
        is_saved = True
    else:
        mapped_targets, _ = match_column_headers(actual_columns)
        is_saved = False

    # 2. Build lookups
    detected_to_target: Dict[str, Optional[str]] = {}
    target_to_column: Dict[str, Optional[str]] = {target: mapped_targets.get(target) for target in TARGET_ORDER}
    confidence_map: Dict[str, str] = {}

    reverse_map = {col: target for target, col in mapped_targets.items()}

    for col in actual_columns:
        target = reverse_map.get(col)
        detected_to_target[col] = target

        if is_saved and target:
            confidence_map[col] = "saved_template"
        elif target:
            norm_col = normalize_header(col)
            aliases = [normalize_header(a) for a in COLUMN_ALIASES.get(target, [])]
            if norm_col in aliases or norm_col == target:
                confidence_map[col] = "high"
            else:
                confidence_map[col] = "medium"
        else:
            confidence_map[col] = "unmapped"

    all_required_matched = all(target_to_column.get(req) is not None for req in REQUIRED_TARGET_FIELDS)

    # Sample rows formatting
    sample_records = []
    for _, row in df_preview.head(5).iterrows():
        clean_row = {}
        for col in actual_columns:
            val = row.get(col)
            clean_row[col] = sanitize_meta_value(val)
        sample_records.append(clean_row)

    available_targets = [
        TargetFieldDefinition(
            key=defn["key"],
            label=defn["label"],
            required=defn["required"],
            description=defn["description"],
        )
        for defn in TARGET_FIELD_DEFINITIONS
    ]

    return BulkPreviewResponse(
        filename=filename,
        fingerprint=fingerprint,
        total_preview_rows=len(df_preview),
        detected_columns=actual_columns,
        suggested_mappings=detected_to_target,
        target_to_column=target_to_column,
        mapping_confidence=confidence_map,
        all_required_matched=all_required_matched,
        matched_template_name=saved_template_name if is_saved else None,
        sample_rows=sample_records,
        available_target_fields=available_targets,
    )


def parse_and_validate_bulk_records(
    df: pd.DataFrame,
    existing_sites_by_id: Set[int],
    site_names_map: Dict[str, int],
    default_user_id: int = 1,
    batch_id: Optional[str] = None,
    batch_label: Optional[str] = None,
    custom_mapping: Optional[Dict[str, str]] = None,
) -> Tuple[List[Report], BulkUploadSummaryResponse]:
    """
    Validates and transforms a parsed DataFrame into Report model instances:
    1. Validates column headers and verifies required fields are present (supporting custom_mapping).
    2. Detects and extracts ground-truth evaluation columns.
    3. Validates each row (raw_text >= 10 chars, site exists).
    4. Preserves extra columns in raw_metadata.
    5. Tags batch_id and batch_label for benchmarking.
    6. Aggregates rejections into grouped categories with max 20 example snippets.
    """
    # 1. Clean column names
    actual_columns = [str(c).strip() for c in df.columns if str(c).strip()]
    if not actual_columns:
        raise ValueError("The uploaded spreadsheet contains no column headers.")

    mapped_targets, extra_columns = match_column_headers(actual_columns, custom_mapping=custom_mapping)

    # 2. Check for missing required columns (fail-fast)
    missing_required = [req for req in REQUIRED_TARGET_FIELDS if req not in mapped_targets]
    if missing_required:
        detected_list = ", ".join(f"'{c}'" for c in actual_columns)
        missing_list = ", ".join(f"'{m}'" for m in missing_required)
        raise ValueError(
            f"Missing required column(s): {missing_list}. "
            f"Detected columns: [{detected_list}]. "
            f"Required target fields are: raw_text, report_type, site_id, activity."
        )

    col_raw_text = mapped_targets["raw_text"]
    col_report_type = mapped_targets["report_type"]
    col_site_id = mapped_targets["site_id"]
    col_activity = mapped_targets["activity"]
    col_date = mapped_targets.get("submitted_at")

    # Optional Ground Truth Columns
    col_gt_sif = mapped_targets.get("ground_truth_sif_label")
    col_gt_lsr = mapped_targets.get("ground_truth_lsr")
    col_gt_barrier = mapped_targets.get("ground_truth_barrier_status")
    col_gt_split = mapped_targets.get("ground_truth_split")

    effective_batch_id = batch_id or f"batch_{uuid.uuid4().hex[:8]}"
    effective_batch_label = batch_label or f"Batch {effective_batch_id} ({datetime.now().strftime('%Y-%m-%d %H:%M')})"

    reports_to_insert: List[Report] = []
    rejection_groups: Dict[str, Dict[str, Any]] = {}
    flat_errors: List[BulkUploadRowError] = []
    ground_truth_count = 0

    total_rows = len(df)

    # 3. Process row-by-row
    for idx, row in df.iterrows():
        row_num = idx + 2  # 1-indexed header is row 1, data starts at row 2

        # Extract full row dict for snippet preservation
        raw_row_data = {}
        for col in actual_columns:
            val = row.get(col)
            if not pd.isna(val):
                raw_row_data[col] = sanitize_meta_value(val)

        def record_rejection(reason_msg: str):
            if reason_msg not in rejection_groups:
                rejection_groups[reason_msg] = {"reason": reason_msg, "count": 0, "examples": []}
            rejection_groups[reason_msg]["count"] += 1
            if len(rejection_groups[reason_msg]["examples"]) < 20:
                rejection_groups[reason_msg]["examples"].append({
                    "row": row_num,
                    "data": raw_row_data,
                })
            # Also keep in flat errors for backward compatibility
            flat_errors.append(BulkUploadRowError(row=row_num, reason=reason_msg, data=raw_row_data))

        # Check raw_text
        raw_text_val = row.get(col_raw_text)
        if raw_text_val is None or pd.isna(raw_text_val):
            record_rejection("Missing or too short 'raw_text' (must be at least 10 characters)")
            continue

        raw_text = str(raw_text_val).strip()
        if len(raw_text) < 10 or raw_text.lower() in ["nan", "none", "null", "n/a"]:
            record_rejection("Missing or too short 'raw_text' (must be at least 10 characters)")
            continue

        # Match site_id
        site_val = row.get(col_site_id)
        resolved_site_id: Optional[int] = None

        if site_val is not None and not pd.isna(site_val):
            # Try integer ID match
            try:
                numeric_site = int(float(str(site_val).strip()))
                if numeric_site in existing_sites_by_id:
                    resolved_site_id = numeric_site
            except (ValueError, TypeError):
                pass

            # Try name match
            if resolved_site_id is None:
                clean_name = normalize_header(str(site_val))
                alpha_name = canonical_alphanumeric(str(site_val))
                if clean_name in site_names_map:
                    resolved_site_id = site_names_map[clean_name]
                elif alpha_name in site_names_map:
                    resolved_site_id = site_names_map[alpha_name]
                else:
                    # Partial match on site name
                    for s_name, s_id in site_names_map.items():
                        if s_name and (s_name in clean_name or clean_name in s_name):
                            resolved_site_id = s_id
                            break

        if resolved_site_id is None:
            # Fallback if no sites exist in database (e.g. testing)
            if not existing_sites_by_id and not site_names_map:
                resolved_site_id = 1
            else:
                site_display = str(site_val).strip() if site_val is not None and not pd.isna(site_val) else "empty"
                record_rejection(f"Site '{site_display}' not found in database")
                continue

        # Parse report_type
        report_type = parse_report_type(row.get(col_report_type))

        # Parse activity
        act_val = row.get(col_activity)
        if act_val is None or pd.isna(act_val) or not str(act_val).strip():
            activity = "General Operations"
        else:
            activity = str(act_val).strip()

        # Parse date
        submitted_at = parse_submitted_date(row.get(col_date) if col_date else None)

        # Extract Ground Truth annotations if present
        gt_sif_label: Optional[str] = None
        if col_gt_sif:
            gt_sif_label = normalize_sif_ground_truth(row.get(col_gt_sif))

        gt_lsr: Optional[str] = None
        if col_gt_lsr:
            raw_gt_lsr = row.get(col_gt_lsr)
            if raw_gt_lsr is not None and not pd.isna(raw_gt_lsr):
                gt_lsr = str(raw_gt_lsr).strip()

        gt_barrier_status: Optional[str] = None
        if col_gt_barrier:
            raw_gt_b = row.get(col_gt_barrier)
            if raw_gt_b is not None and not pd.isna(raw_gt_b):
                gt_barrier_status = str(raw_gt_b).strip()

        gt_split: Optional[str] = None
        if col_gt_split:
            gt_split = normalize_split_name(row.get(col_gt_split))

        if gt_sif_label or gt_lsr or gt_barrier_status:
            ground_truth_count += 1

        # Build raw_metadata preserving extra columns
        raw_metadata: Dict[str, Any] = {}
        for extra_col in extra_columns:
            extra_val = row.get(extra_col)
            if not pd.isna(extra_val):
                clean_val = sanitize_meta_value(extra_val)
                if clean_val is not None:
                    raw_metadata[extra_col] = clean_val

        # Create Report model
        report = Report(
            report_type=report_type,
            raw_text=raw_text,
            submitted_by=default_user_id,
            site_id=resolved_site_id,
            activity=activity,
            language="en",
            submitted_at=submitted_at,
            status=ReportStatus.pending_review,
            raw_metadata=raw_metadata if raw_metadata else None,
            upload_batch_id=effective_batch_id,
            upload_batch_label=effective_batch_label,
            ground_truth_sif_label=gt_sif_label,
            ground_truth_lsr=gt_lsr,
            ground_truth_barrier_status=gt_barrier_status,
            ground_truth_split=gt_split,
        )
        reports_to_insert.append(report)

    # 4. Build summary
    rejection_breakdown = [
        BulkUploadErrorGroup(
            reason=info["reason"],
            count=info["count"],
            examples=info["examples"],
        )
        for info in rejection_groups.values()
    ]

    has_gt = ground_truth_count > 0

    # Aggregate distribution counts across accepted reports
    report_type_counts: Dict[str, int] = defaultdict(int)
    ground_truth_sif_counts: Dict[str, int] = defaultdict(int)
    sif_label_counts: Dict[str, int] = defaultdict(int)

    for r in reports_to_insert:
        r_type_key = r.report_type.value if hasattr(r.report_type, "value") else str(r.report_type)
        report_type_counts[r_type_key] += 1

        if r.ground_truth_sif_label:
            ground_truth_sif_counts[r.ground_truth_sif_label] += 1
        elif r.sif_label:
            s_label_key = r.sif_label.value if hasattr(r.sif_label, "value") else str(r.sif_label)
            sif_label_counts[s_label_key] += 1
        else:
            sif_label_counts["pending_review"] += 1

    summary = BulkUploadSummaryResponse(
        total_rows=total_rows,
        accepted_count=len(reports_to_insert),
        rejected_count=len(flat_errors),
        accepted_report_ids=[],
        upload_batch_id=effective_batch_id,
        upload_batch_label=effective_batch_label,
        has_ground_truth=has_gt,
        ground_truth_count=ground_truth_count,
        accuracy_report_url=f"/api/datasets/{effective_batch_id}/accuracy-report" if has_gt else None,
        download_csv_url=f"/api/datasets/{effective_batch_id}/export-csv",
        report_type_counts=dict(report_type_counts),
        sif_label_counts=dict(sif_label_counts),
        ground_truth_sif_counts=dict(ground_truth_sif_counts),
        rejection_breakdown=rejection_breakdown,
        errors=flat_errors,
    )

    return reports_to_insert, summary
