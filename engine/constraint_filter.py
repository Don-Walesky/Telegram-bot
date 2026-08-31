"""
Hard Safety Constraint Filter Module
Evaluates candidate betting selections against binary pass/fail safety invariants
prior to scoring and combinatorial optimization. Zero bypass allowed during fallback.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Tuple

from models.bet_candidate import BetCandidate
from models.engine_contracts import (
    BetConstructionRequest,
    RejectedCandidate,
    RejectionCategory,
    RiskProfile,
)

logger = logging.getLogger(__name__)


class HardConstraintFilter:
    # Minimum lead time before kickoff in seconds
    KICKOFF_BUFFER_SECONDS = 120

    @classmethod
    def evaluate_candidates(
        cls,
        candidates: List[BetCandidate],
        request: BetConstructionRequest,
    ) -> Tuple[List[BetCandidate], List[RejectedCandidate]]:
        """
        Filters candidates against hard safety invariants.
        Returns:
            Tuple of (eligible_candidates, rejected_candidates)
        """
        eligible: List[BetCandidate] = []
        rejected: List[RejectedCandidate] = []

        now = datetime.now()
        cutoff_time = now + timedelta(seconds=cls.KICKOFF_BUFFER_SECONDS)

        # Determine odds bounds from risk profile if not customized
        min_odds, max_odds = cls._get_odds_bounds_for_profile(request.risk_profile)

        for candidate in candidates:
            # 1. Kickoff Time Validation
            if candidate.kickoff_time and candidate.kickoff_time <= cutoff_time:
                rejected.append(
                    RejectedCandidate(
                        candidate_id=candidate.candidate_id,
                        fixture=candidate.fixture_title,
                        market_name=candidate.market_name,
                        odds=candidate.decimal_odds,
                        rejection_category=RejectionCategory.MATCH_ALREADY_STARTED,
                        rejection_reason=f"Event kickoff ({candidate.kickoff_time.strftime('%H:%M')}) is past or within 2 minutes of start.",
                        event_id=candidate.event_id,
                    )
                )
                continue

            # 2. Decimal Odds Basic Validity
            if candidate.decimal_odds <= 1.01:
                rejected.append(
                    RejectedCandidate(
                        candidate_id=candidate.candidate_id,
                        fixture=candidate.fixture_title,
                        market_name=candidate.market_name,
                        odds=candidate.decimal_odds,
                        rejection_category=RejectionCategory.INVALID_ODDS,
                        rejection_reason=f"Decimal odds ({candidate.decimal_odds:.2f}) must be strictly greater than 1.01.",
                        event_id=candidate.event_id,
                    )
                )
                continue

            # 3. Odds Range per Risk Profile
            if candidate.decimal_odds < min_odds:
                rejected.append(
                    RejectedCandidate(
                        candidate_id=candidate.candidate_id,
                        fixture=candidate.fixture_title,
                        market_name=candidate.market_name,
                        odds=candidate.decimal_odds,
                        rejection_category=RejectionCategory.ODDS_TOO_LOW,
                        rejection_reason=f"Decimal odds ({candidate.decimal_odds:.2f}) below {request.risk_profile.value} profile minimum ({min_odds:.2f}).",
                        event_id=candidate.event_id,
                    )
                )
                continue

            if candidate.decimal_odds > max_odds:
                rejected.append(
                    RejectedCandidate(
                        candidate_id=candidate.candidate_id,
                        fixture=candidate.fixture_title,
                        market_name=candidate.market_name,
                        odds=candidate.decimal_odds,
                        rejection_category=RejectionCategory.ODDS_TOO_HIGH,
                        rejection_reason=f"Decimal odds ({candidate.decimal_odds:.2f}) exceeds {request.risk_profile.value} profile maximum ({max_odds:.2f}).",
                        event_id=candidate.event_id,
                    )
                )
                continue

            # 4. Minimum Probability Threshold Check (using effective_probability)
            min_prob_pct = request.min_selection_probability
            cand_prob_pct = candidate.effective_probability

            if cand_prob_pct < min_prob_pct:
                rejected.append(
                    RejectedCandidate(
                        candidate_id=candidate.candidate_id,
                        fixture=candidate.fixture_title,
                        market_name=candidate.market_name,
                        odds=candidate.decimal_odds,
                        rejection_category=RejectionCategory.PROBABILITY_BELOW_THRESHOLD,
                        rejection_reason=f"Win probability ({cand_prob_pct:.1f}%) is below user minimum threshold ({min_prob_pct:.1f}%).",
                        event_id=candidate.event_id,
                    )
                )
                continue

            # 5. Data Freshness Check
            if (
                request.odds_freshness_ttl_sec > 0
                and candidate.data_freshness_seconds > request.odds_freshness_ttl_sec
            ):
                rejected.append(
                    RejectedCandidate(
                        candidate_id=candidate.candidate_id,
                        fixture=candidate.fixture_title,
                        market_name=candidate.market_name,
                        odds=candidate.decimal_odds,
                        rejection_category=RejectionCategory.STALE_DATA,
                        rejection_reason=f"Data age ({candidate.data_freshness_seconds:.0f}s) exceeds freshness TTL ({request.odds_freshness_ttl_sec}s).",
                        event_id=candidate.event_id,
                    )
                )
                continue

            # 6. Excluded Leagues Filter
            if request.excluded_leagues and candidate.league in request.excluded_leagues:
                rejected.append(
                    RejectedCandidate(
                        candidate_id=candidate.candidate_id,
                        fixture=candidate.fixture_title,
                        market_name=candidate.market_name,
                        odds=candidate.decimal_odds,
                        rejection_category=RejectionCategory.EXCLUDED_LEAGUE,
                        rejection_reason=f"League '{candidate.league}' is in user excluded leagues blacklist.",
                        event_id=candidate.event_id,
                    )
                )
                continue

            # Candidate passed all hard safety constraints
            candidate.is_eligible = True
            eligible.append(candidate)

        logger.info(
            f"🛡️ [HardConstraintFilter] Evaluated {len(candidates)} candidates: "
            f"{len(eligible)} eligible, {len(rejected)} rejected."
        )
        return eligible, rejected

    @staticmethod
    def _get_odds_bounds_for_profile(profile: RiskProfile) -> Tuple[float, float]:
        """Returns baseline decimal odds bounds for each risk profile (Engineering Defaults)."""
        if profile == RiskProfile.CONSERVATIVE:
            return 1.05, 1.30
        elif profile == RiskProfile.BALANCED:
            return 1.12, 1.65
        elif profile == RiskProfile.AGGRESSIVE:
            return 1.30, 2.20
        elif profile == RiskProfile.VERY_AGGRESSIVE:
            return 1.50, 3.50
        else:  # CUSTOM
            return 1.01, 10.00
