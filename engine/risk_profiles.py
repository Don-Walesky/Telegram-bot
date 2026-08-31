"""
Risk Profiles & Invariants Manager Module
Defines formal mathematical boundaries, expected value minimums, odds bounds,
and Kelly stake sizing fractions for Conservative, Balanced, Aggressive, Very Aggressive, and Custom profiles.

NOTE: Numerical thresholds in this module are ENGINEERING DEFAULTS established from domain betting rules,
pending empirical calibration when historical settled outcome datasets become available.
"""

from dataclasses import dataclass
from typing import Tuple
from models.bet_candidate import BetCandidate
from models.engine_contracts import RiskProfile


@dataclass(frozen=True)
class RiskProfileDefinition:
    profile: RiskProfile
    min_probability: float  # Percentage (e.g. 85.0) - Engineering Default
    max_probability: float  # Percentage (e.g. 98.0) - Engineering Default
    min_odds: float        # Decimal odds (e.g. 1.05) - Engineering Default
    max_odds: float        # Decimal odds (e.g. 1.28) - Engineering Default
    min_ev: float          # EV threshold (e.g. -0.02 for conservative, 0.00 for balanced)
    kelly_fraction: float  # Fraction of Full Kelly (0.125 for Eighth, 0.25 for Quarter)
    target_combined_odds_min: float
    target_combined_odds_max: float
    description: str


class RiskProfileManager:
    PROFILES = {
        RiskProfile.CONSERVATIVE: RiskProfileDefinition(
            profile=RiskProfile.CONSERVATIVE,
            min_probability=85.0,
            max_probability=98.0,
            min_odds=1.05,
            max_odds=1.28,
            min_ev=-0.02,
            kelly_fraction=0.125,
            target_combined_odds_min=1.50,
            target_combined_odds_max=3.00,
            description="Capital preservation; maximize joint probability; minimize variance. (Engineering Default)",
        ),
        RiskProfile.BALANCED: RiskProfileDefinition(
            profile=RiskProfile.BALANCED,
            min_probability=75.0,
            max_probability=90.0,
            min_odds=1.12,
            max_odds=1.55,
            min_ev=0.00,
            kelly_fraction=0.25,
            target_combined_odds_min=2.50,
            target_combined_odds_max=6.00,
            description="Balance probability and expected return; Sharpe-optimal accumulator. (Engineering Default)",
        ),
        RiskProfile.AGGRESSIVE: RiskProfileDefinition(
            profile=RiskProfile.AGGRESSIVE,
            min_probability=60.0,
            max_probability=80.0,
            min_odds=1.25,
            max_odds=2.00,
            min_ev=0.03,
            kelly_fraction=0.50,
            target_combined_odds_min=5.00,
            target_combined_odds_max=15.00,
            description="Exploit higher expected value with greater variance tolerance. (Engineering Default)",
        ),
        RiskProfile.VERY_AGGRESSIVE: RiskProfileDefinition(
            profile=RiskProfile.VERY_AGGRESSIVE,
            min_probability=50.0,
            max_probability=75.0,
            min_odds=1.40,
            max_odds=3.00,
            min_ev=0.05,
            kelly_fraction=0.50,
            target_combined_odds_min=10.00,
            target_combined_odds_max=50.00,
            description="High multiplier long-shot accumulators under positive EV discipline. (Engineering Default)",
        ),
        RiskProfile.CUSTOM: RiskProfileDefinition(
            profile=RiskProfile.CUSTOM,
            min_probability=50.0,
            max_probability=99.0,
            min_odds=1.01,
            max_odds=10.00,
            min_ev=-0.05,
            kelly_fraction=0.25,
            target_combined_odds_min=1.50,
            target_combined_odds_max=20.00,
            description="User-defined custom parameters and boundaries.",
        ),
    }

    @classmethod
    def get_profile_definition(cls, profile: RiskProfile) -> RiskProfileDefinition:
        return cls.PROFILES.get(profile, cls.PROFILES[RiskProfile.BALANCED])

    @classmethod
    def validate_candidate(cls, candidate: BetCandidate, profile: RiskProfile) -> Tuple[bool, str]:
        """
        Validates if a candidate complies with the risk profile's mathematical invariants.
        Uses candidate.effective_probability to evaluate probability thresholds.
        Returns:
            Tuple of (is_valid, rejection_reason)
        """
        defn = cls.get_profile_definition(profile)
        prob_pct = candidate.effective_probability

        if prob_pct < defn.min_probability:
            return False, f"Effective probability ({prob_pct:.1f}%) is below {profile.value} minimum ({defn.min_probability:.1f}%)."

        if candidate.decimal_odds < defn.min_odds:
            return False, f"Odds ({candidate.decimal_odds:.2f}) below {profile.value} minimum ({defn.min_odds:.2f})."

        if candidate.decimal_odds > defn.max_odds:
            return False, f"Odds ({candidate.decimal_odds:.2f}) exceeds {profile.value} maximum ({defn.max_odds:.2f})."

        if candidate.expected_value is not None and candidate.expected_value < defn.min_ev:
            return False, f"Expected Value ({candidate.expected_value:+.2%}) is below {profile.value} minimum ({defn.min_ev:+.2%})."

        return True, ""

    @classmethod
    def calculate_kelly_stake(
        cls,
        estimated_joint_probability: float,
        total_odds: float,
        bankroll: float = 10000.0,
        profile: RiskProfile = RiskProfile.BALANCED,
    ) -> float:
        """
        Calculates recommended stake sizing using Fractional Kelly Criterion.
        Formula:
            Full Kelly = (b * p - q) / b, where b = odds - 1, p = prob, q = 1 - p.
            Fractional Kelly = Full Kelly * fraction.
        """
        if total_odds <= 1.0 or estimated_joint_probability <= 0.0 or bankroll <= 0:
            return 0.0

        p = min(1.0, estimated_joint_probability / 100.0 if estimated_joint_probability > 1.0 else estimated_joint_probability)
        b = total_odds - 1.0
        q = 1.0 - p

        full_kelly = (b * p - q) / b
        if full_kelly <= 0:
            return min(100.0, bankroll * 0.01)  # Default token minimum stake on negative edge

        defn = cls.get_profile_definition(profile)
        recommended_pct = full_kelly * defn.kelly_fraction

        # Clamp stake to max 10% of bankroll for risk management
        clamped_pct = max(0.01, min(0.10, recommended_pct))
        return round(bankroll * clamped_pct, 2)
