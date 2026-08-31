"""
Unified Risk / Bet Construction Engine Module
Acts as the central domain orchestrator coordinating candidate gating, EV enrichment,
scoring, risk profiling, correlation defense, and combinatorial slip optimization.
"""

import logging
from typing import List, Optional

from calculator import BetCalculator
from models.bet_candidate import BetCandidate, ProbabilitySource
from models.engine_contracts import (
    BetConstructionRequest,
    BetConstructionResult,
    ConstructionStatusCode,
    SelectedBetLeg,
)
from engine.constraint_filter import HardConstraintFilter
from engine.ev_calculator import EVCalculator
from engine.scoring_model import CandidateScorer
from engine.risk_profiles import RiskProfileManager
from engine.slip_optimizer import SlipOptimizer

logger = logging.getLogger(__name__)


class BetConstructionEngine:
    @classmethod
    def build_bet_slip(
        cls,
        request: BetConstructionRequest,
    ) -> BetConstructionResult:
        """
        Executes the complete end-to-end bet construction pipeline:
        1. Ingests and gates candidates through HardConstraintFilter.
        2. Enriches eligible candidates with expected value & probability provenance.
        3. Enforces RiskProfile invariants.
        4. Computes multi-factor composite scores and ranks candidates.
        5. Optimizes slip combination via combinatorial beam search.
        6. Computes joint probabilities, Kelly recommended stake, and SportyBet bonus ladder.
        7. Assembles structured explainability metadata and returns BetConstructionResult.
        """
        logger.info(
            f"🚀 [BetConstructionEngine] Starting construction for Request ID: {request.request_id} "
            f"(Workflow: {request.workflow.value}, Profile: {request.risk_profile.value})"
        )

        total_evaluated = len(request.candidates)
        if total_evaluated == 0:
            return cls._build_empty_result(request, ConstructionStatusCode.NO_FIXTURES, "No candidate fixtures provided.")

        # Stage 1: Hard Constraints Filter
        eligible, rejected = HardConstraintFilter.evaluate_candidates(request.candidates, request)

        if not eligible:
            return cls._build_empty_result(
                request,
                ConstructionStatusCode.INSUFFICIENT_CANDIDATES,
                "All candidates were dropped by hard safety filters.",
                rejected=rejected,
                total_evaluated=total_evaluated,
            )

        # Stage 2 & 3: Metric Enrichment & Risk Profile Invariant Gating
        profile_eligible: List[BetCandidate] = []
        for cand in eligible:
            EVCalculator.enrich_candidate(cand)
            is_valid, reason = RiskProfileManager.validate_candidate(cand, request.risk_profile)
            if is_valid:
                profile_eligible.append(cand)
            else:
                # Append rejection record
                rejected_record = HardConstraintFilter.evaluate_candidates([cand], request)[1]
                if rejected_record:
                    rejected.append(rejected_record[0])

        # Clean any None rejection records
        rejected = [r for r in rejected if r is not None]

        if not profile_eligible:
            return cls._build_empty_result(
                request,
                ConstructionStatusCode.INSUFFICIENT_CANDIDATES,
                f"No candidates satisfied the {request.risk_profile.value} risk profile invariants.",
                rejected=rejected,
                total_evaluated=total_evaluated,
            )

        # Stage 4: Candidate Scoring & Ranking
        ranked_candidates = CandidateScorer.rank_candidates(profile_eligible, request)

        # Stage 5: Combinatorial Slip Optimization
        selected_candidates, status_code, warnings = SlipOptimizer.optimize_slip(ranked_candidates, request)

        if not selected_candidates or len(selected_candidates) < request.min_game_count:
            return cls._build_empty_result(
                request,
                ConstructionStatusCode.INSUFFICIENT_CANDIDATES,
                f"Only {len(selected_candidates)} valid match(es) found (minimum viable slip requires {request.min_game_count}).",
                rejected=rejected,
                total_evaluated=total_evaluated,
                warnings=warnings,
            )

        # Stage 6: Accumulator Calculations
        total_odds = 1.0
        joint_prob = 1.0
        selected_legs: List[SelectedBetLeg] = []

        for cand in selected_candidates:
            total_odds *= cand.decimal_odds
            cand_prob_pct = cand.effective_probability
            cand_prob_dec = cand_prob_pct / 100.0
            joint_prob *= cand_prob_dec

            # Build clear, provenance-aware explainability reasons
            prob_label = (
                f"Model Probability: {cand_prob_pct:.1f}%"
                if cand.probability_source == ProbabilitySource.PREDICTIVE_MODEL
                else f"Consensus Heuristic Probability: {cand_prob_pct:.1f}%"
                if cand.probability_source == ProbabilitySource.CONSENSUS_HEURISTIC
                else f"Bookmaker Implied Probability: {cand_prob_pct:.1f}%"
            )

            ev_val = cand.expected_value if cand.expected_value is not None else 0.0
            ev_label = (
                f"Heuristic Value Edge: {ev_val:+.1%}"
                if cand.expected_value_is_heuristic
                else f"Model Expected Value: {ev_val:+.1%}"
            )

            reasons = [
                f"{prob_label} satisfies {request.risk_profile.value} threshold",
                ev_label,
                f"Market: {cand.market_name} (Safety Rating: {CandidateScorer.get_market_reliability(cand.market_name):.2f})",
            ]

            selected_legs.append(
                SelectedBetLeg(
                    candidate_id=cand.candidate_id,
                    fixture=cand.fixture_title,
                    league=cand.league,
                    sport=cand.sport,
                    kickoff_time=cand.kickoff_time,
                    market_name=cand.market_name,
                    outcome_name=cand.outcome_name,
                    odds=cand.decimal_odds,
                    implied_probability_pct=cand.bookmaker_implied_prob,
                    probability_source=cand.probability_source,
                    effective_probability_pct=cand_prob_pct,
                    model_probability_pct=round(cand.model_probability * 100.0, 1) if cand.model_probability else None,
                    consensus_probability_pct=cand.consensus_probability,
                    expected_value_pct=round(ev_val * 100.0, 1),
                    is_heuristic_ev=cand.expected_value_is_heuristic,
                    composite_score=cand.composite_score,
                    acceptance_reasons=reasons,
                    specifier=cand.specifier,
                    event_id=cand.event_id,
                    market_id=cand.market_id,
                    outcome_id=cand.outcome_id,
                )
            )

        total_odds = round(total_odds, 2)
        joint_prob_pct = round(joint_prob * 100.0, 2)
        slip_ev_pct = round(((joint_prob * total_odds) - 1.0) * 100.0, 1)

        # SportyBet Multiple Bonus & Payout
        bonus_pct = BetCalculator.calculate_sportybet_bonus_percentage(len(selected_legs))
        calc_res = BetCalculator.calculate_accumulator([leg.odds for leg in selected_legs], stake=request.stake_amount)
        recommended_stake = RiskProfileManager.calculate_kelly_stake(
            estimated_joint_probability=joint_prob_pct,
            total_odds=total_odds,
            bankroll=request.stake_amount * 10.0,
            profile=request.risk_profile,
        )

        # Build Markdown Summary
        summary = cls._format_summary(
            request=request,
            selected_legs=selected_legs,
            total_odds=total_odds,
            joint_prob_pct=joint_prob_pct,
            slip_ev_pct=slip_ev_pct,
            calc_res=calc_res,
            warnings=warnings,
        )

        return BetConstructionResult(
            request_id=request.request_id,
            success=True,
            status_code=status_code,
            risk_profile_applied=request.risk_profile,
            selected_candidates=selected_legs,
            total_combined_odds=total_odds,
            estimated_joint_probability=joint_prob_pct,
            estimated_slip_ev=slip_ev_pct,
            is_heuristic_ev=True,
            recommended_stake=recommended_stake,
            sportybet_bonus_pct=bonus_pct,
            estimated_total_payout=calc_res["total_payout"],
            total_candidates_evaluated=total_evaluated,
            accepted_count=len(selected_legs),
            rejected_candidates=rejected,
            optimization_warnings=warnings,
            fallback_applied=(status_code != ConstructionStatusCode.OPTIMAL or len(warnings) > 0),
            explanation_summary=summary,
            debug_metadata={
                "desired_count": request.desired_game_count,
                "target_odds": request.target_combined_odds,
                "profile": request.risk_profile.value,
            },
        )

    @classmethod
    def _build_empty_result(
        cls,
        request: BetConstructionRequest,
        status_code: ConstructionStatusCode,
        message: str,
        rejected: Optional[List] = None,
        total_evaluated: int = 0,
        warnings: Optional[List[str]] = None,
    ) -> BetConstructionResult:
        """Helper to construct an empty/failed BetConstructionResult."""
        return BetConstructionResult(
            request_id=request.request_id,
            success=False,
            status_code=status_code,
            risk_profile_applied=request.risk_profile,
            selected_candidates=[],
            total_combined_odds=1.0,
            estimated_joint_probability=0.0,
            estimated_slip_ev=0.0,
            is_heuristic_ev=True,
            recommended_stake=0.0,
            sportybet_bonus_pct=0.0,
            estimated_total_payout=0.0,
            total_candidates_evaluated=total_evaluated,
            accepted_count=0,
            rejected_candidates=rejected or [],
            optimization_warnings=warnings or [message],
            fallback_applied=True,
            explanation_summary=f"⚠️ *Bet Construction Notice:* {message}",
        )

    @classmethod
    def _format_summary(
        cls,
        request: BetConstructionRequest,
        selected_legs: List[SelectedBetLeg],
        total_odds: float,
        joint_prob_pct: float,
        slip_ev_pct: float,
        calc_res: dict,
        warnings: List[str],
    ) -> str:
        """Formats clean user-facing Telegram Markdown summary."""
        lines = [
            "🛡️ *OPTIMIZED BETSLIP & RISK SUMMARY*",
            "━━━━━━━━━━━━━━━━━━━━",
            f"🎯 *Profile:* `{request.risk_profile.value}` | 📅 *Date:* `{request.target_date}`",
            f"📈 *Accumulator Odds:* `{total_odds:.2f}x` | ⚽ *Games:* {len(selected_legs)}",
            f"🔥 *Estimated Joint Win Prob:* `{joint_prob_pct:.1f}%`",
            f"📊 *Estimated Value Edge:* `+{slip_ev_pct:.1f}%`" if slip_ev_pct > 0 else f"📊 *Estimated Value Edge:* `{slip_ev_pct:.1f}%`",
            "━━━━━━━━━━━━━━━━━━━━",
            "*MATCH SELECTIONS & MARKET PICKS:*",
        ]

        for idx, leg in enumerate(selected_legs, 1):
            time_str = leg.kickoff_time.strftime("%H:%M WAT") if leg.kickoff_time else "Upcoming"
            sport_icon = "⚽" if leg.sport == "Football" else "🏀" if leg.sport == "Basketball" else "🎾" if leg.sport == "Tennis" else "🏒" if leg.sport == "Ice Hockey" else "🏆"
            source_tag = (
                "Consensus" if leg.probability_source == ProbabilitySource.CONSENSUS_HEURISTIC
                else "Model" if leg.probability_source == ProbabilitySource.PREDICTIVE_MODEL
                else "Implied"
            )
            lines.append(
                f"{idx}. {sport_icon} *{leg.fixture}* (_{leg.league}_)\n"
                f"   ⏰ Kickoff: `{time_str}` 🟢\n"
                f"   🎯 Market: *{leg.market_name}* ({leg.outcome_name}) @ `{leg.odds:.2f}`\n"
                f"   🛡️ *Win Prob ({source_tag}):* `{leg.effective_probability_pct:.1f}%` | *Implied:* `{leg.implied_probability_pct:.1f}%`\n"
            )

        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━",
            f"💰 *Stake:* ₦{calc_res.get('stake', request.stake_amount):,.2f}",
            f"🎁 *SportyBet Bonus:* +{calc_res.get('bonus_pct', 0.0)}% (+₦{calc_res.get('bonus_amount', 0.0):,.2f})",
            f"🏆 *Estimated Payout:* *₦{calc_res.get('total_payout', 0.0):,.2f}*",
            "━━━━━━━━━━━━━━━━━━━━",
        ])

        if warnings:
            lines.append("💡 *Optimization Notes:*")
            for w in warnings:
                lines.append(f"• {w}")

        return "\n".join(lines)
