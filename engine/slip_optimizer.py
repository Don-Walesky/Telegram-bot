"""
Combinatorial Accumulator Slip Optimizer Module
Solves the multi-objective accumulator selection problem using a bounded beam search
heuristic optimizer to maximize score utility while converging on target combined odds.
Enforces the strict "No Bad Bets" invariant: selection quality dominates target multipliers.
"""

import math
import logging
from typing import List, Tuple

from calculator import BetCalculator
from models.bet_candidate import BetCandidate
from models.engine_contracts import (
    BetConstructionRequest,
    ConstructionStatusCode,
)
from engine.correlation_manager import CorrelationManager

logger = logging.getLogger(__name__)


class SlipOptimizer:
    BEAM_WIDTH = 50

    @classmethod
    def optimize_slip(
        cls,
        candidates: List[BetCandidate],
        request: BetConstructionRequest,
    ) -> Tuple[List[BetCandidate], ConstructionStatusCode, List[str]]:
        """
        Selects an optimal combination of candidates satisfying target odds, desired game count,
        and diversity constraints without violating candidate quality.

        Returns:
            Tuple of (selected_candidates, status_code, warnings)
        """
        warnings: List[str] = []

        if not candidates:
            return [], ConstructionStatusCode.INSUFFICIENT_CANDIDATES, ["No eligible candidates available."]

        # 1. Deduplicate intra-match candidates first (keep top score per fixture)
        independent_pool = CorrelationManager.deduplicate_intra_match_candidates(candidates)

        if len(independent_pool) < request.min_game_count:
            # Shortfall condition: fewer independent matches than minimum viable slip
            msg = (
                f"Only {len(independent_pool)} independent fixture(s) met quality criteria "
                f"(minimum viable slip requires {request.min_game_count})."
            )
            return independent_pool, ConstructionStatusCode.INSUFFICIENT_CANDIDATES, [msg]

        # Determine target parameters
        desired_count = min(request.desired_game_count, len(independent_pool))
        target_odds = request.target_combined_odds or 3.00

        # 2. Execute Beam Search optimization
        best_slip = cls._beam_search(
            pool=independent_pool,
            target_count=desired_count,
            min_count=request.min_game_count,
            target_odds=target_odds,
            min_odds=request.min_combined_odds,
            max_odds=request.max_combined_odds,
            max_league_pct=request.max_league_exposure_pct,
            max_sport_pct=request.max_sport_exposure_pct,
        )

        if not best_slip:
            # Fallback to top-score slice if beam search found no valid combination in strict bounds
            best_slip = independent_pool[:desired_count]
            warnings.append("Beam search could not strictly satisfy combined odds bounds; fell back to top-score subset.")

        # Compute actual combined odds
        total_odds = 1.0
        for leg in best_slip:
            total_odds *= leg.decimal_odds

        # Check for target odds deviation
        status_code = ConstructionStatusCode.OPTIMAL
        if abs(total_odds - target_odds) > (target_odds * 0.25):
            status_code = ConstructionStatusCode.SUB_OPTIMAL
            warnings.append(
                f"Combined odds ({total_odds:.2f}x) differed from requested target ({target_odds:.2f}x). "
                f"No weaker legs were added simply to hit the target."
            )

        if len(best_slip) < request.desired_game_count:
            warnings.append(
                f"Selected {len(best_slip)} games (requested {request.desired_game_count}). "
                f"Did not add lower-confidence matches to fulfill requested count."
            )

        logger.info(
            f"🎯 [SlipOptimizer] Optimization complete: {len(best_slip)} legs selected, "
            f"Total Odds: {total_odds:.2f}x (Target: {target_odds:.2f}x), Status: {status_code.value}"
        )
        return best_slip, status_code, warnings

    @classmethod
    def _evaluate_slip_objective(
        cls,
        slip: List[BetCandidate],
        target_odds: float,
        max_league_pct: float,
        max_sport_pct: float,
    ) -> float:
        """
        Calculates accumulator utility score:
        Utility = Sum(Scores) + Bonus_Boost - Odds_Penalty - Exposure_Penalty
        """
        if not slip:
            return -1000.0

        sum_scores = sum(c.composite_score if c.composite_score is not None else 0.0 for c in slip)
        total_odds = 1.0
        for c in slip:
            total_odds *= c.decimal_odds

        bonus_pct = BetCalculator.calculate_sportybet_bonus_percentage(len(slip))
        bonus_boost = math.log1p(bonus_pct / 100.0)

        # Logarithmic odds distance penalty
        odds_diff = abs(math.log(max(1.01, total_odds)) - math.log(max(1.01, target_odds)))
        odds_penalty = 0.50 * odds_diff

        exposure_penalty = CorrelationManager.calculate_exposure_penalty(
            slip, max_league_pct=max_league_pct, max_sport_pct=max_sport_pct
        )

        return sum_scores + bonus_boost - odds_penalty - exposure_penalty

    @classmethod
    def _beam_search(
        cls,
        pool: List[BetCandidate],
        target_count: int,
        min_count: int,
        target_odds: float,
        min_odds: float,
        max_odds: float,
        max_league_pct: float,
        max_sport_pct: float,
    ) -> List[BetCandidate]:
        """
        Bounded beam search over candidate subsets to find the combination maximizing utility.
        """
        beam: List[List[BetCandidate]] = [[]]

        # Consider top candidates up to 4x target count to maintain speed
        search_candidates = pool[: min(len(pool), target_count * 4)]

        for cand in search_candidates:
            new_beam: List[List[BetCandidate]] = []
            for slip in beam:
                # 1. State without this candidate
                new_beam.append(slip)

                # 2. State adding this candidate (if count and independence allowed)
                if len(slip) < target_count:
                    if not any(CorrelationManager.are_conflicting(c, cand) for c in slip):
                        new_slip = slip + [cand]
                        new_beam.append(new_slip)

            # Prune beam to BEAM_WIDTH based on current score
            new_beam = sorted(
                new_beam,
                key=lambda s: cls._evaluate_slip_objective(s, target_odds, max_league_pct, max_sport_pct),
                reverse=True,
            )[: cls.BEAM_WIDTH]
            beam = new_beam

        # Filter completed candidates matching count bounds
        valid_slips = [s for s in beam if len(s) >= min_count]
        if not valid_slips:
            return []

        # Find best slip among valid slips
        best_slip = max(
            valid_slips,
            key=lambda s: cls._evaluate_slip_objective(s, target_odds, max_league_pct, max_sport_pct),
        )
        return best_slip
