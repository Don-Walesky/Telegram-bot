"""
Expected Value & Market De-vigging Calculator Module
Provides mathematical formulations for fair probabilities, bookmaker overround,
proportional margin removal (de-vigging), and expected value metrics.
"""

from typing import List
from engine.contracts import BetCandidate


class EVCalculator:
    @staticmethod
    def calculate_expected_value(model_probability: float, decimal_odds: float) -> float:
        """
        Calculates Expected Value (EV) per unit wagered.
        Formula: EV = (model_probability * decimal_odds) - 1.0
        Where model_probability is in range [0.0, 1.0].
        Returns float, e.g. +0.05 for +5.0% EV or -0.08 for -8.0% EV.
        """
        if model_probability <= 0.0 or decimal_odds <= 0.0:
            return -1.0
        return (model_probability * decimal_odds) - 1.0

    @staticmethod
    def calculate_implied_probability(decimal_odds: float) -> float:
        """
        Calculates Bookmaker-Implied Probability from decimal odds.
        Formula: (1.0 / decimal_odds) * 100%
        """
        if decimal_odds <= 1.0:
            return 0.0
        return (1.0 / decimal_odds) * 100.0

    @staticmethod
    def calculate_overround(odds_list: List[float]) -> float:
        """
        Calculates total bookmaker overround (margin) across all market outcomes.
        Formula: sum(1 / odds_i) - 1.0
        """
        if not odds_list:
            return 0.0
        raw_sum = sum((1.0 / o) for o in odds_list if o > 1.0)
        return max(0.0, raw_sum - 1.0)

    @staticmethod
    def devig_odds_proportional(odds_list: List[float]) -> List[float]:
        """
        Removes bookmaker overround via multiplicative/proportional de-vigging.
        Returns normalized true probabilities summing to 1.0.
        """
        if not odds_list:
            return []
        raw_probs = [(1.0 / o) if o > 1.0 else 0.0 for o in odds_list]
        total_raw = sum(raw_probs)
        if total_raw <= 0:
            return [0.0] * len(odds_list)
        return [p / total_raw for p in raw_probs]

    @classmethod
    def enrich_candidate(cls, candidate: BetCandidate) -> BetCandidate:
        """
        Calculates and populates implied probability and EV fields on a candidate.
        """
        candidate.bookmaker_implied_prob = round(cls.calculate_implied_probability(candidate.decimal_odds), 2)
        if candidate.model_probability <= 0.0:
            candidate.model_probability = round(candidate.bookmaker_implied_prob / 100.0, 4)
        candidate.expected_value = round(
            cls.calculate_expected_value(candidate.model_probability, candidate.decimal_odds), 4
        )
        return candidate
