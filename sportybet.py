"""
SportyBet Booking Code Generator & Parser Module
Handles generating new booking codes and parsing/extracting booking codes from text messages.
"""

import re
import random
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ParsedBookingCode:
    booking_code: str
    country_code: str
    share_url: str
    is_valid_format: bool


class SportyBetService:
    # Regex pattern to match SportyBet booking codes (e.g., BC12345, CST8821, EDIT-BC9910C, or 5-10 alphanumeric codes)
    CODE_REGEX = re.compile(r"\b(?:BC|CST|EDIT)[-_]?[A-Z0-9]{4,10}\b|\b(?=[A-Z0-9]*\d)[A-Z0-9]{5,10}\b", re.IGNORECASE)

    @staticmethod
    def get_booking_url(code: str, country_code: str = "ng") -> str:
        """
        Generate a direct shareable link for a SportyBet booking code.
        Supported country codes: ng (Nigeria), gh (Ghana), ke (Kenya), ug (Uganda), tz (Tanzania), zm (Zambia).
        """
        code_clean = code.strip().upper()
        domain_map = {
            "ng": "https://www.sportybet.com/ng/",
            "gh": "https://www.sportybet.com/gh/",
            "ke": "https://www.sportybet.com/ke/",
            "ug": "https://www.sportybet.com/ug/",
            "tz": "https://www.sportybet.com/tz/",
            "zm": "https://www.sportybet.com/zm/",
        }
        base_url = domain_map.get(country_code.lower(), domain_map["ng"])
        return f"{base_url}?shareCode={code_clean}"

    @classmethod
    def parse_booking_code(cls, raw_text: str, country_code: str = "ng") -> Optional[ParsedBookingCode]:
        """
        Parses and extracts a SportyBet booking code from any text message or channel post.
        """
        text = raw_text.strip()
        matches = cls.CODE_REGEX.findall(text)

        if not matches:
            return None

        # Take first matched code
        code_found = matches[0].upper()
        share_url = cls.get_booking_url(code_found, country_code=country_code)

        return ParsedBookingCode(
            booking_code=code_found,
            country_code=country_code,
            share_url=share_url,
            is_valid_format=True,
        )

    @classmethod
    def generate_booking_code(cls, prefix: str = "BC") -> str:
        """
        Generates a booking code identifier for prediction slips.
        """
        rand_suffix = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=5))
        return f"{prefix.upper()}{rand_suffix}"

    @classmethod
    def convert_external_code(
        cls,
        code: str,
        from_bookmaker: str = "bet9ja",
        country_code: str = "ng",
    ):
        """
        Convert an external bookmaker code (Bet9ja, 1xBet, 22Bet, etc.) to a SportyBet booking code.
        """
        from code_converter import BetCodeConverterService
        return BetCodeConverterService.convert_code_to_sportybet(
            source_code=code,
            source_bookmaker=from_bookmaker,
            destination_bookmaker="sportybet",
            country_code=country_code,
        )

    @staticmethod
    def format_slip_summary(
        booking_code: str,
        matches: List[Dict[str, str]],
        stake: float = 1000.0,
        country_code: str = "ng",
        currency_symbol: str = "₦",
    ) -> str:
        """
        Format a professional betting slip summary for Telegram messages.
        """
        booking_code = booking_code.strip().upper()
        share_url = SportyBetService.get_booking_url(booking_code, country_code)

        total_odds = 1.0
        lines = [
            f"⚽ *SPORTYBET MATCH SLIP PREVIEW*",
            f"📌 *Code / Ref:* `{booking_code}`",
            f"🔗 [Load Code on SportyBet]({share_url})",
            "━━━━━━━━━━━━━━━━━━━━",
        ]

        for i, match in enumerate(matches, 1):
            teams = match.get("teams", "Team A vs Team B")
            selection = match.get("selection", "1X2")
            odds = float(match.get("odds", 1.50))
            league = match.get("league", "")
            time_str = match.get("time", "")

            total_odds *= odds

            league_header = f" _{league}_" if league else ""
            time_header = f" 🕒 {time_str}" if time_str else ""
            lines.append(f"{i}. *{teams}*{league_header}{time_header}")
            lines.append(f"   🎯 Pick: *{selection}* @ `{odds:.2f}`")

        # Calculate estimated returns
        est_return = stake * total_odds

        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━",
            f"📊 *Total Matches:* {len(matches)}",
            f"📈 *Total Odds:* `{total_odds:.2f}`",
            f"💰 *Stake:* {currency_symbol}{stake:,.2f}",
            f"🏆 *Est. Payout:* {currency_symbol}{est_return:,.2f}",
            "━━━━━━━━━━━━━━━━━━━━",
            f"💡 *Note:* If loading a real code created on SportyBet, click the link above. For bot-generated prediction picks, select these picks directly on SportyBet!",
        ])

        return "\n".join(lines)


if __name__ == "__main__":
    new_code = SportyBetService.generate_booking_code()
    print(f"Generated Code: {new_code}")
