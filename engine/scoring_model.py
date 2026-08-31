"""
Candidate Scoring Model Module
Computes a normalized Composite Utility Score S in [0.0, 1.0] across effective probability,
expected value, source reliability, market safety, data freshness, and uncertainty.
"""

import math
from typing import Dict, List
from models.bet_candidate import BetCandidate, ProbabilitySource
from models.engine_contracts import BetConstructionRequest


class CandidateScorer:
    # Default scoring weights (sum = 1.0)
    DEFAULT_WEIGHT_PROB = 0.35
    DEFAULT_WEIGHT_EV = 0.25
    DEFAULT_WEIGHT_SOURCE = 0.15
    DEFAULT_WEIGHT_MARKET = 0.15
    DEFAULT_WEIGHT_FRESHNESS = 0.10

    # Market reliability rating lookup (Heuristic safety ratings)
    MARKET_RELIABILITY_MAP: Dict[str, float] = {
        "double chance": 1.00,
        "double chance (1x)": 1.00,
        "double chance (x2)": 1.00,
        "double chance (12)": 0.95,
        "over 1.5 goals": 0.90,
        "over 1.5 match goals": 0.90,
        "draw no bet": 0.85,
        "draw no bet (dnb)": 0.85,
        "winner (2-way incl. ot)": 0.85,
        "handicap (+8.5 points)": 0.85,
        "handicap (+7.5)": 0.85,
        "to win at least 1 set": 0.80,
        "1x2": 0.65,
        "home win": 0.70,
        "away win": 0.65,
        "over 2.5 goals": 0.60,
        "under 3.5 goals": 0.75,
        "both teams to score (gg)": 0.55,
    }

    @classmethod
    def normalize_probability(cls, prob_decimal: float, min_prob: float = 0.50) -> float:
        """Normalizes probability decimal [0.0, 1.0] into [0.0, 1.0] score component."""
        if prob_decimal <= min_prob:
            return 0.0
        if prob_decimal >= 1.0:
            return 1.0
        return (prob_decimal - min_prob) / (1.0 - min_prob)

    @classmethod
    def normalize_expected_value(cls, ev: float) -> float:
        """
        Normalizes Expected Value using a logistic sigmoid centered at EV = 0.0.
        EV = 0.00 -> 0.50 (Neutral)
        EV = +0.10 -> 0.82 (High Value)
        EV = -0.10 -> 0.18 (Low Value)
        """
        clamped_ev = max(-1.0, min(1.0, ev))
        return 1.0 / (1.0 + math.exp(-15.0 * clamped_ev))

    @classmethod
    def normalize_source_reliability(cls, accuracy: float, sample_size: int) -> float:
        """
        Evaluates source reliability modulated by historical sample size.
        Shrinks small sample sizes toward baseline using an asymptotic saturation curve.
        """
        acc = max(0.0, min(1.0, accuracy))
        confidence_factor = 1.0 - math.exp(-max(0, sample_size) / 30.0)
        return acc * confidence_factor

    @classmethod
    def get_market_reliability(cls, market_name: str) -> float:
        """Returns baseline heuristic reliability score for a given market description."""
        clean_name = market_name.strip().lower()
        return cls.MARKET_RELIABILITY_MAP.get(clean_name, 0.70)

    @classmethod
    def normalize_freshness(cls, age_seconds: float, ttl_seconds: float = 600.0) -> float:
        """Calculates freshness score decaying linearly to 0 at TTL."""
        if age_seconds <= 0:
            return 1.0
        if age_seconds >= ttl_seconds:
            return 0.0
        return max(0.0, 1.0 - (age_seconds / ttl_seconds))

    @classmethod
    def score_candidate(cls, candidate: BetCandidate, min_prob_threshold: float = 0.50) -> float:
        """
        Calculates composite utility score S in [0.0, 1.0] for an individual candidate.
        Uses candidate.effective_probability to handle all probability provenances cleanly.
        """
        eff_prob_dec = candidate.effective_probability / 100.0
        f_prob = cls.normalize_probability(eff_prob_dec, min_prob=min_prob_threshold)

        ev_val = candidate.expected_value if candidate.expected_value is not None else 0.0
        g_ev = cls.normalize_expected_value(ev_val)

        # Source accuracy & sample size (uses sensible defaults when unrecorded in V1)
        src_acc = candidate.source_historical_accuracy if candidate.source_historical_accuracy is not None else 0.75
        src_samples = candidate.source_sample_size if candidate.source_sample_size is not None else 10
        h_source = cls.normalize_source_reliability(src_acc, src_samples)

        m_market = cls.get_market_reliability(candidate.market_name)
        q_fresh = cls.normalize_freshness(candidate.data_freshness_seconds)

        base_score = (
            cls.DEFAULT_WEIGHT_PROB * f_prob
            + cls.DEFAULT_WEIGHT_EV * g_ev
            + cls.DEFAULT_WEIGHT_SOURCE * h_source
            + cls.DEFAULT_WEIGHT_MARKET * m_market
            + cls.DEFAULT_WEIGHT_FRESHNESS * q_fresh
        )

        # Apply uncertainty penalty if model confidence is provided
        confidence = candidate.model_confidence if candidate.model_confidence is not None else 1.0
        uncertainty_penalty = (1.0 - max(0.0, min(1.0, confidence))) * 0.20

        composite = max(0.0, min(1.0, base_score - uncertainty_penalty))
        candidate.composite_score = round(composite, 4)
        return candidate.composite_score

    @classmethod
    def rank_candidates(cls, candidates: List[BetCandidate], request: BetConstructionRequest) -> List[BetCandidate]:
        """Scores and sorts candidates descending by composite score."""
        min_prob = request.min_selection_probability / 100.0
        for cand in candidates:
            cls.score_candidate(cand, min_prob_threshold=min_prob)

        return sorted(candidates, key=lambda c: c.composite_score if c.composite_score is not None else 0.0, reverse=True)
