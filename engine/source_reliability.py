"""
Bayesian Source Reliability & Credibility Model Module
Calculates sample-size regressed credibility scores and applies exponential recency decay
to ensure small-sample tipsters or channels do not artificially outrank proven predictors.
"""

import math
from typing import Dict, Optional


class SourceReliabilityModel:
    SHRINKAGE_K = 25.0       # Number of pseudo-observations for prior shrinkage
    PRIOR_ACCURACY = 0.75    # Baseline global accuracy prior (75%)
    RECENCY_LAMBDA = 0.023   # Half-life of ~30 days (decay per day of inactivity)

    @classmethod
    def calculate_regressed_reliability(
        cls,
        wins: int,
        total_predictions: int,
        prior: Optional[float] = None,
        shrinkage_k: Optional[float] = None,
    ) -> float:
        """
        Computes Bayesian regressed accuracy with shrinkage toward the prior.
        Formula:
            R = (N / (N + K)) * (Wins / N) + (K / (N + K)) * Prior
        """
        if total_predictions <= 0:
            return cls.PRIOR_ACCURACY

        k = shrinkage_k if shrinkage_k is not None else cls.SHRINKAGE_K
        mu_prior = prior if prior is not None else cls.PRIOR_ACCURACY

        empirical_acc = max(0.0, min(1.0, wins / total_predictions))
        weight_data = total_predictions / (total_predictions + k)
        weight_prior = k / (total_predictions + k)

        regressed = (weight_data * empirical_acc) + (weight_prior * mu_prior)
        return round(regressed, 4)

    @classmethod
    def calculate_recency_weight(cls, days_since_last_activity: float) -> float:
        """
        Computes exponential decay weight in [0.0, 1.0] based on activity recency.
        Formula:
            W = exp(-lambda * days)
        """
        if days_since_last_activity <= 0:
            return 1.0
        decay = math.exp(-cls.RECENCY_LAMBDA * days_since_last_activity)
        return round(max(0.05, min(1.0, decay)), 4)

    @classmethod
    def evaluate_source_credibility(
        cls,
        wins: int,
        total_predictions: int,
        days_inactive: float = 0.0,
    ) -> float:
        """
        Computes combined effective source credibility score in [0.0, 1.0].
        """
        base_reliability = cls.calculate_regressed_reliability(wins, total_predictions)
        recency_factor = cls.calculate_recency_weight(days_inactive)
        return round(base_reliability * recency_factor, 4)
