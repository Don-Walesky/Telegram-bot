"""
Betting Application Service
Orchestrates the core betting intelligence pipeline: fixture discovery, SportyBet catalog matching,
probability filtering, and booking code generation.
Completely decoupled from Telegram UI/formatting framework.
"""

import logging
from typing import List, Optional
from config import config
from livescore_client import LiveScoreClient, DiscoveredFixture
from sportybet_catalog import SportyBetCatalogService, MappedSportyBetSelection
from probability_filter import ImpliedProbabilityFilter, FilteredPick
from sportybet_booking import SportyBetBookingClient, BookingSlipResponse

logger = logging.getLogger(__name__)


class BettingService:
    @classmethod
    def execute_scan_pipeline(
        cls, target_date: str = "Today", sport: str = "All"
    ) -> BookingSlipResponse:
        """
        Orchestrates the end-to-end betting scan pipeline:
        1. LiveScore fixture discovery.
        2. SportyBet catalog fetching & fuzzy team matching.
        3. Implied probability safety range filtering (config-driven).
        4. Top-pick selection and official SportyBet order share API submission.
        """
        logger.info(f"🚀 [BettingService] Starting scan pipeline for Date='{target_date}', Sport='{sport}'")

        # 1. Discovery
        fixtures: List[DiscoveredFixture] = LiveScoreClient.fetch_unstarted_fixtures(
            target_date_str=target_date, sport_filter=sport
        )

        if not fixtures:
            logger.info(f"ℹ️ [BettingService] No unstarted fixtures found for {target_date} / {sport}")
            return BookingSlipResponse(
                success=False,
                booking_code=None,
                share_url="https://www.sportybet.com/ng/m/sports/football/",
                picks=[],
                total_odds=1.0,
                formatted_summary=f"⚠️ *No unstarted matches discovered for {target_date.upper()} in category {sport.upper()}.*",
                unmapped_warning=False,
                message="No unstarted fixtures discovered",
            )

        # 2. SportyBet Catalog Fetching & Matching
        sb_events = SportyBetCatalogService.fetch_sportybet_catalog(sport=sport)

        all_selections: List[MappedSportyBetSelection] = []
        unmapped_count = 0

        if sb_events:
            for fix in fixtures:
                sb_event = SportyBetCatalogService.match_fixture(fix, sb_events)
                if sb_event:
                    extracted = SportyBetCatalogService.extract_selections_from_event(sb_event)
                    all_selections.extend(extracted)
                else:
                    unmapped_count += 1
        else:
            logger.warning("⚠️ [BettingService] SportyBet live catalog returned no active events.")
            return BookingSlipResponse(
                success=False,
                booking_code=None,
                share_url="https://www.sportybet.com/ng/m/sports/football/",
                picks=[],
                total_odds=1.0,
                formatted_summary=(
                    f"📡 *SportyBet Live Catalog Status Update*\n\n"
                    f"LiveScore discovered {len(fixtures)} unstarted matches for `{target_date.upper()}` ({sport.upper()}).\n"
                    f"However, SportyBet live catalog endpoints are currently updating or restricting request access.\n\n"
                    f"💡 *No fake events were generated.* Please retry in a few moments or use `/custom` to build a slip!"
                ),
                unmapped_warning=True,
                message="SportyBet catalog empty or updating",
            )

        # 3. Probability Filter (Config-driven bounds)
        filtered_picks: List[FilteredPick] = ImpliedProbabilityFilter.filter_selections(
            all_selections,
            min_prob=config.betting.min_implied_probability,
            max_prob=config.betting.max_implied_probability,
        )

        # Limit to configured scan leg count
        slip_picks = filtered_picks[:config.betting.default_scan_legs]

        # 4. Generate Official SportyBet Booking Code or Structured Fallback
        slip_res = SportyBetBookingClient.generate_booking_code(
            slip_picks, country_code=config.betting.default_country_code
        )
        slip_res.unmapped_warning = (unmapped_count > 0)
        logger.info(
            f"✅ [BettingService] Pipeline complete. "
            f"Selected picks: {len(slip_picks)}, Success: {slip_res.success}, Code: {slip_res.booking_code}"
        )
        return slip_res
