"""
LiveScore Discovery Module
Pulls upcoming, unstarted sport fixtures for Today and Tomorrow across:
Football, Basketball, Tennis, and Ice Hockey.
Strictly filters out started, live, or postponed matches.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


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
        Fetch unstarted (NS) fixtures for Today or Tomorrow.
        """
        now = datetime.now()
        target_dt = now + timedelta(days=1) if target_date_str.lower() == "tomorrow" else now
        date_param = target_dt.strftime("%Y%m%d")

        sports_to_fetch = []
        if sport_filter.lower() == "all":
            sports_to_fetch = ["soccer", "basketball", "tennis", "hockey"]
        else:
            mapped_sport = cls.SPORT_MAP.get(sport_filter.lower(), "soccer")
            sports_to_fetch = [mapped_sport]

        fixtures: List[DiscoveredFixture] = []

        for ls_sport in sports_to_fetch:
            url = f"https://prod-public-api.livescore.com/v1/api/app/date/{ls_sport}/{date_param}/0"
            try:
                with httpx.Client(timeout=8.0) as client:
                    resp = client.get(url, headers=HEADERS)
                    if resp.status_code == 200:
                        data = resp.json()
                        for stage in data.get("Stages", []):
                            league_name = stage.get("Snm", "")
                            country_name = stage.get("Cnm", "")
                            full_league = f"{country_name} {league_name}".strip()

                            disp_sport = (
                                "Football" if ls_sport == "soccer"
                                else "Basketball" if ls_sport == "basketball"
                                else "Tennis" if ls_sport == "tennis"
                                else "Ice Hockey" if ls_sport == "hockey"
                                else "Football"
                            )

                            for ev in stage.get("Events", []):
                                status = ev.get("Eps", "")
                                # Filter strictly for Not Started / Scheduled matches
                                if status in ["NS", "Sched"]:
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

                                    if kickoff_dt > now and h_team and a_team:
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
            except Exception as e:
                logger.warning(f"LiveScore discovery error for {ls_sport}: {e}")

        return fixtures
