"""
SportyBet Catalog & Event Matcher Module
Queries SportyBet's live schedule & market catalog.
Fuzzy matches LiveScore discovered events against SportyBet's official event IDs,
market IDs, outcome IDs, and live decimal odds.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from typing import Dict, List, Optional
import httpx

from livescore_client import DiscoveredFixture

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.sportybet.com/ng/",
    "Origin": "https://www.sportybet.com",
    "Clientid": "web",
}


@dataclass
class MappedSportyBetSelection:
    event_id: str
    home_team: str
    away_team: str
    league: str
    sport: str
    kickoff_time: Optional[datetime]
    market_id: str
    market_name: str
    outcome_id: str
    outcome_name: str
    odds: float
    specifier: Optional[str] = None
    match_confidence: float = 1.0


class SportyBetCatalogService:
    POPULAR_EVENTS_URL = "https://www.sportybet.com/api/ng/factsCenter/popularEvents"
    QUERY_EVENTS_URL = "https://www.sportybet.com/api/ng/factsCenter/query"

    @classmethod
    def fetch_sportybet_catalog(cls, sport: str = "Football") -> List[Dict]:
        """
        Queries SportyBet live catalog for scheduled upcoming events.
        Handles 'All' sports by iterating through Football, Basketball, Tennis, and Ice Hockey.
        """
        sport_id_map = {
            "football": "sr:sport:1",
            "soccer": "sr:sport:1",
            "basketball": "sr:sport:2",
            "tennis": "sr:sport:5",
            "ice hockey": "sr:sport:4",
            "hockey": "sr:sport:4",
        }

        if sport.lower() == "all":
            target_sports = ["football", "basketball", "tennis", "ice hockey"]
        else:
            target_sports = [sport.lower()]

        all_events: List[Dict] = []

        for target in target_sports:
            sport_id = sport_id_map.get(target, "sr:sport:1")
            endpoints = [cls.POPULAR_EVENTS_URL, cls.QUERY_EVENTS_URL]

            for url in endpoints:
                try:
                    with httpx.Client(timeout=8.0) as client:
                        params = {
                            "sportId": sport_id,
                            "_t": str(int(datetime.now().timestamp() * 1000)),
                        }
                        resp = client.get(url, params=params, headers=HEADERS)
                        logger.info(f"SportyBet catalog query [{target}] [{url}]: HTTP {resp.status_code}")
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get("bizCode") == 10000 and data.get("data"):
                                raw_items = data.get("data", [])
                                flattened = cls._flatten_sportybet_events(raw_items)
                                if flattened:
                                    all_events.extend(flattened)
                                    break
                except Exception as e:
                    logger.warning(f"SportyBet catalog fetch error for {target} [{url}]: {e}")

        logger.info(f"SportyBet catalog query finished. Flattened event count: {len(all_events)}")
        return all_events

    @classmethod
    def _flatten_sportybet_events(cls, items: List[Dict]) -> List[Dict]:
        """
        Flattens raw SportyBet response items (which can contain tournament wrappers or nested event arrays).
        """
        events: List[Dict] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            # If item contains a nested 'events' array (tournament wrapper)
            if "events" in item and isinstance(item["events"], list):
                for sub_event in item["events"]:
                    if isinstance(sub_event, dict):
                        events.append(sub_event)
            elif "homeTeamName" in item or "eventId" in item:
                events.append(item)

        return events

    @classmethod
    def _normalize_name(cls, name: str) -> str:
        import re
        text = name.lower()
        text = re.sub(r"\b(fc|sc|club|cd|sd|kv)\b", "", text)
        text = re.sub(r"\bunited\b", "utd", text)
        text = re.sub(r"\b(saint|st\.)\b", "st", text)
        return " ".join(text.split())

    @classmethod
    def similarity_score(cls, a: str, b: str) -> float:
        norm_a = cls._normalize_name(a)
        norm_b = cls._normalize_name(b)
        return SequenceMatcher(None, norm_a, norm_b).ratio()

    @classmethod
    def match_fixture(
        cls, fixture: DiscoveredFixture, sportybet_events: List[Dict]
    ) -> Optional[Dict]:
        """
        Fuzzy matches a LiveScore fixture against SportyBet catalog events.
        """
        best_match = None
        best_score = 0.0

        for sb_event in sportybet_events:
            sb_home = sb_event.get("homeTeamName") or sb_event.get("homeTeam", {}).get("name", "")
            sb_away = sb_event.get("awayTeamName") or sb_event.get("awayTeam", {}).get("name", "")

            home_sim = cls.similarity_score(fixture.home_team, sb_home)
            away_sim = cls.similarity_score(fixture.away_team, sb_away)
            avg_sim = (home_sim + away_sim) / 2.0

            # Check kickoff time alignment if available
            est_start = sb_event.get("estimateStartTime")
            time_match = True
            if est_start and fixture.kickoff_time:
                sb_dt = datetime.fromtimestamp(est_start / 1000.0)
                diff_minutes = abs((sb_dt - fixture.kickoff_time).total_seconds()) / 60.0
                if diff_minutes > 180:  # Allow max 3 hours time zone offset/delay
                    time_match = False

            if time_match and avg_sim > best_score and avg_sim >= 0.65:
                best_score = avg_sim
                best_match = sb_event

        if best_match:
            h_name = best_match.get("homeTeamName", "")
            a_name = best_match.get("awayTeamName", "")
            logger.info(
                f"Matched '{fixture.home_team} vs {fixture.away_team}' "
                f"to SportyBet '{h_name} vs {a_name}' (Confidence: {best_score:.2f})"
            )
            return best_match

        logger.info(
            f"Unmapped event: Could not match '{fixture.home_team} vs {fixture.away_team}' to SportyBet catalog."
        )
        return None

    @classmethod
    def extract_selections_from_event(
        cls, sb_event: Dict
    ) -> List[MappedSportyBetSelection]:
        """
        Extracts available market outcomes and live decimal odds from a SportyBet catalog event.
        """
        selections: List[MappedSportyBetSelection] = []
        event_id = str(sb_event.get("eventId") or sb_event.get("id") or "")
        home = sb_event.get("homeTeamName", "")
        away = sb_event.get("awayTeamName", "")
        league = sb_event.get("tournament", {}).get("name", "League")
        sport = sb_event.get("sport", {}).get("name", "Football")

        est_start = sb_event.get("estimateStartTime")
        kickoff_dt = datetime.fromtimestamp(est_start / 1000.0) if est_start else None

        markets = sb_event.get("markets", [])
        for mkt in markets:
            mkt_id = str(mkt.get("id") or mkt.get("marketId") or "")
            mkt_name = mkt.get("desc") or mkt.get("name") or "Market"
            specifier = mkt.get("specifier")

            for outcome in mkt.get("outcomes", []):
                outcome_id = str(outcome.get("id") or outcome.get("outcomeId") or "")
                outcome_name = outcome.get("desc") or outcome.get("name") or ""
                odds_val = float(outcome.get("odds", 0.0))

                if odds_val > 1.0:
                    selections.append(
                        MappedSportyBetSelection(
                            event_id=event_id,
                            home_team=home,
                            away_team=away,
                            league=league,
                            sport=sport,
                            kickoff_time=kickoff_dt,
                            market_id=mkt_id,
                            market_name=mkt_name,
                            outcome_id=outcome_id,
                            outcome_name=outcome_name,
                            odds=odds_val,
                            specifier=specifier,
                        )
                    )

        return selections
