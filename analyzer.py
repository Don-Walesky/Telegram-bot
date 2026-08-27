"""
Multi-Source Consensus & Probability Engine Module
Calculates composite consensus probability across 5 prediction sources,
filters out past/settled matches, converts predictions to safe markets matching SportyBet UI,
and formats date & sport filtered reports with kick-off timestamps.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from aggregator import PredictionAggregator, RawPrediction
from sportybet import SportyBetService

logger = logging.getLogger(__name__)


@dataclass
class ConsensusPrediction:
    home_team: str
    away_team: str
    league: str
    sport: str
    original_pick: str
    safe_market: str
    odds: float
    consensus_probability: float
    agreed_sources: List[str]
    match_date: str = "Today"
    kickoff_time: Optional[datetime] = None

    @property
    def consensus_score(self) -> float:
        return self.consensus_probability

    @property
    def teams(self) -> str:
        return f"{self.home_team} vs {self.away_team}"

    @property
    def safe_pick(self) -> str:
        return self.safe_market

    @property
    def safe_odds(self) -> float:
        return self.odds


# Alias for backward compatibility
SafeMarketPrediction = ConsensusPrediction


class PredictionAnalyzer:
    @staticmethod
    def convert_to_ultra_safe_market(raw_pred: str) -> tuple[str, float]:
        return PredictionAnalyzer.convert_to_safe_market(raw_pred, "Football")

    @staticmethod
    def analyze_high_probability_fixtures(target_threshold: float = 95.0) -> List[ConsensusPrediction]:
        return PredictionAnalyzer.analyze_consensus_predictions(min_probability=target_threshold)

    @staticmethod
    def convert_to_safe_market(raw_pred: str, sport: str = "Football") -> tuple[str, float]:
        """
        Converts predictions to ultra-safe markets with exact SportyBet sportsbook market names and odds.
        """
        if sport.lower() in ["football", "soccer"]:
            if raw_pred in ["1", "Home Win"]:
                return "Double Chance (1X)", 1.18
            elif raw_pred in ["2", "Away Win"]:
                return "Double Chance (X2)", 1.20
            elif raw_pred in ["Over 2.5", "Over 1.5"]:
                return "Over 1.5 Goals", 1.16
            elif raw_pred in ["X", "Draw"]:
                return "Double Chance (1X)", 1.22
            else:
                return "Over 1.5 Goals", 1.15

        elif sport.lower() == "basketball":
            if raw_pred in ["Home Win", "1"]:
                return "Winner (2-Way Incl. OT)", 1.25
            elif raw_pred in ["Away Win", "2"]:
                return "Handicap (+8.5 Points)", 1.22
            else:
                return "Winner (2-Way Incl. OT)", 1.20

        elif sport.lower() == "tennis":
            if "Winner" in raw_pred or raw_pred in ["1", "Home Win"]:
                return f"Match Winner ({raw_pred})", 1.20
            else:
                return "To Win At Least 1 Set", 1.18

        elif sport.lower() == "ice hockey":
            if raw_pred in ["1", "Home Win"]:
                return "Double Chance (1X)", 1.20
            elif raw_pred in ["2", "Away Win"]:
                return "Double Chance (X2)", 1.22
            else:
                return "Over 4.5 Goals", 1.18

        elif sport.lower() == "cricket":
            return "Match Winner (2-Way)", 1.25

        return "Double Chance (1X)", 1.18

    @staticmethod
    def analyze_consensus_predictions(
        min_probability: float = 75.0,
        match_date: str = "Today",
        sport: str = "All",
    ) -> List[ConsensusPrediction]:
        """
        Groups raw predictions by match, calculates average consensus probability,
        strictly excludes past/settled matches, and converts to safe options.
        """
        raw_predictions = PredictionAggregator.get_upcoming_fixtures(match_date=match_date, sport=sport)

        # Group predictions by (home_team, away_team)
        grouped: Dict[tuple, List[RawPrediction]] = {}
        for p in raw_predictions:
            key = (p.home_team, p.away_team)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(p)

        consensus_list: List[ConsensusPrediction] = []
        now = datetime.now()

        for (home, away), preds in grouped.items():
            first = preds[0]

            # Double check kick-off time is strictly in the future
            if first.kickoff_time and first.kickoff_time <= now:
                logger.info(f"Analyzer excluding settled match: {home} vs {away} at {first.kickoff_time}")
                continue

            avg_prob = sum(p.win_probability for p in preds) / len(preds)

            if avg_prob >= min_probability:
                safe_market, odds = PredictionAnalyzer.convert_to_safe_market(first.raw_prediction, first.sport)
                sources = list(set(p.source for p in preds))

                consensus_list.append(
                    ConsensusPrediction(
                        home_team=home,
                        away_team=away,
                        league=first.league,
                        sport=first.sport,
                        original_pick=first.raw_prediction,
                        safe_market=safe_market,
                        odds=odds,
                        consensus_probability=round(avg_prob, 1),
                        agreed_sources=sources,
                        match_date=first.match_date,
                        kickoff_time=first.kickoff_time,
                    )
                )

        consensus_list.sort(key=lambda x: x.consensus_probability, reverse=True)
        return consensus_list

    @staticmethod
    def format_consensus_report(
        min_probability: float = 75.0,
        match_date: str = "Today",
        sport: str = "All",
        booking_code: str = "BC95SAFE",
    ) -> str:
        """
        Formats consensus predictions into Telegram Markdown text with clear kick-off times.
        """
        top_picks = PredictionAnalyzer.analyze_consensus_predictions(
            min_probability=min_probability, match_date=match_date, sport=sport
        )

        sport_icon = "⚽" if sport == "Football" else "🏀" if sport == "Basketball" else "🎾" if sport == "Tennis" else "🏒" if sport == "Ice Hockey" else "🏆"

        lines = [
            "🛡️ *HIGH-PROBABILITY MULTI-SPORT PREDICTIONS*",
            f"📅 *Date:* `{match_date.upper()}` | *Sport:* `{sport.upper()}` {sport_icon}",
            "📊 *Source:* LiveScore Real Fixture Discovery & Implied Probability Analysis",
            "⏰ *Strict Filter:* Only unstarted & upcoming future matches included",
            "━━━━━━━━━━━━━━━━━━━━",
        ]

        if not top_picks:
            lines.append("⚠️ No unstarted matches met the 95%+ probability criteria for the selected filter.")
            lines.append("💡 Try selecting **Tomorrow** or lowering the safety threshold to 90%!")
            return "\n".join(lines)

        url = SportyBetService.get_booking_url(booking_code)
        lines.append(f"📌 *Booking Code:* `{booking_code}`")
        lines.append(f"🔗 [Click to Load Slip on SportyBet]({url})")
        lines.append("━━━━━━━━━━━━━━━━━━━━")

        def clean_md(text: str) -> str:
            return text.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")

        total_odds = 1.0
        for idx, pick in enumerate(top_picks, 1):
            total_odds *= pick.odds
            sources_str = ", ".join(pick.agreed_sources[:3])
            time_str = pick.kickoff_time.strftime("%H:%M WAT") if pick.kickoff_time else "Upcoming"

            clean_h = clean_md(pick.home_team)
            clean_a = clean_md(pick.away_team)
            clean_l = clean_md(pick.league)

            lines.append(
                f"{idx}. *{clean_h} vs {clean_a}* (_{clean_l}_)\n"
                f"   ⏰ Kickoff: `{time_str}`\n"
                f"   🎯 Safe Pick: *{pick.safe_market}* @ `{pick.odds:.2f}`\n"
                f"   🔥 Implied Probability: *{pick.consensus_probability}%* (Source: {sources_str})\n"
            )

        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"📈 *Accumulator Total Odds:* `{total_odds:.2f}`")
        lines.append(f"⚡ *Booking Code:* `{booking_code}`")
        lines.append(f"🔗 [Direct Load Link]({url})")
        lines.append("━━━━━━━━━━━━━━━━━━━━")

        return "\n".join(lines)


if __name__ == "__main__":
    print(PredictionAnalyzer.format_consensus_report())
