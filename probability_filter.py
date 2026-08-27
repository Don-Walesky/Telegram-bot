"""
Bookmaker-Implied Probability Filter Module
Calculates Implied Probability strictly from decimal odds:
    Implied Probability = (1.0 / decimal_odds) * 100%
Filters markets strictly within configured implied probability bounds
(e.g., 60.0% to 95.0%, decimal odds ~1.05 to ~1.66).
Explicitly labels all outputs as "Bookmaker-Implied Probability".
"""

from dataclasses import dataclass
from typing import List
from sportybet_catalog import MappedSportyBetSelection


@dataclass
class FilteredPick:
    selection: MappedSportyBetSelection
    odds: float
    implied_probability: float  # Percentage (e.g. 80.0%)
    label: str = "Bookmaker-Implied Probability"


class ImpliedProbabilityFilter:
    MIN_IMPLIED_PROB = 60.0
    MAX_IMPLIED_PROB = 95.0

    @staticmethod
    def calculate_implied_probability(odds: float) -> float:
        """
        Calculate Bookmaker-Implied Probability from decimal odds.
        Formula: (1 / decimal_odds) * 100%
        """
        if odds <= 1.0:
            return 0.0
        return (1.0 / odds) * 100.0

    @classmethod
    def filter_selections(
        cls,
        selections: List[MappedSportyBetSelection],
        min_prob: float = 60.0,
        max_prob: float = 95.0,
    ) -> List[FilteredPick]:
        """
        Filters picks whose Bookmaker-Implied Probability is strictly within [min_prob, max_prob].
        """
        valid_picks: List[FilteredPick] = []

        for sel in selections:
            prob = cls.calculate_implied_probability(sel.odds)
            if min_prob <= prob <= max_prob:
                valid_picks.append(
                    FilteredPick(
                        selection=sel,
                        odds=sel.odds,
                        implied_probability=round(prob, 1),
                    )
                )

        return valid_picks
