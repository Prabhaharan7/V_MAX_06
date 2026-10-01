"""
SIF Sentinel AI - Safety Barrier Failure Extractor
Smart India Hackathon 2026 (Problem Statement PS 26165 - Oil India Limited)

Extracts failed administrative and physical safety barriers from unstructured field reports
using the 10-category Oil & Gas Safety Barrier Taxonomy:
1. PPE Non-Compliance
2. Isolation Not Verified
3. Permit Not Checked/Invalid
4. Guarding Removed/Bypassed
5. Communication Breakdown
6. Procedure Not Followed
7. Supervision Gap
8. Equipment Failure
9. Fatigue/Human Factors
10. Housekeeping

Methodology:
- spaCy dependency parsing (negation detection, verb-object pairs, prepositional dependency subtrees)
- Curated domain trigger phrase matching (Oil India upstream terminology)
- Contextual evidence phrase extraction (capturing the precise clause/subphrase that triggered the match)
- Severity scoring (low / medium / high) tied to high-energy fatal hazards and IOGP Life-Saving Rules (LSR)
- Database persistence to barrier_failures table
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.entities import BarrierFailure, BarrierSeverity, Report, SIFLabel

logger = logging.getLogger("sif_sentinel.barrier_extractor")

# Initialize spaCy NLP pipeline
try:
    import spacy
    from spacy.matcher import PhraseMatcher
    try:
        nlp = spacy.load("en_core_web_sm")
    except Exception:
        nlp = spacy.blank("en")
except ImportError:
    spacy = None
    PhraseMatcher = None
    nlp = None


# ==============================================================================
# 1. 10-Category Safety Barrier Taxonomy & Domain Triggers
# ==============================================================================

BARRIER_TAXONOMY: List[str] = [
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

BARRIER_PATTERNS: Dict[str, Dict[str, Any]] = {
    "PPE Non-Compliance": {
        "triggers": [
            "no safety harness", "unhooked harness", "without harness", "missing harness",
            "detached lanyard", "no fall arrest", "lanyard unclipped", "without safety glasses",
            "missing face shield", "no ear protection", "gloves missing", "not wearing ppe",
            "ppe non-compliance", "hard hat not worn", "harness detached", "respirator not used",
            "without rubber boots", "missing life jacket", "did not wear safety glasses",
            "no safety glasses", "missing ppe", "refused to wear ppe", "damaged hard hat",
            "without chemical gloves", "eye protection missing", "no safety helmet",
        ],
        "verbs": ["wear", "use", "don", "clip", "hook", "attach"],
        "objects": ["ppe", "harness", "lanyard", "helmet", "glasses", "goggles", "shield", "gloves", "respirator"],
        "default_severity": BarrierSeverity.medium,
        "high_hazard_keywords": ["height", "fall", "derrick", "monkey board", "toxic", "h2s", "chemical", "acid", "415v", "live"],
    },
    "Isolation Not Verified": {
        "triggers": [
            "isolation not verified", "not isolated", "loto bypassed", "lockout tagout not done",
            "lockout tagout bypassed", "no loto", "without isolation", "residual pressure not bled",
            "blind flange not installed", "live conductor", "energized line", "valve not closed",
            "zero energy not confirmed", "electrical drive not isolated", "hydraulic pressure not discharged",
            "lockout tagout", "loto padlock", "live busbar", "stored energy", "hydraulic accumulator",
            "bleed valve closed", "bleed valve not opened", "spectacle blind open", "isolated electrical",
            "energy not isolated", "without loto", "no padlock", "bypassed lockout",
        ],
        "verbs": ["isolate", "lockout", "tagout", "bleed", "depressurize", "de-energize", "discharge"],
        "objects": ["energy", "loto", "power", "pressure", "valve", "breaker", "switch", "voltage", "hydraulic", "padlock"],
        "default_severity": BarrierSeverity.high,
        "high_hazard_keywords": ["415v", "electrical", "high pressure", "hydraulic", "steam", "gas", "toxic", "flange", "live"],
    },
    "Permit Not Checked/Invalid": {
        "triggers": [
            "permit not checked", "invalid permit", "permit expired", "without permit to work",
            "no ptw", "hot work without permit", "confined space without permit", "unauthorized work",
            "permit not signed", "work permit missing", "no clearance certificate", "unauthorized entry without permit",
            "without valid permit", "ptw expired", "permit missing", "no hot work permit",
            "no lifting permit", "without permit", "permit revoked", "unauthorized maintenance",
            "cold work permit missing", "gas test certificate missing", "no entry permit",
        ],
        "verbs": ["check", "obtain", "sign", "issue", "verify", "validate", "renew"],
        "objects": ["permit", "ptw", "clearance", "certificate", "authorization", "form"],
        "default_severity": BarrierSeverity.high,
        "high_hazard_keywords": ["hot work", "confined space", "lifting", "crane", "high voltage", "explosive", "gas"],
    },
    "Guarding Removed/Bypassed": {
        "triggers": [
            "guarding removed", "machine guard bypassed", "safety guard missing", "coupling guard off",
            "belt guard removed", "interlock bypassed", "safety switch jumpered", "tampered interlock",
            "grating removed without barricade", "open hole unguarded", "derrick safety gate open",
            "rotary table guard off", "relief valve gagged", "guard removed", "open machinery",
            "missing barrier", "safety railing missing", "interlock jumpered", "esd bypassed",
            "alarm inhibited", "detector muted", "interlock bridged", "guard disabled", "protective guard detached",
        ],
        "verbs": ["guard", "bypass", "remove", "jumper", "tamper", "override", "disable", "bridge"],
        "objects": ["guard", "barrier", "grating", "interlock", "railing", "switch", "sensor", "gate", "esd", "cover"],
        "default_severity": BarrierSeverity.high,
        "high_hazard_keywords": ["rotary", "engine", "belt", "pulley", "winch", "coupling", "gear", "shaft", "flywheel", "high pressure"],
    },
    "Communication Breakdown": {
        "triggers": [
            "communication breakdown", "miscommunication", "control room not informed", "no radio communication",
            "hand signals misunderstood", "shift handover missed", "failed to notify supervisor", "no warning given",
            "uncoordinated start", "poor communication between driller and derrickman", "without notifying control room",
            "no prior notification", "radio dead zone", "misunderstanding of instructions", "no verbal confirmation",
            "unannounced startup", "without signaling", "signalman absent", "no horn sounded",
        ],
        "verbs": ["communicate", "notify", "inform", "warn", "signal", "radio", "handover", "confirm"],
        "objects": ["control room", "supervisor", "radio", "signal", "handover", "warning", "driller", "derrickman", "instruction"],
        "default_severity": BarrierSeverity.medium,
        "high_hazard_keywords": ["lifting", "crane", "drilling", "well control", "energized", "suspended", "blowout", "line of fire"],
    },
    "Procedure Not Followed": {
        "triggers": [
            "procedure not followed", "sop violated", "bypassed procedure", "deviation from standard procedure",
            "shortcut taken", "improper steps", "did not follow checklist", "ignored standing instructions",
            "failed to follow drilling procedure", "bypassed standard operating procedure", "non-standard method",
            "unapproved procedure", "unauthorized shortcut", "violated operating guidelines", "skipped procedural step",
            "did not consult sop", "contrary to safety manual", "improper procedure",
        ],
        "verbs": ["follow", "adhere", "comply", "execute", "observe", "apply"],
        "objects": ["procedure", "sop", "checklist", "guideline", "instruction", "standard", "manual", "protocol"],
        "default_severity": BarrierSeverity.medium,
        "high_hazard_keywords": ["well control", "casing", "tripping", "pressure test", "swabbing", "wireline", "explosive"],
    },
    "Supervision Gap": {
        "triggers": [
            "supervision gap", "no supervisor present", "unsupervised work", "lack of oversight",
            "standby attendant left post", "banksman missing", "signalman absent", "no hse oversight",
            "unsupervised apprentice", "supervisor failed to check", "lack of supervision", "unattended operation",
            "safety officer absent", "competent person missing", "unsupervised contractor",
        ],
        "verbs": ["supervise", "oversee", "attend", "monitor", "check", "inspect"],
        "objects": ["supervisor", "oversight", "attendant", "banksman", "signalman", "lead", "officer"],
        "default_severity": BarrierSeverity.medium,
        "high_hazard_keywords": ["confined space", "lifting", "critical", "derrick", "high pressure", "manway", "tank"],
    },
    "Equipment Failure": {
        "triggers": [
            "equipment failure", "sling snapped", "crane wire birdcaged", "hydraulic hose burst",
            "brake failure", "relief valve stuck", "sheave seized", "gas detector malfunction",
            "sensor failure", "pipe parted", "whip check snapped", "compressor seal blew",
            "pump leak", "flange leak", "valve cracked", "gauge broken", "instrument failure",
            "seal blowout", "o-ring ruptured", "cable frayed", "structural crack",
        ],
        "verbs": ["fail", "snap", "burst", "leak", "rupture", "break", "seize", "malfunction", "crack"],
        "objects": ["equipment", "sling", "hose", "valve", "wire", "pump", "seal", "sensor", "flange", "gauge", "cable", "whip check"],
        "default_severity": BarrierSeverity.high,
        "high_hazard_keywords": ["crane", "lifting", "high pressure", "gas", "toxic", "h2s", "blowout", "cathead", "winch"],
    },
    "Fatigue/Human Factors": {
        "triggers": [
            "fatigue", "human factor", "double shift fatigue", "extended shift",
            "drowsiness", "worked 18 hours", "operator fell asleep", "distracted operator",
            "exhaustion", "lack of rest", "heat stress exhaustion", "rushing before shift change",
            "complacency", "overworked crew", "long working hours", "sleep deprived", "heat exhaustion",
        ],
        "verbs": ["rest", "sleep", "rush", "focus", "concentrate", "fatigue"],
        "objects": ["shift", "hours", "fatigue", "exhaustion", "stress", "sleep", "rest"],
        "default_severity": BarrierSeverity.medium,
        "high_hazard_keywords": ["driving", "crane", "driller", "heavy equipment", "night shift", "vehicle", "derrick"],
    },
    "Housekeeping": {
        "triggers": [
            "housekeeping", "oil spill on deck", "grease on gangway", "tripping hazard",
            "cluttered pathway", "scrap metal in walkway", "uncoiled hoses", "scattered tools",
            "wet floor no sign", "poor housekeeping", "trash blocking exit", "spilled mud on rig floor",
            "mud accumulation", "debris in work area", "obstruction in emergency path", "slippery surface",
        ],
        "verbs": ["clean", "clear", "tidy", "remove", "store", "organize"],
        "objects": ["housekeeping", "spill", "hazard", "clutter", "debris", "pathway", "walkway", "deck", "floor", "tools"],
        "default_severity": BarrierSeverity.low,
        "high_hazard_keywords": ["fire", "emergency exit", "stairs", "rotary table", "cellar", "ignition"],
    },
}


# ==============================================================================
# 2. Matcher & Phrase Extraction Engine
# ==============================================================================

def _clean_evidence_phrase(text: str, match_span: str, sentence_context: Optional[str] = None) -> str:
    """
    Cleans and extracts a concise, high-signal evidence phrase (max ~140 chars)
    representing the exact barrier failure context.
    """
    if sentence_context:
        clean_ctx = " ".join(sentence_context.strip().split())
        if len(clean_ctx) <= 160:
            return clean_ctx
        # If sentence is long, center a window around the match
        idx = clean_ctx.lower().find(match_span.lower())
        if idx != -1:
            start = max(0, idx - 40)
            end = min(len(clean_ctx), idx + len(match_span) + 50)
            snippet = clean_ctx[start:end].strip()
            if start > 0:
                snippet = "..." + snippet
            if end < len(clean_ctx):
                snippet = snippet + "..."
            return snippet

    # Fallback to match span with word boundary formatting
    return match_span.strip()


def _extract_via_spacy_dependency(doc, barrier_category: str) -> List[Tuple[str, str]]:
    """
    Leverages spaCy token dependency parsing (negations, verb-object pairs,
    adpositional phrases) to detect subtle barrier failures and extract evidence subtrees.
    Returns: List of (matched_trigger, evidence_phrase)
    """
    findings = []
    config = BARRIER_PATTERNS.get(barrier_category, {})
    verbs = set(config.get("verbs", []))
    objects = set(config.get("objects", []))

    for token in doc:
        # Check 1: Verb with direct negation ("did not wear", "failed to isolate", "never inspected")
        is_negated = any(child.dep_ == "neg" or child.lemma_.lower() in ["no", "not", "without", "never", "fail"] for child in token.children)
        
        # Check verb lemma
        if token.lemma_.lower() in verbs or token.text.lower() in ["bypass", "skip", "ignore", "tamper", "break", "snap"]:
            # Inspect direct objects or prepositional objects
            for child in token.children:
                if child.lemma_.lower() in objects or child.text.lower() in objects:
                    # Construct subtree clause
                    subtree_tokens = [t.text for t in token.subtree]
                    phrase = " ".join(subtree_tokens)
                    if len(phrase) > 10:
                        findings.append((f"{token.text} {child.text}", phrase[:150]))

        # Check 2: Prepositional "without" phrases ("without permit", "without isolation", "without harness")
        if token.lemma_.lower() in ["without", "no", "lack"] and token.dep_ in ["prep", "det", "amod"]:
            for child in token.children:
                if child.lemma_.lower() in objects or child.text.lower() in objects:
                    # Extract surrounding phrase
                    span_tokens = [t.text for t in token.head.subtree] if hasattr(token, "head") else [token.text, child.text]
                    phrase = " ".join(span_tokens)
                    findings.append((f"{token.text} {child.text}", phrase[:150]))

    return findings


# ==============================================================================
# 3. Severity Assignment Engine
# ==============================================================================

def determine_barrier_severity(
    barrier_type: str,
    text: str,
    evidence_phrase: str,
    is_sif: Optional[bool] = None,
    primary_lsr: Optional[str] = None,
) -> BarrierSeverity:
    """
    Assigns a severity (low, medium, high) based on:
    1. Direct connection to SIF-precursor classification or Life-Saving Rule (LSR)
    2. High-energy fatal hazard keywords in proximity (415V, H2S, suspended load, fall, derrick)
    3. Baseline barrier category criticality
    """
    text_lower = (text + " " + evidence_phrase).lower()
    config = BARRIER_PATTERNS.get(barrier_type, {})
    high_keywords = config.get("high_hazard_keywords", [])
    default_sev = config.get("default_severity", BarrierSeverity.medium)

    # 1. Immediate High Severity Conditions:
    # Any life-critical barrier tied to an active SIF or high-energy hazard
    has_high_energy_signal = any(re.search(r"\b" + re.escape(kw) + r"\b", text_lower) for kw in high_keywords)

    if barrier_type in ["Isolation Not Verified", "Guarding Removed/Bypassed"]:
        # Mechanical/electrical/pressure barriers are inherently high severity
        return BarrierSeverity.high

    if barrier_type == "Permit Not Checked/Invalid":
        if has_high_energy_signal or is_sif or (primary_lsr and primary_lsr in ["Hot Work", "Confined Space Entry", "Safe Mechanical Lifting", "Energy Isolation"]):
            return BarrierSeverity.high
        return BarrierSeverity.medium

    if barrier_type == "PPE Non-Compliance":
        # Working at height harness failure or toxic gas respirator failure is High
        if any(w in text_lower for w in ["height", "fall", "derrick", "monkey board", "harness", "lanyard", "toxic", "h2s"]):
            return BarrierSeverity.high
        return BarrierSeverity.low if ("glasses" in text_lower or "gloves" in text_lower or "boots" in text_lower) else BarrierSeverity.medium

    if barrier_type == "Equipment Failure":
        if has_high_energy_signal or is_sif or any(w in text_lower for w in ["crane", "sling", "wire", "burst", "blowout", "high pressure", "gas leak"]):
            return BarrierSeverity.high
        return BarrierSeverity.medium

    if barrier_type == "Communication Breakdown":
        if has_high_energy_signal or is_sif or any(w in text_lower for w in ["crane", "lift", "drilling", "energized", "derrick"]):
            return BarrierSeverity.high
        return BarrierSeverity.medium

    if barrier_type == "Supervision Gap":
        if is_sif or any(w in text_lower for w in ["confined space", "tank entry", "critical lift", "derrick"]):
            return BarrierSeverity.high
        return BarrierSeverity.medium

    if barrier_type == "Fatigue/Human Factors":
        if is_sif or any(w in text_lower for w in ["crane", "heavy vehicle", "driller", "rig floor"]):
            return BarrierSeverity.high
        return BarrierSeverity.medium

    if barrier_type == "Housekeeping":
        if any(w in text_lower for w in ["flammable", "cellar fire", "ignition", "blocked emergency exit", "stairs fall"]):
            return BarrierSeverity.medium
        return BarrierSeverity.low

    if is_sif and default_sev == BarrierSeverity.medium:
        return BarrierSeverity.high

    return default_sev


# ==============================================================================
# 4. Core Extractor: extract_barriers_from_text()
# ==============================================================================

def extract_barriers_from_text(
    raw_text: str,
    activity: Optional[str] = None,
    is_sif: Optional[bool] = None,
    primary_lsr: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Analyzes safety report text and returns all identified failed barrier categories,
    the exact extracted evidence phrases, and calculated severity ratings.

    Returns:
        List of dicts:
        [
            {
                "barrier_type": "Isolation Not Verified",
                "evidence_phrase": "bypassed lockout tagout on discharge header electrical drive",
                "severity": BarrierSeverity.high,
                "confidence": 0.92
            },
            ...
        ]
    """
    if not raw_text or not raw_text.strip():
        return []

    combined_text = f"{activity or ''} {raw_text}".strip()
    text_lower = combined_text.lower()
    results: List[Dict[str, Any]] = []
    seen_barriers: Set[str] = set()

    # Process with spaCy if available
    doc = None
    if nlp is not None:
        try:
            doc = nlp(combined_text)
        except Exception as e:
            logger.debug(f"spaCy parsing failed, falling back to regex: {e}")

    # 1. Pattern & Keyword Trigger Matching per Barrier Category
    for barrier_name, config in BARRIER_PATTERNS.items():
        triggers = config.get("triggers", [])
        matched_trigger = None
        evidence = None

        # Search for domain trigger phrases
        for trigger in triggers:
            pattern = r"\b" + re.escape(trigger) + r"\b"
            match = re.search(pattern, text_lower)
            if match:
                matched_trigger = trigger
                sent_ctx = None
                try:
                    if doc and doc.has_annotation("SENT_START"):
                        for sent in doc.sents:
                            if trigger in sent.text.lower():
                                sent_ctx = sent.text
                                break
                except Exception:
                    pass

                if not sent_ctx and "." in combined_text:
                    for s in combined_text.split("."):
                        if trigger in s.lower():
                            sent_ctx = s.strip()
                            break

                evidence = _clean_evidence_phrase(combined_text, match.group(0), sent_ctx)
                break

        # Check spaCy dependency parsing if trigger match didn't catch or to augment evidence
        if doc and not matched_trigger:
            try:
                if doc.has_annotation("DEP"):
                    dep_findings = _extract_via_spacy_dependency(doc, barrier_name)
                    if dep_findings:
                        matched_trigger, evidence = dep_findings[0]
            except Exception:
                pass

        if matched_trigger and barrier_name not in seen_barriers:
            seen_barriers.add(barrier_name)
            severity = determine_barrier_severity(
                barrier_type=barrier_name,
                text=combined_text,
                evidence_phrase=evidence or matched_trigger,
                is_sif=is_sif,
                primary_lsr=primary_lsr,
            )
            results.append({
                "barrier_type": barrier_name,
                "evidence_phrase": evidence or matched_trigger,
                "severity": severity,
                "confidence": 0.88 if severity == BarrierSeverity.high else 0.80,
            })

    # Sort results by severity (high > medium > low)
    severity_order = {BarrierSeverity.high: 3, BarrierSeverity.medium: 2, BarrierSeverity.low: 1}
    results.sort(key=lambda x: severity_order.get(x["severity"], 0), reverse=True)

    return results


# ==============================================================================
# 5. Async Database Pipeline Task: extract_barriers_for_report(report_id)
# ==============================================================================

async def extract_barriers_for_report(report_id: int) -> Optional[List[Dict[str, Any]]]:
    """
    Background Task:
    1. Loads Report from database
    2. Runs extract_barriers_from_text()
    3. Deletes any stale barrier failure records for this report
    4. Writes newly extracted BarrierFailure records to the database
    5. Returns list of extracted barrier failure records
    """
    async with AsyncSessionLocal() as db:
        try:
            stmt = select(Report).where(Report.id == report_id)
            result = await db.execute(stmt)
            report = result.scalar_one_or_none()

            if not report:
                logger.warning(f"Report ID {report_id} not found for barrier extraction.")
                return None

            is_sif_potential = (report.sif_label == SIFLabel.sif_potential)
            extracted_barriers = extract_barriers_from_text(
                raw_text=report.raw_text,
                activity=report.activity,
                is_sif=is_sif_potential,
                primary_lsr=report.primary_lsr,
            )

            # Clear existing barrier failure entries for this report to prevent duplicates
            await db.execute(delete(BarrierFailure).where(BarrierFailure.report_id == report.id))

            # Persist newly extracted barrier failures
            for item in extracted_barriers:
                bf = BarrierFailure(
                    report_id=report.id,
                    barrier_type=item["barrier_type"],
                    evidence_phrase=item["evidence_phrase"],
                    severity=item["severity"],
                )
                db.add(bf)

            await db.commit()
            logger.info(
                f"Barrier Extraction complete for Report {report_id}: "
                f"Extracted {len(extracted_barriers)} failed barriers."
            )

            return extracted_barriers

        except Exception as e:
            await db.rollback()
            logger.error(f"Error extracting barriers for Report {report_id}: {str(e)}", exc_info=True)
            return None
