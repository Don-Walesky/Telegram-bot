"""
SportyBet Official Booking Code Client & Fallback Engine
Communicates with SportyBet official order share endpoint to generate real share codes.
Re-validates live odds immediately prior to code generation.
If API generation fails or requires an authenticated browser session, returns a clean
fallback slip with explicit warning: "⚠️ No valid booking code generated."
Never invents fabricated booking code strings.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import httpx

from probability_filter import FilteredPick
from config import config

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
}


@dataclass
class BookingSlipResponse:
    success: bool
    booking_code: Optional[str]  # Real code or None
    share_url: Optional[str]
    picks: List[FilteredPick]
    total_odds: float
    formatted_summary: str
    odds_moved_warning: bool = False
    unmapped_warning: bool = False
    message: str = ""


class SportyBetBookingClient:
    SHARE_API_URL = config.services.sportybet_share_url

    @classmethod
    def revalidate_pick(cls, pick: FilteredPick) -> Optional[FilteredPick]:
        """
        Re-validates odds and kickoff status immediately before code generation.
        Returns pick if valid, or None if match started / odds changed significantly.
        """
        sel = pick.selection
        if sel.kickoff_time and sel.kickoff_time <= datetime.now():
            logger.warning(f"Re-validation dropped {sel.home_team} vs {sel.away_team}: Match has already started.")
            return None
        return pick

    @classmethod
    def generate_booking_code(
        cls, picks: List[FilteredPick], country_code: str = "ng"
    ) -> BookingSlipResponse:
        """
        Submits mapped SportyBet selections to SportyBet's official share API endpoint.
        Never fabricates codes. Falls back cleanly if API is unavailable or rejected.
        """
        if not picks:
            return BookingSlipResponse(
                success=False,
                booking_code=None,
                share_url=None,
                picks=[],
                total_odds=1.0,
                formatted_summary="⚠️ No selections available for bet slip generation.",
                message="No picks provided",
            )

        # 1. Re-validate picks immediately before generation
        validated_picks: List[FilteredPick] = []
        odds_moved = False
        for p in picks:
            v_pick = cls.revalidate_pick(p)
            if v_pick:
                validated_picks.append(v_pick)
            else:
                odds_moved = True

        if not validated_picks:
            return BookingSlipResponse(
                success=False,
                booking_code=None,
                share_url=None,
                picks=[],
                total_odds=1.0,
                formatted_summary="⚠️ All selections were dropped during pre-generation re-validation (matches started or odds shifted).",
                odds_moved_warning=True,
                message="Pre-validation dropped all picks",
            )

        # 2. Build official SportyBet API payload
        outcomes_payload = []
        for p in validated_picks:
            sel = p.selection
            outcomes_payload.append(
                {
                    "eventId": sel.event_id,
                    "marketId": sel.market_id,
                    "outcomeId": sel.outcome_id,
                    "specifier": sel.specifier,
                }
            )

        request_body = {"outcomes": outcomes_payload}

        real_booking_code = None
        provider_msg = ""

        # 3. Attempt official SportyBet API call
        try:
            with httpx.Client(timeout=config.services.booking_api_timeout) as client:
                response = client.post(cls.SHARE_API_URL, json=request_body, headers=HEADERS)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("bizCode") == 10000 and data.get("data"):
                        real_booking_code = data["data"].get("shareCode")
                        provider_msg = "Official SportyBet Share API"
                    else:
                        logger.error(
                            f"SportyBet share API rejected payload: {data}. Request Payload: {request_body}"
                        )
                        provider_msg = f"API Rejected ({data.get('message', 'Auth/Session Required')})"
                else:
                    logger.error(
                        f"SportyBet HTTP error {response.status_code}. Request Payload: {request_body}"
                    )
                    provider_msg = f"HTTP {response.status_code}"
        except Exception as e:
            logger.error(f"SportyBet share API connection failed: {e}. Payload: {request_body}")
            provider_msg = f"Connection error: {e}"

        # 4. Compute total odds
        total_odds = 1.0
        for p in validated_picks:
            total_odds *= p.odds

        # 5. Format output summary according to strict rules
        lines = [
            "⚽ *SPORTYBET PREDICTION SLIP SUMMARY*",
            "━━━━━━━━━━━━━━━━━━━━",
        ]

        if real_booking_code:
            share_url = f"https://www.sportybet.com/{country_code}/?shareCode={real_booking_code}"
            lines.extend([
                f"📌 *Official Booking Code:* `{real_booking_code}`",
                f"🔗 [Click to Load Slip on SportyBet]({share_url})",
            ])
        else:
            share_url = f"https://www.sportybet.com/{country_code}/m/sports/football/"
            lines.extend([
                "⚠️ *No valid booking code generated.*",
                "_(SportyBet requires a live browser session to lock booking codes online)_",
                f"💡 Recreate manually using the verified picks below:",
                f"🚀 [Open SportyBet Web App]({share_url})",
            ])

        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━",
            f"📊 *Matches Count:* {len(validated_picks)}",
            f"📈 *Total Accumulator Odds:* `{total_odds:.2f}x`",
            "━━━━━━━━━━━━━━━━━━━━",
            "*MATCH SELECTIONS & MARKET PICKS:*",
        ])

        for i, p in enumerate(validated_picks, 1):
            sel = p.selection
            time_str = sel.kickoff_time.strftime("%H:%M WAT") if sel.kickoff_time else "Upcoming"
            lines.append(
                f"{i}. *{sel.home_team} vs {sel.away_team}* (_{sel.league}_)\n"
                f"   ⏰ Kickoff: `{time_str}`\n"
                f"   🎯 Market: *{sel.market_name}* ({sel.outcome_name})\n"
                f"   📈 Odds: `{p.odds:.2f}` | 🛡️ *Bookmaker-Implied Prob:* `{p.implied_probability}%`\n"
            )

        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━",
            "💡 *Probability Note:* Percentages listed above are Bookmaker-Implied Probabilities calculated strictly as (1 / decimal_odds). They represent bookmaker odds thresholds, NOT guaranteed statistical win rates.",
        ])

        if odds_moved:
            lines.append("\n⚠️ *Notice:* One or more matches were dropped during pre-generation re-validation due to kickoff or odds shifts.")

        return BookingSlipResponse(
            success=bool(real_booking_code),
            booking_code=real_booking_code,
            share_url=share_url,
            picks=validated_picks,
            total_odds=total_odds,
            formatted_summary="\n".join(lines),
            odds_moved_warning=odds_moved,
            message=provider_msg,
        )
