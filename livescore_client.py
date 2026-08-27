"""
LiveScore Discovery Module
Pulls upcoming, unstarted sport fixtures for Today and Tomorrow across:
Football, Basketball, Tennis, and Ice Hockey.
Strictly filters out started, live, or postponed matches using status codes and kickoff clock patterns.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional
import httpx

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

STARTED_STATUSES = {"FT", "AET", "AP", "HT", "PEN", "AOT", "CANC", "ABD", "INT", "WO"}


def is_unstarted_match(eps: str) -> bool:
    """
    Determines if a LiveScore event status (Eps) represents an unstarted match.
    Matches with Eps="NS", "Sched", or time strings like "20:00" are unstarted.
    Matches with Eps="FT", "HT", "63'", etc. are started or finished.
    """
    if not eps:
        return True
    s = str(eps).strip()
    if s in {"NS", "Sched", "SCHEDULED"}:
        return True
    if s in STARTED_STATUSES or s.endswith("'") or s.isdigit():
        return False
    # Matches kickoff time string e.g. "20:00" or "09:30"
    return bool(re.fullmatch(r"\d{1,2}:\d{2}", s))


@dataclass
class DiscoveredFixture:
    sport: str  # Football, Basketball, Tennis, Ice Hockey
    league: str
    home_team: str
    away_team: str
    kickoff_time: datetime
    status: str  # "NS" (Not Started)
    source: str = "LiveScore"


class LiveScoreClient:
    SPORT_MAP = {
        "football": "soccer",
        "soccer": "soccer",
        "basketball": "basketball",
        "tennis": "tennis",
        "ice hockey": "hockey",
        "hockey": "hockey",
    }

    @classmethod
    def fetch_unstarted_fixtures(
        cls, target_date_str: str = "Today", sport_filter: str = "All"
    ) -> List[DiscoveredFixture]:
        """
        Fetch unstarted fixtures for Today or Tomorrow via multi-candidate LiveScore endpoints.
        """
        now = datetime.now()
        target_dt = now + timedelta(days=1) if target_date_str.lower() == "tomorrow" else now
        date_param = target_dt.strftime("%Y%m%d")

        if sport_filter.lower() == "all":
            sports_to_fetch = ["soccer", "basketball", "tennis", "hockey"]
        else:
            mapped_sport = cls.SPORT_MAP.get(sport_filter.lower(), "soccer")
            sports_to_fetch = [mapped_sport]

        fixtures: List[DiscoveredFixture] = []

        for ls_sport in sports_to_fetch:
            disp_sport = (
                "Football" if ls_sport == "soccer"
                else "Basketball" if ls_sport == "basketball"
                else "Tennis" if ls_sport == "tennis"
                else "Ice Hockey" if ls_sport == "hockey"
                else "Football"
            )

            candidate_urls = [
                f"https://prod-cdn-mev-api.livescore.com/v1/api/app/date/{ls_sport}/{date_param}/1?locale=en",
                f"https://prod-public-api.livescore.com/v1/api/react/date/{ls_sport}/{date_param}/0.00?MD=1",
                f"https://prod-public-api.livescore.com/v1/api/app/date/{ls_sport}/{date_param}/0",
            ]

            fetched_stages = []
            for url in candidate_urls:
                try:
                    with httpx.Client(timeout=8.0) as client:
                        resp = client.get(url, headers=HEADERS)
                        logger.info(f"LiveScore fetch {ls_sport} [{url}]: HTTP {resp.status_code}")
                        if resp.status_code == 200:
                            data = resp.json()
                            fetched_stages = data.get("Stages", [])
                            if fetched_stages:
                                break
                except Exception as e:
                    logger.warning(f"LiveScore candidate URL error [{url}]: {e}")

            for stage in fetched_stages:
                league_name = stage.get("Snm", "")
                country_name = stage.get("Cnm", "")
                full_league = f"{country_name} {league_name}".strip()

                for ev in stage.get("Events", []):
                    eps = ev.get("Eps", "")
                    if is_unstarted_match(eps):
                        t1_list = ev.get("T1", [{}])
                        t2_list = ev.get("T2", [{}])
                        h_team = t1_list[0].get("Nm", "") if t1_list else ""
                        a_team = t2_list[0].get("Nm", "") if t2_list else ""
                        esd = str(ev.get("Esd", ""))

                        kickoff_dt = None
                        if len(esd) == 14:
                            try:
                                kickoff_dt = datetime.strptime(esd, "%Y%m%d%H%M%S")
                            except Exception:
                                pass

                        if not kickoff_dt:
                            kickoff_dt = target_dt + timedelta(hours=2)

                        now = datetime.now()
                        if h_team and a_team and kickoff_dt > now:
                            fixtures.append(
                                DiscoveredFixture(
                                    sport=disp_sport,
                                    league=full_league if full_league else disp_sport,
                                    home_team=h_team,
                                    away_team=a_team,
                                    kickoff_time=kickoff_dt,
                                    status="NS",
                                )
                            )

        logger.info(
            f"LiveScore discovery complete. Total unstarted fixtures found: {len(fixtures)}"
        )
        return fixtures
