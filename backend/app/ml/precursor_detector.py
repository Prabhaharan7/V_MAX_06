import re
import numpy as np
from typing import Dict, List, Tuple


class SIFPrecursorDetector:
    """
    AI/NLP engine for detecting Serious Injury & Fatality (SIF) precursors
    in Oil & Gas safety observation reports (SIH 2026 PS 26165).
    """

    SIF_DOMAINS = {
        "Well Control & Blowout Risk": [
            "kick", "blowout", "bop", "annular", "choke manifold", "mud weight",
            "drilling fluid", "casing pressure", "wellhead", "gas influx", "degasser"
        ],
        "Toxic Gas & Hazardous Atmosphere (H2S)": [
            "h2s", "hydrogen sulfide", "sour gas", "gas leak", "flammable vapor",
            "lEL alarm", "breathing apparatus", "scba", "toxic gas", "asphyxiation"
        ],
        "Energy Isolation & High Pressure Systems": [
            "loto", "lockout", "tagout", "pressurized line", "relief valve",
            "burst disc", "high pressure", "manifold failure", "live voltage", "arc flash"
        ],
        "Lifting Operations & Suspended Loads": [
            "crane", "winch", "rigging", "sling snapped", "suspended load",
            "dropped object", "hoist", "traveling block", "drawworks"
        ],
        "Working at Heights & Scaffold Safety": [
            "fall arrest", "harness", "monkey board", "derrick", "mast",
            "scaffold collapse", "unsecured plank", "guardrail missing", "floor opening"
        ],
        "Confined Space Entry": [
            "mud tank", "storage vessel", "enclosed compartment", "oxygen deficient",
            "entry permit", "gas test failed"
        ]
    }

    SEVERITY_MODIFIERS = [
        "catastrophic", "rupture", "exploded", "failure", "uncontrolled",
        "near-fatal", "struck by", "crushed", "entangled", "spark ignited", "bypass"
    ]

    def analyze_report(self, title: str, description: str) -> Dict:
        """
        Extracts semantic risk signals, classifies precursor domain, calculates confidence,
        and assigns risk levels.
        """
        combined_text = f"{title} {description}".lower()
        matched_categories: List[Tuple[str, int, List[str]]] = []
        matched_severity_words = []

        # Check domain keyword matching and semantic density
        for domain, keywords in self.SIF_DOMAINS.items():
            matched_kw = [kw for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', combined_text)]
            if matched_kw:
                score = len(matched_kw)
                matched_categories.append((domain, score, matched_kw))

        # Check severity amplification keywords
        for mod in self.SEVERITY_MODIFIERS:
            if re.search(r'\b' + re.escape(mod) + r'\b', combined_text):
                matched_severity_words.append(mod)

        is_sif = False
        confidence = 0.0
        top_category = None
        risk_level = "Low"
        key_factors = []

        if matched_categories:
            matched_categories.sort(key=lambda x: x[1], reverse=True)
            top_category, match_count, keywords_found = matched_categories[0]
            key_factors.extend(keywords_found)

            # Base score from keyword intensity
            base_score = min(0.5 + (match_count * 0.15), 0.85)
            # Bonus from severity amplifier
            severity_bonus = min(len(matched_severity_words) * 0.1, 0.2)
            confidence = round(min(base_score + severity_bonus, 0.99), 2)

            if confidence >= 0.70:
                is_sif = True
                if confidence >= 0.88 or len(matched_severity_words) > 0:
                    risk_level = "Critical" if "blowout" in combined_text or "h2s" in combined_text else "High"
                else:
                    risk_level = "High"
            else:
                is_sif = False
                risk_level = "Medium"
        else:
            if len(matched_severity_words) > 0:
                risk_level = "Medium"
                confidence = 0.45
            else:
                risk_level = "Low"
                confidence = 0.15

        key_factors.extend(matched_severity_words)

        # Generate human-readable AI analysis explanation
        if is_sif:
            summary = (
                f"POTENTIAL SIF PRECURSOR IDENTIFIED in domain '{top_category}'. "
                f"High-energy hazard indicators detected with {int(confidence*100)}% model confidence. "
                f"Immediate review recommended to verify safety barriers and control integrity."
            )
        else:
            summary = (
                f"Standard safety observation. No immediate critical SIF precursors identified. "
                f"Assessed Risk: {risk_level} (Confidence: {int(confidence*100)}%)."
            )

        return {
            "is_sif_precursor": is_sif,
            "sif_confidence": confidence,
            "precursor_category": top_category,
            "risk_level": risk_level,
            "ai_analysis_summary": summary,
            "key_risk_factors": list(set(key_factors))
        }

    def generate_dummy_embedding(self, text: str) -> List[float]:
        """
        Generates deterministic normalized 384-dimensional vector embedding
        for pgvector similarity storage.
        """
        rng = np.random.RandomState(abs(hash(text)) % (2**32))
        vec = rng.randn(384)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()


detector = SIFPrecursorDetector()
