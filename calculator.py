"""
Betting & Odds Calculator Module
Includes SportyBet bonus calculation, accumulator returns, and Kelly Criterion stake sizing.
"""

from typing import List, Dict, Tuple


class BetCalculator:
    @staticmethod
    def calculate_sportybet_bonus_percentage(legs_count: int, min_odds_met: bool = True) -> float:
        """
        Calculates estimated SportyBet Multiple Bonus percentage based on legs count.
        SportyBet bonus starts at 3 legs (~3%-5%) up to 30+ legs (1000%+).
        """
        if not min_odds_met or legs_count < 3:
            return 0.0

        # Tiered bonus calculation structure matching SportyBet bonus ladder
        if legs_count == 3:
            return 3.0
        elif legs_count == 4:
            return 5.0
        elif legs_count == 5:
            return 10.0
        elif legs_count <= 10:
            return 10.0 + (legs_count - 5) * 5.0  # 6: 15%, 7: 20%, 8: 25%, 9: 30%, 10: 35%
        elif legs_count <= 20:
            return 35.0 + (legs_count - 10) * 10.0  # Up to 135% at 20 legs
        else:
            return min(1000.0, 135.0 + (legs_count - 20) * 20.0)

    @staticmethod
    def calculate_accumulator(
        odds_list: List[float], stake: float = 1000.0, min_odds_for_bonus: float = 1.20
    ) -> Dict[str, float]:
        """
        Calculate total odds, gross payout, bonus, and net payout.
        """
        if not odds_list or stake <= 0:
            return {
                "total_odds": 0.0,
                "gross_payout": 0.0,
                "bonus_pct": 0.0,
                "bonus_amount": 0.0,
                "total_payout": 0.0,
                "potential_profit": 0.0,
            }

        total_odds = 1.0
        qualifying_legs = 0

        for odds in odds_list:
            total_odds *= odds
            if odds >= min_odds_for_bonus:
                qualifying_legs += 1

        gross_payout = stake * total_odds
        gross_winnings = gross_payout - stake

        bonus_pct = BetCalculator.calculate_sportybet_bonus_percentage(qualifying_legs)
        bonus_amount = gross_winnings * (bonus_pct / 100.0)

        total_payout = gross_payout + bonus_amount
        potential_profit = total_payout - stake

        return {
            "total_odds": round(total_odds, 2),
            "gross_payout": round(gross_payout, 2),
            "bonus_pct": round(bonus_pct, 1),
            "bonus_amount": round(bonus_amount, 2),
            "total_payout": round(total_payout, 2),
            "potential_profit": round(potential_profit, 2),
        }

    @staticmethod
    def kelly_criterion(odds: float, estimated_win_probability: float, bankroll: float = 10000.0, fraction: float = 0.25) -> Tuple[float, float]:
        """
        Calculate recommended stake using Fractional Kelly Criterion.
        fraction: 0.25 = Quarter Kelly (safe bankroll management).
        Returns: (recommended_stake, stake_percentage_of_bankroll)
        """
        b = odds - 1.0
        p = estimated_win_probability
        q = 1.0 - p

        if b <= 0 or p <= 0:
            return 0.0, 0.0

        full_kelly = (b * p - q) / b

        if full_kelly <= 0:
            return 0.0, 0.0  # Negative edge - do not bet

        recommended_fractional_kelly = full_kelly * fraction
        stake = bankroll * recommended_fractional_kelly
        stake_pct = recommended_fractional_kelly * 100.0

        return round(stake, 2), round(stake_pct, 2)


if __name__ == "__main__":
    odds = [1.50, 1.80, 2.10, 1.35, 1.70]
    result = BetCalculator.calculate_accumulator(odds, stake=2000)
    print("Accumulator Test Result:", result)
    stake, pct = BetCalculator.kelly_criterion(odds=2.00, estimated_win_probability=0.55, bankroll=50000)
    print(f"Kelly Stake: ₦{stake:,.2f} ({pct}% of bankroll)")
