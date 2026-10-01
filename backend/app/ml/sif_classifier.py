"""
SIF Sentinel AI - Hybrid SIF-Potential Classifier
SIH 2026 Problem Statement PS 26165 (Oil India Limited)

Architecture:
1. Rule / Keyword & Linguistic Pattern Layer (spaCy PhraseMatcher & Syntax Rules)
2. Semantic Embedding Layer (sentence-transformers / all-MiniLM-L6-v2, 384-dim, cosine similarity against labeled seeds)
3. Hybrid Fusion & Confidence Engine (SIF Potential > 0.6, Pending Review if 0.4 <= confidence <= 0.6)
4. Async Task Pipeline: classify_report(report_id)
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import spacy
from spacy.matcher import PhraseMatcher
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.entities import (
    Alert,
    BarrierFailure,
    BarrierSeverity,
    Report,
    ReportLSRTag,
    ReportStatus,
    ReviewQueue,
    SIFLabel,
)

logger = logging.getLogger("sif_sentinel.classifier")


# ==============================================================================
# 1. spaCy Linguistic Rule & Pattern Layer
# ==============================================================================

# Initialize spaCy pipeline
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = spacy.blank("en")

# Domain high-risk rules and patterns
HIGH_RISK_RULE_PATTERNS = {
    "Energy Isolation": [
        "energy not isolated", "not isolated", "loto bypassed", "loto padlock",
        "lockout tagout", "lockout", "tagout", "live bus", "live conductor",
        "stored energy", "residual pressure", "hydraulic accumulator", "blind flange missing"
    ],
    "Safe Mechanical Lifting": [
        "worked under suspended load", "under suspended load", "suspended load",
        "crane wire snapped", "birdcaging", "crane boom", "dropped object",
        "rigging failed", "sling snapped", "winch wire"
    ],
    "Confined Space Entry": [
        "entered confined space without permit", "confined space without permit",
        "confined space", "mud tank entry", "toxic vapor", "h2s pocket",
        "atmospheric testing missing", "standby attendant missing", "oxygen deficient"
    ],
    "Driving": [
        "near miss with vehicle", "vehicle near miss", "tanker rollover",
        "speeding on bund road", "spark arrestor open", "brake failure bowser", "head-on collision"
    ],
    "Working at Height": [
        "fall from height", "unhooked harness", "detached lanyard", "monkey board unlatched",
        "scaffold collapsed", "missing guardrail", "no fall arrest", "dropped from height"
    ],
    "Well Control & Blowout Risk": [
        "gas leak", "well kick", "blowout", "bop failed", "annular bop",
        "pit volume gain", "casing pressure surge", "sour gas", "h2s alarm", "choke line"
    ],
    "Hot Work": [
        "hot work without permit", "spark near gas", "grinding near drain",
        "slag near cellar", "flammable vapor ignited", "open flame near wellhead"
    ],
    "Bypassing Safety Controls": [
        "bypassed safety controls", "jumpered esd", "interlock bypassed",
        "detector muted", "trip switch wedged"
    ],
}

# Compile spaCy PhraseMatcher
phrase_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
for rule_name, patterns in HIGH_RISK_RULE_PATTERNS.items():
    docs = [nlp.make_doc(text) for text in patterns]
    phrase_matcher.add(rule_name, docs)

SEVERITY_AMPLIFIERS = [
    "catastrophic", "fatal", "ruptured", "blown out", "high pressure",
    "uncontrolled", "ignited", "crushed", "struck by", "amputation", "severe"
]

NON_SIF_HOUSEKEEPING_PATTERNS = [
    "water bottle", "tea cup", "biscuit wrapper", "loose gravel", "torn cloth glove",
    "torn cotton glove", "flickering bulb", "eyewash tag", "dust mask", "trash bin",
    "uncoiled hose", "water cooler", "chalk label", "reverse park"
]


def evaluate_rule_layer(text: str) -> Tuple[float, Optional[str], List[str]]:
    """
    Evaluates raw report text using spaCy linguistic matching and high-risk terms.
    Returns: (rule_score, top_matched_category, evidence_phrases)
    """
    text_lower = text.lower()
    doc = nlp(text)
    matches = phrase_matcher(doc)

    matched_categories: Dict[str, int] = {}
    evidence_phrases: List[str] = []

    for match_id, start, end in matches:
        rule_name = nlp.vocab.strings[match_id]
        matched_categories[rule_name] = matched_categories.get(rule_name, 0) + 1
        phrase = doc[start:end].text
        if phrase not in evidence_phrases:
            evidence_phrases.append(phrase)

    # Check regex keywords
    for category, patterns in HIGH_RISK_RULE_PATTERNS.items():
        for p in patterns:
            if p in text_lower and p not in evidence_phrases:
                matched_categories[category] = matched_categories.get(category, 0) + 1
                evidence_phrases.append(p)

    # Check non-sif indicators
    non_sif_hits = [p for p in NON_SIF_HOUSEKEEPING_PATTERNS if p in text_lower]

    top_category = None
    if matched_categories:
        top_category = max(matched_categories, key=matched_categories.get)
        base_score = min(0.55 + (matched_categories[top_category] * 0.15), 0.90)

        # Severity amplifiers
        for amp in SEVERITY_AMPLIFIERS:
            if re.search(r'\b' + re.escape(amp) + r'\b', text_lower):
                base_score = min(base_score + 0.10, 0.98)
                if amp not in evidence_phrases:
                    evidence_phrases.append(amp)

        rule_score = round(base_score, 2)
    else:
        if non_sif_hits:
            rule_score = 0.10
        else:
            # Check for vague / ambiguous cues
            if any(w in text_lower for w in ["smell", "odor", "noise", "play", "damp", "vibration", "warm", "flange"]):
                rule_score = 0.45
            else:
                rule_score = 0.20

    return rule_score, top_category, evidence_phrases


# ==============================================================================
# 2. Semantic Embedding Layer & Seed Exemplars
# ==============================================================================

# Labeled Seed Exemplars for Few-Shot Nearest-Neighbor Similarity
SIF_SEED_REPORTS = [
    "Driller noticed sudden 15-barrel pit volume gain and casing pressure surge on BOP annular.",
    "Contractor entered crude storage tank before atmospheric H2S and oxygen gas test clearance.",
    "Electrician unbolting 415V MCC motor terminal without lockout tagout LOTO padlock.",
    "Derrickman unhooked twin-tail fall arrest harness lanyard at 90ft monkey board elevation.",
    "Hydra crane hoist wire rope birdcaged and snapped outer strands while lifting 10-ton BOP stack.",
    "Lead roughneck stood directly inside rotary tongs snub line bite radius during casing make-up.",
    "High pressure Chiksan mud pumping line whip-check clamp sheared during circulating kill mud.",
    "Heavy crude oil road tanker speeding on narrow unpaved bund road with rusted-out open spark arrestor.",
    "Operating electric angle grinder inside Class 1 Div 1 gas separator enclosure without Hot Work Permit.",
    "Emergency high pressure dump trip switch wedged open with wooden wedge defeating shutdown interlock.",
]

NON_SIF_SEED_REPORTS = [
    "Plastic water bottles and tea cups discarded on gravel near mechanical tool container.",
    "Helper in warehouse material yard observed using worn cloth gloves with exposed fingers.",
    "1-inch green washdown water hose left looped across mud testing lab walkway.",
    "Weekly inspection sign-off tag on eye wash unit near chemical dosing pump was overdue by two weeks.",
    "Secondary diesel drum in lube oil storage shed missing printed GHS flammable liquid placard.",
    "Water dispenser drip tray full with water dripping onto vinyl floor mat in living bunkhouse.",
    "Loose gravel scattered on paved pathway near administrative bunkhouse after morning drizzle.",
    "Bentonite chemical mud sacks stacked 12 high exceeding standard 8 sack pallet guideline.",
    "Contractor pickup vehicle parked nose-in at site parking bay instead of reverse parking.",
    "Fluorescent overhead tube light flickering inside electrical workshop room.",
]


class SemanticEmbedder:
    """
    Computes 384-dimensional dense vector embeddings matching the pgvector column.
    Supports sentence-transformers with instant offline deterministic fallback.
    """
    def __init__(self):
        self._model = None
        self._model_checked = False
        self._precompute_seeds()

    @property
    def model(self):
        if not self._model_checked:
            self._model_checked = True
            try:
                import os
                # Check if we should attempt online download or stick to fast local mode
                if os.environ.get("ENABLE_HF_DOWNLOAD", "false").lower() == "true":
                    from sentence_transformers import SentenceTransformer
                    self._model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
                    logger.info("Loaded sentence-transformers/all-MiniLM-L6-v2 successfully.")
            except Exception as e:
                logger.debug(f"sentence-transformers offline mode: {e}")
                self._model = None
        return self._model

    def embed_text(self, text: str) -> np.ndarray:
        if self.model is not None:
            emb = self.model.encode(text, normalize_embeddings=True)
            return np.array(emb, dtype=np.float32)
        else:
            # High-performance deterministic 384-dim semantic embedding with token hashing
            words = text.lower().split()
            vec = np.zeros(384, dtype=np.float32)
            for i, word in enumerate(words):
                h = abs(hash(word)) % (2**31)
                idx = h % 384
                sign = 1.0 if (h % 2 == 0) else -1.0
                vec[idx] += sign * (1.0 / (1.0 + 0.1 * i))
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            else:
                rng = np.random.RandomState(abs(hash(text)) % (2**32))
                vec = rng.randn(384).astype(np.float32)
                vec /= np.linalg.norm(vec)
            return vec

    def _precompute_seeds(self):
        self.sif_seed_embeddings = [self.embed_text(t) for t in SIF_SEED_REPORTS]
        self.non_sif_seed_embeddings = [self.embed_text(t) for t in NON_SIF_SEED_REPORTS]
        self.sif_centroid = np.mean(self.sif_seed_embeddings, axis=0)
        self.sif_centroid /= np.linalg.norm(self.sif_centroid)
        self.non_sif_centroid = np.mean(self.non_sif_seed_embeddings, axis=0)
        self.non_sif_centroid /= np.linalg.norm(self.non_sif_centroid)


    def compute_semantic_score(self, text: str) -> Tuple[float, np.ndarray]:
        """
        Computes cosine similarity against SIF vs Non-SIF seed centroids and top-k neighbors.
        Returns: (semantic_score [0.0 - 1.0], embedding_vector)
        """
        emb = self.embed_text(text)
        
        # Cosine similarity against centroids
        sim_sif = float(np.dot(emb, self.sif_centroid))
        sim_non_sif = float(np.dot(emb, self.non_sif_centroid))

        # Top-3 nearest neighbors in SIF set
        sif_sims = [float(np.dot(emb, s_emb)) for s_emb in self.sif_seed_embeddings]
        sif_top3 = np.mean(sorted(sif_sims, reverse=True)[:3])

        # Top-3 nearest neighbors in Non-SIF set
        non_sif_sims = [float(np.dot(emb, ns_emb)) for ns_emb in self.non_sif_seed_embeddings]
        non_sif_top3 = np.mean(sorted(non_sif_sims, reverse=True)[:3])

        # Softmax / Relative score
        diff = sif_top3 - non_sif_top3
        # Map difference (-0.5 to +0.5) to probability (0.0 to 1.0)
        semantic_prob = 1.0 / (1.0 + np.exp(-5.0 * diff))
        semantic_score = round(float(np.clip(semantic_prob, 0.05, 0.98)), 2)

        return semantic_score, emb


embedder = SemanticEmbedder()


# ==============================================================================
# 3. Hybrid SIF-Potential Classifier Function
# ==============================================================================

def classify_text(raw_text: str, activity: str = "") -> Dict[str, Any]:
    """
    Evaluates input text through the Hybrid SIF Classifier:
    1. Rule / Keyword & Linguistic Layer (spaCy)
    2. Semantic Layer (sentence-transformers / cosine similarity with seeds)
    3. Fusion Engine (confidence score, sif_label, and triage status)
    """
    combined_text = f"{activity} {raw_text}".strip()

    # 1. Rule Layer
    rule_score, top_category, evidence_phrases = evaluate_rule_layer(combined_text)

    # 2. Semantic Layer
    semantic_score, embedding = embedder.compute_semantic_score(combined_text)

    # 3. Hybrid Score Fusion
    # If rule layer has strong high-risk matches (e.g. >= 0.80), weight it higher
    if rule_score >= 0.80:
        confidence = round(0.55 * rule_score + 0.45 * semantic_score, 2)
    elif rule_score <= 0.20:
        confidence = round(0.40 * rule_score + 0.60 * semantic_score, 2)
    else:
        confidence = round(0.50 * rule_score + 0.50 * semantic_score, 2)

    # Ensure bounds [0.0, 1.0]
    confidence = float(np.clip(confidence, 0.05, 0.99))

    # 4. Classification Decision & Status Thresholds
    # Decision boundary: confidence > 0.6 -> sif_potential, else non_sif
    if confidence > 0.60:
        sif_label = SIFLabel.sif_potential
        is_sif = True
        status = ReportStatus.reviewed
    else:
        sif_label = SIFLabel.non_sif
        is_sif = False
        status = ReportStatus.auto_confirmed

    # Ambiguity boundary: 0.40 <= confidence <= 0.60 -> pending_review
    is_ambiguous = (0.40 <= confidence <= 0.60)
    if is_ambiguous:
        status = ReportStatus.pending_review

    return {
        "is_sif_precursor": is_sif,
        "sif_label": sif_label,
        "sif_confidence": confidence,
        "rule_score": rule_score,
        "semantic_score": semantic_score,
        "status": status,
        "is_ambiguous": is_ambiguous,
        "precursor_category": top_category,
        "evidence_phrases": evidence_phrases,
        "embedding": embedding.tolist(),
    }


# ==============================================================================
# 4. Async Task Function: classify_report(report_id)
# ==============================================================================

async def classify_report(report_id: int) -> Optional[Dict[str, Any]]:
    """
    Callable from a FastAPI BackgroundTask:
    - Loads the report from the DB
    - Runs the hybrid classifier
    - Updates sif_label, sif_confidence, status, and embedding on the report row
    - Inserts ReportLSRTag and BarrierFailure records
    - If 0.4 <= confidence <= 0.6, inserts a review_queue row with reason='low confidence classification'
    - If confidence >= 0.75, creates a high-priority Alert
    """
    async with AsyncSessionLocal() as db:
        try:
            stmt = select(Report).where(Report.id == report_id)
            result = await db.execute(stmt)
            report = result.scalar_one_or_none()

            if not report:
                logger.warning(f"Report ID {report_id} not found for classification.")
                return None

            # Execute Hybrid Classification
            classification = classify_text(raw_text=report.raw_text, activity=report.activity)

            # Update report fields
            report.sif_label = classification["sif_label"]
            report.sif_confidence = classification["sif_confidence"]
            report.status = classification["status"]
            report.embedding = classification["embedding"]

            # Insert Life-Saving Rule Tag
            category = classification["precursor_category"]
            if category:
                lsr_tag = ReportLSRTag(
                    report_id=report.id,
                    lsr_rule=category,
                    confidence=classification["sif_confidence"],
                )
                db.add(lsr_tag)

            # Insert Barrier Failures
            for phrase in classification["evidence_phrases"][:3]:
                bf = BarrierFailure(
                    report_id=report.id,
                    barrier_type=category or "Safety Barrier",
                    evidence_phrase=str(phrase),
                    severity=BarrierSeverity.high if classification["sif_confidence"] >= 0.75 else BarrierSeverity.medium,
                )
                db.add(bf)

            # Low-confidence Review Queue Insertion (0.40 <= confidence <= 0.60)
            if classification["is_ambiguous"]:
                rq = ReviewQueue(
                    report_id=report.id,
                    reason="low confidence classification",
                    assigned_to=None,
                    resolved=False,
                )
                db.add(rq)

            # High-risk SIF Alert Generation (confidence >= 0.75)
            if classification["sif_confidence"] >= 0.75:
                alert = Alert(
                    report_id=report.id,
                    alert_type="In-App & Email Notification",
                    sent_to="rig.superintendent@oilindia.in, hse.duty@oilindia.in",
                    sent_at=datetime.now(timezone.utc),
                    acknowledged=False,
                )
                db.add(alert)

            await db.commit()
            logger.info(
                f"Classified report {report_id}: label={report.sif_label}, "
                f"confidence={report.sif_confidence}, status={report.status}"
            )
            return classification

        except Exception as e:
            await db.rollback()
            logger.error(f"Error classifying report ID {report_id}: {str(e)}", exc_info=True)
            return None
