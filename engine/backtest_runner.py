"""
Historical Backtesting & Calibration Engine Module
Simulates historical bet execution against actual settled match scores, computing
Brier score calibration, win rates, simulated ROI, and maximum drawdown with zero lookahead bias.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class LegBacktestResult:
    candidate_id: str
    event_id: str
    fixture: str
    market_name: str
    outcome_name: str
    odds: float
    model_probability: float
    won: bool
    brier_loss: float


@dataclass
class SlipBacktestResult:
    request_id: str
    total_odds: float
    stake: float
    legs: List[LegBacktestResult]
    all_legs_won: bool
    payout: float
    profit: float


@dataclass
class BacktestSummaryReport:
    total_slips: int
    won_slips: int
    slip_win_rate_pct: float
    total_legs: int
    won_legs: int
    leg_hit_rate_pct: float
    mean_brier_score: float
    total_staked: float
    total_returned: float
    net_profit: float
    roi_pct: float
    max_drawdown_pct: float
    slips: List[SlipBacktestResult] = field(default_factory=list)


class BacktestRunner:
    @staticmethod
    def evaluate_selection_outcome(
        market_name: str,
        outcome_name: str,
        home_score: int,
        away_score: int,
    ) -> Optional[bool]:
        """
        Determines whether a selection won based on final home and away scores.
        Returns:
            True if won, False if lost, None if market cannot be deterministically resolved.
        """
        m_lower = market_name.lower().strip()
        o_lower = outcome_name.lower().strip()

        # 1. Double Chance
        if "double chance" in m_lower or o_lower in ["1x", "12", "x2"]:
            if "1x" in o_lower or "1/x" in o_lower:
                return home_score >= away_score
            elif "x2" in o_lower or "x/2" in o_lower:
                return away_score >= home_score
            elif "12" in o_lower or "1/2" in o_lower:
                return home_score != away_score

        # 2. Over / Under Goals
        total_goals = home_score + away_score
        if "over 1.5" in m_lower or "over 1.5" in o_lower:
            return total_goals > 1.5
        if "over 2.5" in m_lower or "over 2.5" in o_lower:
            return total_goals > 2.5
        if "under 2.5" in m_lower or "under 2.5" in o_lower:
            return total_goals < 2.5
        if "under 3.5" in m_lower or "under 3.5" in o_lower:
            return total_goals < 3.5

        # 3. 1X2 Match Winner
        if "1x2" in m_lower or "winner" in m_lower:
            if o_lower in ["1", "home", "home win"]:
                return home_score > away_score
            elif o_lower in ["2", "away", "away win"]:
                return away_score > home_score
            elif o_lower in ["x", "draw"]:
                return home_score == away_score

        # 4. Draw No Bet (DNB)
        if "draw no bet" in m_lower or "dnb" in m_lower:
            if home_score == away_score:
                return None  # Push / Void
            if o_lower in ["1", "home"]:
                return home_score > away_score
            if o_lower in ["2", "away"]:
                return away_score > home_score

        # 5. Both Teams to Score (GG / NG)
        if "both teams to score" in m_lower or "gg" in m_lower or "btts" in m_lower:
            if "yes" in o_lower or "gg" in o_lower:
                return home_score > 0 and away_score > 0
            if "no" in o_lower or "ng" in o_lower:
                return home_score == 0 or away_score == 0

        return None

    @classmethod
    def run_backtest(
        cls,
        simulated_slips: List[Dict],
        settlements: Dict[str, Dict],
    ) -> BacktestSummaryReport:
        """
        Executes historical backtest over a series of generated slips against match settlements.

        simulated_slips: List of dicts with keys: 'request_id', 'stake', 'legs'
                         where each leg is a dict with: 'candidate_id', 'event_id', 'fixture',
                         'market_name', 'outcome_name', 'odds', 'model_probability'
        settlements: Dict mapping event_id -> {'home_score': int, 'away_score': int}
        """
        total_slips = len(simulated_slips)
        won_slips = 0
        total_legs = 0
        won_legs = 0
        brier_scores: List[float] = []

        total_staked = 0.0
        total_returned = 0.0
        peak_capital = 0.0
        current_capital = 0.0
        max_drawdown = 0.0

        evaluated_slips: List[SlipBacktestResult] = []

        for slip in simulated_slips:
            stake = slip.get("stake", 1000.0)
            total_staked += stake
            current_capital -= stake

            legs_data = slip.get("legs", [])
            total_odds = 1.0
            slip_legs_won = True
            evaluated_legs: List[LegBacktestResult] = []

            for leg in legs_data:
                total_legs += 1
                ev_id = leg.get("event_id")
                odds = leg.get("odds", 1.0)
                model_p = leg.get("model_probability", 0.80)
                total_odds *= odds

                settle = settlements.get(ev_id)
                if not settle:
                    # Unsettled or missing score treated as loss for strict backtesting
                    won = False
                else:
                    won_res = cls.evaluate_selection_outcome(
                        market_name=leg.get("market_name", ""),
                        outcome_name=leg.get("outcome_name", ""),
                        home_score=settle["home_score"],
                        away_score=settle["away_score"],
                    )
                    won = bool(won_res) if won_res is not None else False

                if won:
                    won_legs += 1
                else:
                    slip_legs_won = False

                actual_outcome = 1.0 if won else 0.0
                brier = (model_p - actual_outcome) ** 2
                brier_scores.append(brier)

                evaluated_legs.append(
                    LegBacktestResult(
                        candidate_id=leg.get("candidate_id", ""),
                        event_id=ev_id or "",
                        fixture=leg.get("fixture", ""),
                        market_name=leg.get("market_name", ""),
                        outcome_name=leg.get("outcome_name", ""),
                        odds=odds,
                        model_probability=model_p,
                        won=won,
                        brier_loss=round(brier, 4),
                    )
                )

            payout = 0.0
            if slip_legs_won and len(evaluated_legs) > 0:
                won_slips += 1
                payout = stake * total_odds
                total_returned += payout
                current_capital += payout

            profit = payout - stake
            peak_capital = max(peak_capital, current_capital)
            drawdown = (peak_capital - current_capital) if peak_capital > 0 else 0.0
            max_drawdown = max(max_drawdown, drawdown)

            evaluated_slips.append(
                SlipBacktestResult(
                    request_id=slip.get("request_id", ""),
                    total_odds=round(total_odds, 2),
                    stake=stake,
                    legs=evaluated_legs,
                    all_legs_won=slip_legs_won,
                    payout=round(payout, 2),
                    profit=round(profit, 2),
                )
            )

        mean_brier = sum(brier_scores) / len(brier_scores) if brier_scores else 0.0
        net_profit = total_returned - total_staked
        roi_pct = (net_profit / total_staked * 100.0) if total_staked > 0 else 0.0
        drawdown_pct = (max_drawdown / total_staked * 100.0) if total_staked > 0 else 0.0

        return BacktestSummaryReport(
            total_slips=total_slips,
            won_slips=won_slips,
            slip_win_rate_pct=round((won_slips / total_slips * 100.0) if total_slips > 0 else 0.0, 2),
            total_legs=total_legs,
            won_legs=won_legs,
            leg_hit_rate_pct=round((won_legs / total_legs * 100.0) if total_legs > 0 else 0.0, 2),
            mean_brier_score=round(mean_brier, 4),
            total_staked=round(total_staked, 2),
            total_returned=round(total_returned, 2),
            net_profit=round(net_profit, 2),
            roi_pct=round(roi_pct, 2),
            max_drawdown_pct=round(drawdown_pct, 2),
            slips=evaluated_slips,
        )
