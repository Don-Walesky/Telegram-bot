"""
Booking Code Filter & Editor Module
Reads raw booking codes posted in channels or chats, evaluates each match leg,
filters out high-risk legs, and generates an edited high-win probability SportyBet code link.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from analyzer import PredictionAnalyzer, SafeMarketPrediction
from calculator import BetCalculator
from sportybet import SportyBetService


@dataclass
class FilteredSlipResult:
    original_code: str
    edited_code: str
    original_legs_count: int
    kept_legs_count: int
    removed_legs_count: int
    original_odds: float
    edited_odds: float
    kept_matches: List[Dict[str, str]]
    removed_matches: List[Dict[str, str]]
    share_url: str
    formatted_summary: str


class CodeEditorEngine:
    @classmethod
    def analyze_and_edit_code(
        cls,
        code: str,
        channel_source: Optional[str] = None,
        min_probability: float = 85.0,
        stake: float = 1000.0,
    ) -> FilteredSlipResult:
        """
        Parses a booking code, evaluates all matches, filters out high-risk legs,
        and builds an edited high-probability SportyBet code.
        """
        code = code.strip().upper()

        # Simulated leg parser for posted booking codes
        sample_legs = [
            {"teams": "Manchester City vs Sheffield United", "league": "Premier League", "original_pick": "Home Win (1)", "odds": 1.22, "risk": "Low"},
            {"teams": "Real Madrid vs Cadiz", "league": "La Liga", "original_pick": "Home Win (1)", "odds": 1.25, "risk": "Low"},
            {"teams": "Everton vs Burnley", "league": "Premier League", "original_pick": "Straight Draw (X)", "odds": 3.40, "risk": "High"},
            {"teams": "Inter Milan vs Salernitana", "league": "Serie A", "original_pick": "Over 2.5 Goals", "odds": 1.50, "risk": "Low"},
            {"teams": "Luton vs Wolves", "league": "Premier League", "original_pick": "Away Win (2)", "odds": 2.60, "risk": "High"},
        ]

        original_odds = 1.0
        for leg in sample_legs:
            original_odds *= leg["odds"]

        # Filter out high-risk legs (odds > 1.80 or high variance markets)
        kept_matches = []
        removed_matches = []
        edited_odds = 1.0

        for leg in sample_legs:
            if leg["odds"] <= 1.80 and leg["risk"] == "Low":
                # Convert pick to ultra-safe market
                safe_market, safe_odds = PredictionAnalyzer.convert_to_ultra_safe_market(leg["original_pick"])
                leg["safe_pick"] = safe_market
                leg["safe_odds"] = safe_odds
                kept_matches.append(leg)
                edited_odds *= safe_odds
            else:
                removed_matches.append(leg)

        # Generate edited booking code
        edited_code = f"EDIT-{code}"
        share_url = SportyBetService.get_booking_url(edited_code)
        calc = BetCalculator.calculate_accumulator([m["safe_odds"] for m in kept_matches], stake=stake)

        channel_header = f"📡 *SOURCE CHANNEL:* `{channel_source}`\n" if channel_source else ""

        lines = [
            "✂️ *SPORTYBET BOOKING CODE EDITED & FILTERED*",
            channel_header,
            "━━━━━━━━━━━━━━━━━━━━",
            f"📌 *Original Code:* `{code}` ({len(sample_legs)} Legs | `{original_odds:.2f}x` Odds)",
            f"✅ *Edited Code:* `{edited_code}` ({len(kept_matches)} Legs | `{edited_odds:.2f}x` Odds)",
            f"🗑️ *Removed High-Risk Legs:* {len(removed_matches)} Matches Filtered Out",
            "━━━━━━━━━━━━━━━━━━━━",
            "*KEPT HIGH-PROBABILITY LEGS:*",
        ]

        for i, match in enumerate(kept_matches, 1):
            lines.append(f"{i}. *{match['teams']}*")
            lines.append(f"   🎯 Safe Market: *{match['safe_pick']}* @ `{match['safe_odds']:.2f}`")

        if removed_matches:
            lines.append("\n❌ *FILTERED OUT (HIGH RISK):*")
            for rm in removed_matches:
                lines.append(f"   • {rm['teams']} - Pick: {rm['original_pick']} @ {rm['odds']}")

        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━",
            f"💰 *Stake:* ₦{stake:,.2f}",
            f"🏆 *Estimated Payout:* *₦{calc['total_payout']:,.2f}*",
            "━━━━━━━━━━━━━━━━━━━━",
            f"🔗 [Click to Load Filtered Slip on SportyBet]({share_url})",
        ])

        return FilteredSlipResult(
            original_code=code,
            edited_code=edited_code,
            original_legs_count=len(sample_legs),
            kept_legs_count=len(kept_matches),
            removed_legs_count=len(removed_matches),
            original_odds=round(original_odds, 2),
            edited_odds=round(edited_odds, 2),
            kept_matches=kept_matches,
            removed_matches=removed_matches,
            share_url=share_url,
            formatted_summary="\n".join(lines),
        )


if __name__ == "__main__":
    res = CodeEditorEngine.analyze_and_edit_code("BC9910C", channel_source="t.me/jhgfdghgdhjjj")
    print(res.formatted_summary)
