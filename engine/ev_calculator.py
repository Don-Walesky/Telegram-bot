"""
Expected Value & Market De-vigging Calculator Module
Provides mathematical formulations for fair probabilities, bookmaker overround,
proportional margin removal (de-vigging), and expected value metrics with explicit provenance.
"""

from typing import List
from models.bet_candidate import BetCandidate, ProbabilitySource


class EVCalculator:
    @staticmethod
    def calculate_expected_value(
        prob_decimal: float = 0.0,
        decimal_odds: float = 0.0,
        model_probability: Optional[float] = None,
    ) -> float:
        """
        Calculates Expected Value (EV) per unit wagered.
        Formula: EV = (prob_decimal * decimal_odds) - 1.0
        Where prob_decimal is in range [0.0, 1.0].
        Returns float, e.g. +0.05 for +5.0% EV or -0.08 for -8.0% EV.
        """
        p = model_probability if model_probability is not None else prob_decimal
        if p <= 0.0 or decimal_odds <= 0.0:
            return -1.0
        return (p * decimal_odds) - 1.0

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
        Calculates and populates probability provenance and expected value fields.
        - Calculates implied probability strictly from decimal odds.
        - If candidate has genuine model_probability, calculates MODEL EV.
        - If candidate has consensus_probability, calculates HEURISTIC ESTIMATED EV.
        - If candidate only has bookmaker implied probability, marks EV as 0.0 (equilibrium) with heuristic flag.
        - Crucially: NEVER fabricates model_probability from 1/odds.
        """
        if candidate.bookmaker_implied_prob == 0.0 and candidate.decimal_odds > 0:
            candidate.bookmaker_implied_prob = round(cls.calculate_implied_probability(candidate.decimal_odds), 2)

        if candidate.model_probability is not None and candidate.model_probability > 0:
            candidate.expected_value = round(
                cls.calculate_expected_value(candidate.model_probability, candidate.decimal_odds), 4
            )
            candidate.expected_value_is_heuristic = False
            candidate.probability_source = ProbabilitySource.PREDICTIVE_MODEL
        elif candidate.consensus_probability is not None and candidate.consensus_probability > 0:
            consensus_dec = candidate.consensus_probability / 100.0
            candidate.expected_value = round(
                cls.calculate_expected_value(consensus_dec, candidate.decimal_odds), 4
            )
            candidate.expected_value_is_heuristic = True
            candidate.probability_source = ProbabilitySource.CONSENSUS_HEURISTIC
        else:
            # Baseline: bookmaker pricing equilibrium; no predictive model edge
            candidate.expected_value = 0.0
            candidate.expected_value_is_heuristic = True
            candidate.probability_source = ProbabilitySource.BOOKMAKER_IMPLIED

        return candidate
