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
from engine import (
    BetCandidate,
    BetConstructionRequest,
    ProbabilitySource,
    RiskProfile,
    WorkflowType,
)
from engine.bet_construction_engine import BetConstructionEngine

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

        # 3. Risk / Bet Construction Engine Optimization with explicit bookmaker implied provenance
        candidates: List[BetCandidate] = [
            BetCandidate(
                candidate_id=f"{sel.event_id}:{sel.market_id}:{sel.outcome_id}",
                event_id=sel.event_id,
                sport=sel.sport,
                league=sel.league,
                home_team=sel.home_team,
                away_team=sel.away_team,
                kickoff_time=sel.kickoff_time,
                market_id=sel.market_id,
                market_name=sel.market_name,
                outcome_id=sel.outcome_id,
                outcome_name=sel.outcome_name,
                decimal_odds=sel.odds,
                specifier=sel.specifier,
                bookmaker_implied_prob=round((1.0 / sel.odds) * 100.0, 2),
                probability_source=ProbabilitySource.BOOKMAKER_IMPLIED,
            )
            for sel in all_selections
        ]

        req = BetConstructionRequest(
            workflow=WorkflowType.STANDARD_SCAN,
            risk_profile=RiskProfile.BALANCED,
            desired_game_count=config.betting.default_scan_legs,
            min_game_count=1,
            min_selection_probability=config.betting.min_implied_probability,
            target_date=target_date,
            target_sports=[sport],
            candidates=candidates,
        )

        engine_res = BetConstructionEngine.build_bet_slip(req)

        if engine_res.selected_candidates:
            slip_picks: List[FilteredPick] = [
                FilteredPick(
                    selection=MappedSportyBetSelection(
                        event_id=leg.event_id,
                        home_team=leg.fixture.split(" vs ")[0] if " vs " in leg.fixture else leg.fixture,
                        away_team=leg.fixture.split(" vs ")[1] if " vs " in leg.fixture else "",
                        league=leg.league,
                        sport=leg.sport,
                        kickoff_time=leg.kickoff_time,
                        market_id=leg.market_id,
                        market_name=leg.market_name,
                        outcome_id=leg.outcome_id,
                        outcome_name=leg.outcome_name,
                        odds=leg.odds,
                        specifier=leg.specifier,
                    ),
                    odds=leg.odds,
                    implied_probability=leg.implied_probability_pct,
                )
                for leg in engine_res.selected_candidates
            ]
        else:
            # Fallback filter if engine found 0 items under strict invariants
            filtered_picks: List[FilteredPick] = ImpliedProbabilityFilter.filter_selections(
                all_selections,
                min_prob=config.betting.min_implied_probability,
                max_prob=config.betting.max_implied_probability,
            )
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
