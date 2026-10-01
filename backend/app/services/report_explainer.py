"""
SIF Sentinel AI - Report Explanation Span Generator
Smart India Hackathon 2026 (Problem Statement PS 26165 - Oil India Limited)

Generates character-offset spans across raw safety observation text marking:
(a) Phrases that drove the SIF classification (rule-matcher triggers & severity amplifiers)
(b) Phrases that drove each IOGP Life-Saving Rule (LSR) tag
(c) Phrases that represent evidence for each safety barrier failure
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from app.ml.barrier_extractor import BARRIER_PATTERNS, extract_barriers_from_text
from app.ml.lsr_tagger import IOGP_LSR_RULES, tag_text
from app.ml.sif_classifier import HIGH_RISK_RULE_PATTERNS, SEVERITY_AMPLIFIERS
from app.models.entities import Report, BarrierSeverity
from app.schemas.safety_report import ExplanationSpan, ReportExplanationResponse


def _find_all_substring_spans(text: str, pattern: str) -> List[Tuple[int, int, str]]:
    """
    Finds all non-overlapping occurrences of pattern in text (case-insensitively),
    returning list of (start_idx, end_idx, matched_text).
    """
    spans = []
    if not text or not pattern:
        return spans

    # Try word-boundary regex first
    try:
        regex = re.compile(r"\b" + re.escape(pattern) + r"\b", re.IGNORECASE)
        for match in regex.finditer(text):
            spans.append((match.start(), match.end(), text[match.start():match.end()]))
    except Exception:
        pass

    # Fallback to literal case-insensitive search if regex missed
    if not spans:
        lower_text = text.lower()
        lower_pat = pattern.lower()
        start = 0
        while True:
            idx = lower_text.find(lower_pat, start)
            if idx == -1:
                break
            end = idx + len(pattern)
            spans.append((idx, end, text[idx:end]))
            start = end

    return spans


def generate_explanation_spans(report: Report) -> ReportExplanationResponse:
    """
    Computes explainable AI spans with 0-indexed character offsets over report.raw_text.
    Spans are structured with {start, end, type, label, confidence, matched_text}.
    """
    raw_text = report.raw_text or ""
    spans: List[ExplanationSpan] = []
    seen_spans: Set[Tuple[int, int, str, str]] = set()

    # --------------------------------------------------------------------------
    # (a) SIF Classification Rule-Matcher Hits
    # --------------------------------------------------------------------------
    sif_conf = report.sif_confidence or 0.85
    for category, patterns in HIGH_RISK_RULE_PATTERNS.items():
        for pat in patterns:
            matches = _find_all_substring_spans(raw_text, pat)
            for start, end, matched_text in matches:
                key = (start, end, "sif_precursor", category)
                if key not in seen_spans:
                    seen_spans.add(key)
                    spans.append(
                        ExplanationSpan(
                            start=start,
                            end=end,
                            type="sif_precursor",
                            label=category,
                            confidence=round(sif_conf, 2),
                            matched_text=matched_text,
                        )
                    )

    # Severity amplifiers (high energy modifiers)
    for amp in SEVERITY_AMPLIFIERS:
        matches = _find_all_substring_spans(raw_text, amp)
        for start, end, matched_text in matches:
            key = (start, end, "sif_precursor", f"High-Energy: {amp}")
            if key not in seen_spans:
                seen_spans.add(key)
                spans.append(
                    ExplanationSpan(
                        start=start,
                        end=end,
                        type="sif_precursor",
                        label=f"High-Energy: {amp}",
                        confidence=0.90,
                        matched_text=matched_text,
                    )
                )

    # --------------------------------------------------------------------------
    # (b) IOGP Life-Saving Rules (LSR) Tag Phrases
    # --------------------------------------------------------------------------
    tagged_rules: Dict[str, float] = {}
    if report.lsr_tags:
        for tag in report.lsr_tags:
            tagged_rules[tag.lsr_rule] = tag.confidence
    elif report.primary_lsr:
        tagged_rules[report.primary_lsr] = 0.85
    else:
        # On-the-fly tagging fallback if report had not yet been processed
        tagged_result = tag_text(raw_text=raw_text, activity=report.activity or "")
        for t in tagged_result.get("tags", []):
            tagged_rules[t["lsr_rule"]] = t["confidence"]

    for rule_name, confidence in tagged_rules.items():
        rule_data = IOGP_LSR_RULES.get(rule_name, {})
        triggers = rule_data.get("triggers", [])
        for trig in triggers:
            matches = _find_all_substring_spans(raw_text, trig)
            for start, end, matched_text in matches:
                key = (start, end, "lsr_tag", rule_name)
                if key not in seen_spans:
                    seen_spans.add(key)
                    spans.append(
                        ExplanationSpan(
                            start=start,
                            end=end,
                            type="lsr_tag",
                            label=rule_name,
                            confidence=round(confidence, 2),
                            matched_text=matched_text,
                        )
                    )

    # --------------------------------------------------------------------------
    # (c) Safety Barrier Failure Evidence Phrases
    # --------------------------------------------------------------------------
    barrier_list = report.barrier_failures or []
    if not barrier_list:
        # On-the-fly barrier extraction fallback
        barrier_list = extract_barriers_from_text(
            raw_text=raw_text,
            activity=report.activity,
            is_sif=(report.sif_label and report.sif_label.value == "sif_potential"),
            primary_lsr=report.primary_lsr,
        )

    for bf in barrier_list:
        # Handle both ORM entity and dict format
        if isinstance(bf, dict):
            b_type = bf.get("barrier_type", "")
            evidence = bf.get("evidence_phrase", "")
            b_sev = bf.get("severity", BarrierSeverity.medium)
        else:
            b_type = bf.barrier_type
            evidence = bf.evidence_phrase
            b_sev = bf.severity

        sev_conf = 0.95 if b_sev == BarrierSeverity.high or b_sev == "high" else 0.85

        # 1. Exact or partial evidence phrase match
        if evidence:
            matches = _find_all_substring_spans(raw_text, evidence)
            for start, end, matched_text in matches:
                key = (start, end, "barrier_failure", b_type)
                if key not in seen_spans:
                    seen_spans.add(key)
                    spans.append(
                        ExplanationSpan(
                            start=start,
                            end=end,
                            type="barrier_failure",
                            label=b_type,
                            confidence=sev_conf,
                            matched_text=matched_text,
                        )
                    )

        # 2. Match known trigger words for this barrier category
        triggers = BARRIER_PATTERNS.get(b_type, {}).get("triggers", [])
        for trig in triggers:
            matches = _find_all_substring_spans(raw_text, trig)
            for start, end, matched_text in matches:
                key = (start, end, "barrier_failure", b_type)
                if key not in seen_spans:
                    seen_spans.add(key)
                    spans.append(
                        ExplanationSpan(
                            start=start,
                            end=end,
                            type="barrier_failure",
                            label=b_type,
                            confidence=sev_conf,
                            matched_text=matched_text,
                        )
                    )

    # Sort spans by starting character offset, then by length descending
    spans.sort(key=lambda s: (s.start, -(s.end - s.start)))

    return ReportExplanationResponse(
        id=report.id,
        text=raw_text,
        spans=spans,
    )
