"""
SIF Sentinel AI - IOGP Life-Saving Rules (LSR) Multi-Label Tagger
SIH 2026 Problem Statement PS 26165 (Oil India Limited)

Multi-label classifier tagging safety reports against the 9 IOGP Life-Saving Rules:
1. Bypassing Safety Controls
2. Confined Space Entry
3. Driving
4. Energy Isolation
5. Hot Work
6. Line of Fire
7. Safe Mechanical Lifting
8. Work Authorisation
9. Working at Height

Uses:
- Curated trigger phrases and spaCy PhraseMatcher
- Semantic cosine similarity against canonical IOGP rule descriptions (384-dim embeddings)
- Assigns 1+ applicable rules with confidence per tag
- Stores results in report_lsr_tags table
- Updates report.primary_lsr for quick dashboard display
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import spacy
from spacy.matcher import PhraseMatcher
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.ml.sif_classifier import embedder
from app.models.entities import Report, ReportLSRTag

logger = logging.getLogger("sif_sentinel.lsr_tagger")


# ==============================================================================
# 1. 9 IOGP Life-Saving Rules Definitions & Canonical Descriptions
# ==============================================================================

IOGP_LSR_RULES: Dict[str, Dict[str, Any]] = {
    "Bypassing Safety Controls": {
        "canonical": "Obtain authorization before overriding or disabling safety-critical equipment, emergency shutdown ESD systems, interlocks, or fire and gas detectors.",
        "triggers": [
            "bypassing safety controls", "bypassed safety controls", "safety controls bypassed",
            "jumpered esd", "interlock bypassed", "interlock jumpered", "detector muted",
            "alarm inhibited", "override switch", "trip switch wedged", "safety device disabled",
            "relief valve gagged", "tampered interlock", "alarm bypassed", "flame detector masked",
        ],
    },
    "Confined Space Entry": {
        "canonical": "Confirm energy sources are isolated, gas testing is completed with calibrated detector, and a dedicated standby attendant is stationed at the confined space entrance.",
        "triggers": [
            "confined space entry", "entered confined space", "confined space without permit",
            "mud tank entry", "mud tank", "tank manway", "vessel entry", "toxic vapor",
            "h2s pocket", "atmospheric testing missing", "standby attendant missing",
            "oxygen deficient", "sludge cleaning tank", "separator vessel cleaning",
            "inside storage vessel",
        ],
    },
    "Driving": {
        "canonical": "Wear seatbelts, adhere to speed limits, do not use mobile phones while driving, verify journey management plans and vehicle spark arrestors in operating zones.",
        "triggers": [
            "near miss with vehicle", "vehicle near miss", "tanker rollover", "bowser speeding",
            "speeding on bund road", "spark arrestor open", "rusted spark arrestor",
            "unbelted driver", "head-on collision", "distracted driving", "brake failure tanker",
            "road shoulder collapse", "overspeeding tanker", "heavy transport rollover",
        ],
    },
    "Energy Isolation": {
        "canonical": "Verify zero energy state and isolate all hazardous mechanical, electrical, pneumatic, and pressurized fluid energy sources using verified Lockout/Tagout LOTO padlocks.",
        "triggers": [
            "energy isolation", "energy not isolated", "not isolated", "loto bypassed",
            "loto padlock", "lockout tagout", "lockout", "tagout", "live bus",
            "live conductor", "stored energy", "residual pressure", "hydraulic accumulator",
            "blind flange missing", "isolated electrical", "bleed valve not opened",
            "415v mcc", "mcc panel", "energized busbar", "spectacle blind open",
        ],
    },
    "Hot Work": {
        "canonical": "Control flammables and ignition sources, verify continuous combustible gas LEL atmospheric monitoring, and install fire containment blankets prior to welding or grinding.",
        "triggers": [
            "hot work", "hot work without permit", "spark near gas", "grinding near drain",
            "welding near separator", "slag near cellar", "open flame near wellhead",
            "flammable vapor ignited", "unprotected welding sparks", "hot work clearance",
            "angle grinding in gas zone", "fire blanket missing", "continuous lel",
            "skimmer pit welding",
        ],
    },
    "Line of Fire": {
        "canonical": "Position yourself clear of moving machinery, pressurized lines, snapback zones, swinging objects, and high-pressure discharge lines.",
        "triggers": [
            "line of fire", "stood inside rotary tongs", "snub line bite zone",
            "snapback zone", "whip check disconnected", "high pressure hose whip",
            "chiksan line", "swung within reach", "chiseled projectile",
            "hydrotest barricade breach", "struck by falling", "crush point",
            "rotary table nip point", "cathead line",
        ],
    },
    "Safe Mechanical Lifting": {
        "canonical": "Plan and execute lifts within certified equipment capacities, establish barricaded load exclusion zones, and never stand or walk beneath a suspended load.",
        "triggers": [
            "safe mechanical lifting", "mechanical lifting", "worked under suspended load",
            "under suspended load", "suspended load", "crane wire snapped", "birdcaging",
            "crane boom buckled", "crane outrigger sinking", "dropped object lift",
            "rigging failed", "sling snapped", "unrated lifting shackle", "no tagline used",
            "hydra crane", "bop stack lift", "crane hoist rope",
        ],
    },
    "Work Authorisation": {
        "canonical": "Confirm that a valid Permit to Work (PTW) is authorized, job safety analysis is completed, and safety controls are in place before starting work.",
        "triggers": [
            "work authorisation", "work authorization", "permit to work", "ptw",
            "ptw closed out prematurely", "cold work permit for hot work", "unauthorized work",
            "no permit to work", "simops conflict", "toolbox talk omitted",
            "unapproved modification", "permit expired", "unauthorized contractor",
        ],
    },
    "Working at Height": {
        "canonical": "Use 100% fall protection and tie-off with certified harness, lanyards, and lifelines when working at height, and secure tools with lanyards against dropped object hazards.",
        "triggers": [
            "working at height", "work at height", "fall from height", "unhooked harness",
            "detached lanyard", "monkey board unlatched", "monkey board", "derrickman",
            "90ft mast", "scaffold collapsed", "missing guardrail", "no fall arrest",
            "loose toe board", "dropped wrench from derrick", "open floor hatch",
            "self-retracting lifeline",
        ],
    },
}


# ==============================================================================
# 2. spaCy PhraseMatcher & Canonical Embedding Setup
# ==============================================================================

try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = spacy.blank("en")

lsr_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
for rule_name, rule_data in IOGP_LSR_RULES.items():
    docs = [nlp.make_doc(phrase) for phrase in rule_data["triggers"]]
    lsr_matcher.add(rule_name, docs)

# Precompute Canonical Embeddings for the 9 IOGP rules
CANONICAL_LSR_EMBEDDINGS: Dict[str, np.ndarray] = {
    rule_name: embedder.embed_text(rule_data["canonical"])
    for rule_name, rule_data in IOGP_LSR_RULES.items()
}


# ==============================================================================
# 3. Multi-Label Tagging Logic
# ==============================================================================

def tag_text(
    raw_text: str,
    activity: str = "",
    report_embedding: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Multi-label tags text against the 9 IOGP Life-Saving Rules using:
    1. spaCy PhraseMatcher on curated trigger phrases
    2. Semantic cosine similarity against canonical rule descriptions
    3. Multi-tag confidence scoring and primary_lsr resolution
    """
    combined_text = f"{activity} {raw_text}".strip()
    text_lower = combined_text.lower()
    doc = nlp(combined_text)

    # 1. Rule / Phrase Matching
    matches = lsr_matcher(doc)
    rule_hit_counts: Dict[str, int] = {r: 0 for r in IOGP_LSR_RULES}
    for match_id, start, end in matches:
        rule_name = nlp.vocab.strings[match_id]
        rule_hit_counts[rule_name] += 1

    # Supplementary keyword check
    for rule_name, rule_data in IOGP_LSR_RULES.items():
        for trigger in rule_data["triggers"]:
            if trigger in text_lower and rule_hit_counts[rule_name] == 0:
                rule_hit_counts[rule_name] += 1

    # 2. Semantic Embedding & Cosine Similarity
    if report_embedding is None:
        emb = embedder.embed_text(combined_text)
    else:
        emb = np.array(report_embedding, dtype=np.float32)
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb /= norm

    semantic_sims: Dict[str, float] = {}
    for rule_name, canonical_emb in CANONICAL_LSR_EMBEDDINGS.items():
        sim = float(np.dot(emb, canonical_emb))
        semantic_sims[rule_name] = max(0.0, min(1.0, sim))

    # 3. Compute Multi-Tag Confidences
    assigned_tags: List[Dict[str, Any]] = []

    for rule_name in IOGP_LSR_RULES:
        hits = rule_hit_counts[rule_name]
        sem_sim = semantic_sims[rule_name]

        if hits > 0:
            # Direct phrase trigger match (strong signal 0.75+)
            base_score = 0.72 + min(hits * 0.08, 0.22)
            tag_conf = round(min(base_score + (0.10 * sem_sim), 0.99), 2)
            assigned_tags.append({
                "lsr_rule": rule_name,
                "confidence": tag_conf,
                "match_type": "phrase_and_semantic",
                "hits": hits,
            })
        elif sem_sim >= 0.55:
            # Semantic fallback tag
            tag_conf = round(sem_sim, 2)
            assigned_tags.append({
                "lsr_rule": rule_name,
                "confidence": tag_conf,
                "match_type": "semantic_fallback",
                "hits": 0,
            })

    # Sort tags descending by confidence
    assigned_tags.sort(key=lambda x: x["confidence"], reverse=True)

    # Resolve Primary LSR
    primary_lsr = assigned_tags[0]["lsr_rule"] if assigned_tags and assigned_tags[0]["confidence"] >= 0.45 else None

    # Filter output tags
    clean_tags = [
        {"lsr_rule": t["lsr_rule"], "confidence": t["confidence"]}
        for t in assigned_tags if t["confidence"] >= 0.40
    ]

    return {
        "primary_lsr": primary_lsr,
        "tags": clean_tags,
        "total_tags": len(clean_tags),
    }


# ==============================================================================
# 4. Async Pipeline Task: tag_report(report_id)
# ==============================================================================

async def tag_report(report_id: int) -> Optional[Dict[str, Any]]:
    """
    Executes multi-label LSR tagging for a report in the background:
    1. Loads Report from DB
    2. Runs tag_text()
    3. Persists assigned tags in report_lsr_tags table
    4. Updates report.primary_lsr
    5. Returns result dict with primary_lsr and tags list
    """
    async with AsyncSessionLocal() as db:
        try:
            stmt = select(Report).where(Report.id == report_id)
            result = await db.execute(stmt)
            report = result.scalar_one_or_none()

            if not report:
                logger.warning(f"Report ID {report_id} not found for LSR tagging.")
                return None

            # Execute Tagging
            tagging_result = tag_text(
                raw_text=report.raw_text,
                activity=report.activity,
                report_embedding=report.embedding,
            )

            primary_lsr = tagging_result["primary_lsr"]
            tags = tagging_result["tags"]

            # Update report primary_lsr
            report.primary_lsr = primary_lsr

            # Clean existing LSR tags for this report to prevent duplicates
            await db.execute(delete(ReportLSRTag).where(ReportLSRTag.report_id == report.id))

            # Insert new LSR tags
            for tag_data in tags:
                lsr_tag = ReportLSRTag(
                    report_id=report.id,
                    lsr_rule=tag_data["lsr_rule"],
                    confidence=tag_data["confidence"],
                )
                db.add(lsr_tag)

            await db.commit()
            logger.info(
                f"LSR Tagging complete for Report {report_id}: "
                f"primary_lsr='{primary_lsr}', total_tags={len(tags)}"
            )

            return tagging_result

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in LSR tagging for Report {report_id}: {str(e)}", exc_info=True)
            return None
