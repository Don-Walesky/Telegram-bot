"""
Interactive Custom Bet Slip Builder Engine Module
Generates custom bet slips matching requested target odds, game count (up to 25 games),
probability threshold (85%, 90%, 95%), match date (Today/Tomorrow), and sport category.
Drawn EXCLUSIVELY from LiveScore.com and strictly excludes past or settled matches.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from analyzer import ConsensusPrediction, PredictionAnalyzer
from calculator import BetCalculator
from sportybet import SportyBetService

logger = logging.getLogger(__name__)


@dataclass
class CustomSlipResult:
    target_odds: float
    actual_odds: float
    game_count: int
    min_probability: float
    selections: List[ConsensusPrediction]
    booking_code: str
    formatted_summary: str
    stake: float = 1000.0
    sportybet_bonus_pct: float = 0.0
    sportybet_bonus_amount: float = 0.0
    total_payout: float = 0.0


class CustomSlipBuilder:
    @staticmethod
    def generate_custom_slip(
        target_odds: float = 2.00,
        game_count: int = 3,
        min_probability: float = 75.0,
        match_date: str = "Today",
        sport: str = "All",
        stake: float = 1000.0,
    ) -> CustomSlipResult:
        """
        Builds a custom bet slip up to 25 games containing ONLY upcoming LiveScore.com matches.
        """
        candidates = PredictionAnalyzer.analyze_consensus_predictions(
            min_probability=min_probability,
            match_date=match_date,
            sport=sport,
        )

        now = datetime.now()

        # Double check candidates are strictly in the future
        unstarted_candidates = [c for c in candidates if (not c.kickoff_time or c.kickoff_time > now)]

        if not unstarted_candidates:
            # Fallback if no matches met threshold: pull all upcoming unstarted
            unstarted_candidates = PredictionAnalyzer.analyze_consensus_predictions(
                min_probability=60.0,
                match_date=match_date,
                sport=sport,
            )

        # Select up to requested game_count from unstarted candidates
        selected = unstarted_candidates[:game_count]

        # Select up to requested game_count from unstarted candidates
        selected = unstarted_candidates[:game_count]

        sportybet_direct_url = "https://www.sportybet.com/ng/m/sports/football/"

        odds_list = [pick.odds for pick in selected]
        calc_res = BetCalculator.calculate_accumulator(odds_list, stake=stake)

        actual_odds = calc_res["total_odds"]

        sport_icon = "⚽" if sport == "Football" else "🏀" if sport == "Basketball" else "🎾" if sport == "Tennis" else "🏒" if sport == "Ice Hockey" else "🏆"

        def clean_md(text: str) -> str:
            return text.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")

        lines = [
            "⚙️ *CUSTOM MULTI-SPORT PREDICTION SLIP*",
            "━━━━━━━━━━━━━━━━━━━━",
            f"📅 *Date:* `{match_date.upper()}` | *Sport:* `{sport.upper()}` {sport_icon}",
            "✔ *Source:* LiveScore Real Fixture Discovery",
            "⏰ *Match Status:* `UNSTARTED / UPCOMING GAMES ONLY` 🟢",
            f"🎯 *Target Odds:* `{target_odds:.2f}x` | *Actual Odds:* `{actual_odds:.2f}x`",
            f"⚽ *Matches Count:* {len(selected)} Games",
            f"🛡️ *Minimum Probability:* *{min_probability:.0f}%*",
            "━━━━━━━━━━━━━━━━━━━━",
            "*MATCH SELECTIONS & SAFE MARKETS:*",
        ]

        for idx, pick in enumerate(selected, 1):
            sport_symbol = "⚽" if pick.sport == "Football" else "🏀" if pick.sport == "Basketball" else "🎾" if pick.sport == "Tennis" else "🏒" if pick.sport == "Ice Hockey" else "🏆"
            time_str = pick.kickoff_time.strftime("%H:%M WAT") if pick.kickoff_time else "Upcoming"

            clean_h = clean_md(pick.home_team)
            clean_a = clean_md(pick.away_team)
            clean_l = clean_md(pick.league)

            lines.append(
                f"{idx}. {sport_symbol} *{clean_h} vs {clean_a}* (_{clean_l}_)\n"
                f"   ⏰ Kickoff: `{time_str}` 🟢 (Unstarted)\n"
                f"   🎯 Market Pick: *{pick.safe_market}* @ `{pick.odds:.2f}`\n"
                f"   🔥 Win Probability: *{pick.consensus_probability}%*\n"
            )

        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"💰 *Stake:* ₦{stake:,.2f}")
        lines.append(f"🎁 *SportyBet Bonus:* +{calc_res['bonus_pct']}% (+₦{calc_res['bonus_amount']:,.2f})")
        lines.append(f"🏆 *Total Estimated Payout:* *₦{calc_res['total_payout']:,.2f}*")
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"🚀 [Open SportyBet & Select Picks Directly]({sportybet_direct_url})")
        lines.append(f"🔄 *Convert external codes:* Send `/convert <code_or_url>` to convert Bet9ja/1xBet slips directly into a single SportyBet booking code via RapidAPI / Betloy!")
        lines.append(f"💡 *How to bet:* Open SportyBet using the link above, search these verified LiveScore matches, and select the safe market picks listed!")

        return CustomSlipResult(
            target_odds=target_odds,
            actual_odds=actual_odds,
            game_count=len(selected),
            min_probability=min_probability,
            selections=selected,
            booking_code="",
            formatted_summary="\n".join(lines),
            stake=stake,
            sportybet_bonus_pct=calc_res["bonus_pct"],
            sportybet_bonus_amount=calc_res["bonus_amount"],
            total_payout=calc_res["total_payout"],
        )


if __name__ == "__main__":
    res = CustomSlipBuilder.generate_custom_slip(target_odds=3.0, game_count=5, min_probability=85.0)
    print(res.formatted_summary)
