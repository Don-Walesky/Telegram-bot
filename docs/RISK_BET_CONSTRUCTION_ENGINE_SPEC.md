# Technical Specification: Risk & Bet Construction Engine

**Document Version:** 2.0.0  
**Target System:** Telegram Betting Intelligence Assistant (`Don-Walesky/Telegram-bot`)  
**Status:** Architectural Specification & Design (NO PRODUCTION CODE IMPLEMENTATION)  
**Creation Date:** 2026-08-29  
**Last Revised:** 2026-08-30  

---

## 1. Executive Summary

This technical specification establishes the comprehensive architectural blueprint, mathematical models, constraint rules, data contracts, optimization algorithms, and integration interfaces for the unified **Risk / Bet Construction Engine**.

The primary objective of this engine is to provide a single, centralized, mathematically disciplined domain layer that evaluates available betting opportunities from any source (LiveScore fixture discovery, SportyBet live market catalogs, or monitored Telegram tipster channels) and constructs an optimal accumulator betslip that maximizes risk-adjusted expected value subject to user preferences and strict safety constraints.

```
+-----------------------------------------------------------------------------------+
|                           INCOMING BETTING REQUESTS                               |
|              (Bet Builder Wizard, Channel Scanner, Code Editor, CLI)             |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        STANDARDIZED CANDIDATE POOL                                |
|        (Normalized BetCandidate Objects with Odds, Sources & Probabilities)       |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+===================================================================================+
|                        RISK / BET CONSTRUCTION ENGINE                              |
|                                                                                   |
|  [Stage 1: Hard Safety Filter] ---> Validates kickoff, odds bounds, markets       |
|  [Stage 2: Metric Enrichment]  ---> Implied prob, True prob, EV, Uncertainty      |
|  [Stage 3: Candidate Scoring]  ---> Multi-factor Composite Utility Score          |
|  [Stage 4: Correlation Check]  ---> Same match / mutually exclusive elimination   |
|  [Stage 5: Slip Optimization]  ---> Knapsack/Heuristic Target Odds Multi-Optimizer|
|  [Stage 6: Risk Verification]  ---> Risk Profile Invariants & Exposure Limits     |
|  [Stage 7: Explainability Gen] ---> Structured Acceptance & Rejection Metadata    |
+=========================================+=========================================+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                           BetConstructionResult                                   |
|   (Optimal Slip Picks + Rejections + Expected Value + Audit Trail + Summary)     |
+-----------------------------------------------------------------------------------+
```

### Core Design Principles
1. **Quality Constraints Strictly Dominate Target Multipliers:** The engine must **never** lower selection quality, accept negative expected value legs, or relax probability thresholds merely to satisfy a requested selection count or target accumulator odds.
2. **Honesty, Transparency & Calibration:** Odds-derived probabilities must always be explicitly labeled as *Bookmaker-Implied Probability*. Model-derived probabilities must account for uncertainty and historical calibration error.
3. **Unified Candidate Ingestion:** The engine treats all candidates identically regardless of origin (LiveScore, SportyBet, or Telegram channels).
4. **Zero Fabrication:** The system must never inject fake fixtures, simulate synthetic odds as real prices, or fabricate booking codes when external APIs restrict access.

---

## 2. Current Repository Audit

A comprehensive inspection of the active repository reveals the following component topology, execution paths, and module dependencies:

### 2.1 Bet Builder Data Flow
```
Telegram User Interaction (/custom command or 'Build Betslip' button)
    │
    ▼
handlers/slip_handlers.py (`custom_command`, `handle_slip_callback`)
    │ (5-Step Callback State Machine: Date ➔ Sport ➔ Odds ➔ Count ➔ Safety)
    ▼
builder.py (`CustomSlipBuilder.generate_custom_slip`)
    │
    ▼
analyzer.py (`PredictionAnalyzer.analyze_consensus_predictions`)
    │
    ▼
aggregator.py (`PredictionAggregator.get_upcoming_fixtures`)
    │
    ▼
livescore_client.py (`LiveScoreClient.fetch_unstarted_fixtures`)
    │ (Queries LiveScore REST CDN; filters unstarted matches via is_unstarted_match)
    ▼
Raw Fixtures Returned to `aggregator.py`
    │ (Converts raw picks to static markets using analyzer.convert_to_safe_market)
    ▼
Synthetic Implied Probability Calculation (`implied_prob = (1.0 / odds) * 100.0`)
    │
    ▼
Grouped & Filtered by `analyzer.py` (Filters picks where avg_prob >= min_prob)
    │
    ▼
`CustomSlipBuilder` takes top `game_count` candidates
    │
    ▼
calculator.py (`BetCalculator.calculate_accumulator`)
    │ (Computes total odds, SportyBet multiple bonus ladder, and total payout)
    ▼
database.py (`DatabaseService.save_slip`) ➔ Persisted to `generated_slips` table
    │
    ▼
Rendered Telegram Markdown message delivered to user
```

### 2.2 Scan Channels Data Flow
```
Telegram User Interaction (/scan, /today, /tomorrow, or Channel Wizard)
    │
    ├─────────────────────────────────────────┬────────────────────────────────────────┐
    ▼                                         ▼                                        ▼
handlers/scan_handlers.py             bot.py (`chan_wiz_*`)                 bot.py (`handle_message`)
    │                                         │                                        │
    ▼                                         ▼                                        ▼
betting_service.py                   channel_siever.py                     tipster_learning.py
(`BettingService.execute_scan`)     (`ChannelSlipSiever.scan`)            (`TipsterMarketLearner.analyze`)
    │                                         │                                        │
    ├─────────────────────────────────────────┴────────────────────────────────────────┤
    ▼                                                                                  ▼
LiveScore Discovery (`livescore_client.py`)                                Extracts Regex Market Patterns
    │                                                                                  │
    ▼                                                                                  ▼
SportyBet Catalog (`sportybet_catalog.py`)                                Persists to SQLite DB
(Fuzzy match team names: SequenceMatcher >= 0.65)                         (`tipster_market_learnings` table)
    │
    ▼
Market & Odds Extraction (`sportybet_catalog.py`)
(Extracts eventId, marketId, outcomeId, decimal odds)
    │
    ▼
probability_filter.py (`ImpliedProbabilityFilter.filter_selections`)
(Calculates (1.0 / odds) * 100.0; filters within bounds 60%-95%)
    │
    ▼
SportyBet Booking Client (`sportybet_booking.py`)
(Revalidates kickoff time; calls official `/orders/share` endpoint or falls back cleanly)
    │
    ▼
database.py (`DatabaseService.save_slip`) ➔ Persisted to SQLite
    │
    ▼
Delivered to Telegram User
```

### 2.3 Identified Classes, Functions & Modules
* **[`handlers/slip_handlers.py`](file:///c:/Users/WALE/TELEGRAM-bot/handlers/slip_handlers.py)**: `custom_command`, `handle_slip_callback` — routes interactive 5-step wizard callbacks.
* **[`handlers/scan_handlers.py`](file:///c:/Users/WALE/TELEGRAM-bot/handlers/scan_handlers.py)**: `today_command`, `tomorrow_command`, `sports_command`, `scan_command`, `handle_scan_callback` — routes scan commands.
* **[`betting_service.py`](file:///c:/Users/WALE/TELEGRAM-bot/betting_service.py)**: `BettingService.execute_scan_pipeline` — coordinates discovery, catalog fetching, filtering, and booking.
* **[`builder.py`](file:///c:/Users/WALE/TELEGRAM-bot/builder.py)**: `CustomSlipBuilder.generate_custom_slip`, `CustomSlipResult` — builds custom slips up to 25 legs with target odds.
* **[`analyzer.py`](file:///c:/Users/WALE/TELEGRAM-bot/analyzer.py)**: `PredictionAnalyzer`, `ConsensusPrediction` — groups predictions, converts to safe markets, and applies consensus thresholds.
* **[`aggregator.py`](file:///c:/Users/WALE/TELEGRAM-bot/aggregator.py)**: `PredictionAggregator`, `RawPrediction` — ingests LiveScore fixtures and maps raw options.
* **[`livescore_client.py`](file:///c:/Users/WALE/TELEGRAM-bot/livescore_client.py)**: `LiveScoreClient.fetch_unstarted_fixtures`, `DiscoveredFixture`, `is_unstarted_match` — ingests unstarted fixtures from LiveScore REST CDN.
* **[`sportybet_catalog.py`](file:///c:/Users/WALE/TELEGRAM-bot/sportybet_catalog.py)**: `SportyBetCatalogService`, `MappedSportyBetSelection` — queries SportyBet factsCenter API and fuzzy matches fixtures (`SequenceMatcher >= 0.65`).
* **[`probability_filter.py`](file:///c:/Users/WALE/TELEGRAM-bot/probability_filter.py)**: `ImpliedProbabilityFilter.filter_selections`, `FilteredPick` — computes implied probability `(1.0 / odds) * 100%` and filters candidates.
* **[`sportybet_booking.py`](file:///c:/Users/WALE/TELEGRAM-bot/sportybet_booking.py)**: `SportyBetBookingClient.generate_booking_code`, `BookingSlipResponse` — re-validates odds/kickoffs and calls `/orders/share` endpoint with structured fallback.
* **[`channel_siever.py`](file:///c:/Users/WALE/TELEGRAM-bot/channel_siever.py)**: `ChannelSlipSiever.scan_and_sieve_channel_slips` — sieves channel picks against user probability thresholds.
* **[`channel_monitor.py`](file:///c:/Users/WALE/TELEGRAM-bot/channel_monitor.py)**: `ChannelMonitorService`, `MonitoredChannel` — channel metadata registry.
* **[`tipster_learning.py`](file:///c:/Users/WALE/TELEGRAM-bot/tipster_learning.py)**: `TipsterMarketLearner`, `TipsterMarketTrend` — regex parser for channel posts and market popularity tracker.
* **[`learning_engine.py`](file:///c:/Users/WALE/TELEGRAM-bot/learning_engine.py)**: `StrategyLearningEngine`, `DiscoveredMarket`, `MarketCombinationRule` — hourly catalog harvester and combination rule store.
* **[`database.py`](file:///c:/Users/WALE/TELEGRAM-bot/database.py)**: `DatabaseService` — SQLite persistence repository (`generated_slips`, `code_conversions`, `user_preferences`, `tipster_market_learnings`).
* **[`calculator.py`](file:///c:/Users/WALE/TELEGRAM-bot/calculator.py)**: `BetCalculator` — accumulator payout, SportyBet bonus ladder, and Fractional Kelly stake sizing.
* **[`code_converter.py`](file:///c:/Users/WALE/TELEGRAM-bot/code_converter.py)**: `BetCodeConverterService`, `ConversionResult` — external code conversion gateway (RapidAPI/Betloy).
* **[`code_editor.py`](file:///c:/Users/WALE/TELEGRAM-bot/code_editor.py)**: `CodeEditorEngine`, `FilteredSlipResult` — filters high-risk legs out of booking codes.
* **[`config.py`](file:///c:/Users/WALE/TELEGRAM-bot/config.py)**: `Config`, `BettingEngineConfig`, `ExternalServiceConfig` — typed dataclass settings and validation invariants.

---

## 3. Existing Betting Architecture

The current repository follows an implicit 4-tier layered architecture:

```
+-----------------------------------------------------------------------------------+
|                          1. TELEGRAM PRESENTATION LAYER                           |
|       (bot.py, handlers/slip_handlers.py, handlers/scan_handlers.py, keyboards.py)|
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                          2. APPLICATION SERVICES LAYER                            |
|       (BettingService, CustomSlipBuilder, ChannelSlipSiever, CodeEditorEngine)    |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        3. DOMAIN & CALCULATION ENGINES                            |
| (ImpliedProbabilityFilter, PredictionAnalyzer, BetCalculator, StrategyLearning)   |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                          4. EXTERNAL GATEWAYS & STORAGE                           |
| (LiveScoreClient, SportyBetCatalogService, SportyBetBookingClient, DatabaseService)|
+-----------------------------------------------------------------------------------+
```

### Concurrency & Thread Boundaries
All external network I/O and CPU-bound selection pipelines are non-blocking:
* `BettingService.execute_scan_pipeline`, `CustomSlipBuilder.generate_custom_slip`, and `ChannelSlipSiever.scan_and_sieve_channel_slips` are executed inside `await asyncio.to_thread(...)` wrappers, ensuring the `python-telegram-bot` event loop remains responsive.
* Hourly background catalog market scans are executed via `job_queue.run_repeating(hourly_market_learning_job, interval=3600)`.

---

## 4. Existing Data Sources

The following table details all data currently available in the system:

| Data Domain | Source Module & Function | Class / Structure | Available Fields | Current Limitations |
| :--- | :--- | :--- | :--- | :--- |
| **Fixture Data** | `livescore_client.py`<br>`LiveScoreClient.fetch_unstarted_fixtures` | `DiscoveredFixture` | `sport`, `league`, `home_team`, `away_team`, `kickoff_time` (`datetime`), `status` (`"NS"`), `source` (`"LiveScore"`) | No unique LiveScore fixture ID; country is concatenated into league; no team form, standings, injury, or weather stats. |
| **Odds Data** | `sportybet_catalog.py`<br>`SportyBetCatalogService.extract_selections_from_event` | `MappedSportyBetSelection` | `event_id`, `home_team`, `away_team`, `league`, `sport`, `kickoff_time`, `market_id`, `market_name`, `outcome_id`, `outcome_name`, `odds`, `specifier`, `match_confidence` | Snapshot odds only; no opening vs closing line movements; catalog only exposes popular markets (1X2, Over/Under, Double Chance); bookmaker margin not explicitly separated. |
| **Prediction Data** | `analyzer.py`<br>`PredictionAnalyzer.convert_to_safe_market` | `ConsensusPrediction`<br>`RawPrediction` | `home_team`, `away_team`, `league`, `sport`, `original_pick`, `safe_market`, `odds`, `consensus_probability`, `agreed_sources`, `match_date`, `kickoff_time` | Odds and probabilities are derived from fixed static lookup rules (e.g. 1.18 for 1X) rather than statistical ML models; external tipster scrapers are simulated. |
| **Learning Data** | `database.py`<br>`DatabaseService.get_top_tipster_markets`<br>`learning_engine.py` | `tipster_market_learnings`<br>`DiscoveredMarket`<br>`MarketCombinationRule` | `market_name`, `sport`, `occurrence_count`, `last_seen`, `market_id`, `outcomes`, `first_seen`, `historical_win_rate`, `recommended_safety_margin` | No match settlement tracking (scores are not stored post-match); no slip win/loss tracking; no calibration history; combination rules are static in code. |
| **Channel Data** | `channel_monitor.py`<br>`ChannelMonitorService.get_monitored_channels` | `MonitoredChannel` | `name`, `url`, `handle`, `status`, `codes_analyzed_count` | Channel monitoring relies on user post forwarding or template mock lists; no direct Telethon/MTProto userbot scraper. |
| **Historical Bet Data** | `database.py`<br>`DatabaseService.get_user_history` | `generated_slips` table | `id`, `user_id`, `match_date`, `sport`, `game_count`, `target_odds`, `actual_odds`, `min_probability`, `booking_code`, `summary_text`, `created_at` | Slips stored as monolithic Markdown strings; individual legs/outcomes not normalized into relational child tables; settlement status is unrecorded. |

---

## 5. Existing Prediction / Learning Components

The repository contains several components with prediction or learning titles:
1. **[`analyzer.py`](file:///c:/Users/WALE/TELEGRAM-bot/analyzer.py) (`PredictionAnalyzer`):**
   * Groups ingested LiveScore fixtures by `(home_team, away_team)`.
   * Maps raw picks to safe markets using static mappings (e.g. Football "Home Win" $\rightarrow$ "Double Chance (1X)" @ 1.18).
   * Calculates consensus probability as a mathematical mean of static probabilities.
2. **[`aggregator.py`](file:///c:/Users/WALE/TELEGRAM-bot/aggregator.py) (`PredictionAggregator`):**
   * Serves as an adapter between `LiveScoreClient` and `PredictionAnalyzer`.
   * Assigns synthetic implied probabilities based on fixed odds lookup tables.
3. **[`learning_engine.py`](file:///c:/Users/WALE/TELEGRAM-bot/learning_engine.py) (`StrategyLearningEngine`):**
   * Ingests live SportyBet catalogs hourly and indexes newly seen `marketId` and `outcomeId` definitions in memory.
   * Stores static `MarketCombinationRule` records (e.g., "Double Chance + Over 1.5 Goals" @ 96.4% historical win rate).
4. **[`tipster_learning.py`](file:///c:/Users/WALE/TELEGRAM-bot/tipster_learning.py) (`TipsterMarketLearner`):**
   * Uses regex patterns to identify market types mentioned in forwarded Telegram channel posts.
   * Increments occurrence frequency in the `tipster_market_learnings` SQLite table.

---

## 6. Existing Betting Pipeline

Currently, the primary betting pipeline in [`betting_service.py`](file:///c:/Users/WALE/TELEGRAM-bot/betting_service.py) executes as follows:
```
1. LiveScoreClient.fetch_unstarted_fixtures(date, sport)
       ↓
2. SportyBetCatalogService.fetch_sportybet_catalog(sport)
       ↓
3. Fuzzy matching: SportyBetCatalogService.match_fixture (SequenceMatcher >= 0.65)
       ↓
4. SportyBetCatalogService.extract_selections_from_event (Extract marketId, outcomeId, odds)
       ↓
5. ImpliedProbabilityFilter.filter_selections (Calculates (1/odds)*100%, filters 60%-95%)
       ↓
6. Sort descending by implied probability and slice top-k (default: 5 legs)
       ↓
7. SportyBetBookingClient.generate_booking_code (Revalidate kickoff & call /orders/share API)
```

---

## 7. Problem Statement: Current Pipeline vs. Future Risk Engine

### Why the Existing Pipeline is NOT Equivalent to the Future Risk Engine
While the current `BettingService` is functional, robust, and honest, it is essentially a **filtering and matching script** rather than an intelligent **risk and bet construction engine**.

| Dimension | Current Pipeline (`BettingService`) | Future Risk / Bet Construction Engine |
| :--- | :--- | :--- |
| **Candidate Ranking** | Simple top-$k$ slicing sorted strictly by bookmaker-implied probability $(1 / \text{odds})$. | Multi-factor composite utility scoring combining model probability, EV, source credibility, and market quality. |
| **Value Assessment** | Zero expected value modeling; assumes highest probability equals best bet. | Explicit expected value calculation ($\text{EV} = P_{\text{model}} \cdot \text{Odds} - 1$) and margin de-vigging. |
| **Risk Profiles** | Flat probability range thresholds (e.g. 60%–95% hardcoded in config). | Formally bounded risk profiles (Conservative, Balanced, Aggressive, Very Aggressive, Custom) with distinct variance targets. |
| **Accumulator Optimization** | Slices the first $N$ sorted items; ignores target odds multiplier. | Combinatorial multi-objective optimizer balancing joint probability, target odds convergence, and bonus tiering. |
| **Correlation Defense** | Only deduplicates by match during fuzzy matching. | Formal conflict graph preventing intra-match dependencies, team multi-leg exposure, and league clustering. |
| **Source Intelligence** | Raw frequency counts of regex-matched words in SQLite. | Bayesian regressed credibility modeling with sample-size shrinkage and time decay. |
| **Explainability** | Static markdown formatting with bookmaker-implied probability note. | Structured acceptance/rejection metadata trace explaining exact mathematical reasons for inclusion or exclusion. |
| **Backtesting & Verification** | No historical simulation or outcome settlement tracking. | Deterministic historical replay harness calculating empirical Brier calibration, ROI, and maximum drawdown. |

---

## 8. Responsibilities of the Future Risk / Bet Construction Engine

The engine is the central domain intelligence layer responsible for answering:
> **"Given a pool of available candidate betting selections and a user's operational constraints and risk profile, which subset of selections should be assembled into the final betslip to optimize expected value while strictly adhering to safety and variance constraints?"**

### Core Responsibilities
1. **Candidate Normalization:** Ingest and normalize candidates from any source into a unified `BetCandidate` model.
2. **Hard Safety Gating:** Enforce binary pass/fail constraints (kickoff timing, odds bounds, freshness).
3. **Metric Enrichment:** Calculate fair probabilities, expected values, and source credibility weights.
4. **Multi-Factor Scoring:** Compute a composite utility score $S_i \in [0.0, 1.0]$ for every eligible candidate.
5. **Correlation Defense:** Eliminate intra-match dependencies and penalize excessive league/sport exposure.
6. **Combinatorial Slip Optimization:** Solve the multi-objective accumulator selection problem.
7. **Risk Profile Invariant Enforcement:** Guarantee that the resulting slip satisfies the active risk profile's mathematical constraints.
8. **Explainability Generation:** Emit structured, machine-readable acceptance and rejection rationale.
9. **Graceful Degradation:** Degrade safely without fabricating data or lowering quality standards when liquidity is low.

---

## 9. Responsibilities the Engine MUST NOT Own

To preserve clean separation of concerns and avoid domain pollution, the engine **MUST NOT** own:
* **Telegram UI / Formatting:** Must not render Telegram messages, build inline keyboards, or handle bot callback state machines.
* **HTTP Networking & API Calls:** Must not make direct HTTP requests to LiveScore, SportyBet, or RapidAPI.
* **Browser Automation & Session Management:** Must not manage SportyBet web cookies or session tokens.
* **Booking Code Order Locking:** Must not call the SportyBet `/orders/share` endpoint directly (delegated to `SportyBetBookingClient`).
* **Database Connection Management:** Must not directly execute SQL queries (delegated to `DatabaseService`).
* **User Authentication & Authorization:** Must not inspect Telegram user roles or admin permissions.

---

## 10. Standard BetCandidate Model

Every candidate entering the engine is normalized into the `BetCandidate` schema:

```
+-------------------------------------------------------------------------+
|                              BetCandidate                               |
+-------------------------------------------------------------------------+
| [Identity & Fixture Context]                                            |
|  - candidate_id: str                    (UUID / EventId:Market:Outcome) |
|  - event_id: str                        (SportyBet Event ID or Hash)    |
|  - sport: str                           ("Football", "Basketball", etc.)|
|  - league: str                          ("Premier League", "NBA", etc.) |
|  - home_team: str                       ("Arsenal")                     |
|  - away_team: str                       ("Chelsea")                     |
|  - kickoff_time: datetime               (Kickoff timestamp in WAT)      |
+-------------------------------------------------------------------------+
| [Market & Selection Context]                                            |
|  - market_id: str                       (e.g. "18" for Double Chance)   |
|  - market_name: str                     (e.g. "Double Chance")          |
|  - outcome_id: str                      (e.g. "12" for 1X)              |
|  - outcome_name: str                    (e.g. "1X")                     |
|  - specifier: Optional[str]             (e.g. "total=1.5")              |
|  - decimal_odds: float                  (e.g. 1.25)                     |
+-------------------------------------------------------------------------+
| [Probabilities & Value Metrics]                                         |
|  - bookmaker_implied_prob: float        (1.0 / decimal_odds)            |
|  - model_probability: float             (Estimated true win prob 0-1)   |
|  - model_confidence: float              (Model uncertainty score 0-1)   |
|  - expected_value: float                ((Prob * Odds) - 1.0)           |
+-------------------------------------------------------------------------+
| [Source & Provenance]                                                   |
|  - source_type: SourceType              (LIVESCORE | SPORTYBET | TIPSTER)|
|  - source_name: str                     ("@jhgfdghgdhjjj", "LiveScore") |
|  - source_historical_accuracy: float    (Historical hit rate 0-1)       |
|  - source_sample_size: int              (Count of graded historical bets|
|  - ingested_at: datetime                (Timestamp of data capture)     |
|  - data_freshness_seconds: float        (Age of odds/prediction)       |
+-------------------------------------------------------------------------+
| [Derived Scoring & State]                                               |
|  - is_eligible: bool                    (Passed hard constraints)       |
|  - composite_score: float               (Calculated ranking score)      |
|  - flags: List[str]                     (["HIGH_VALUE", "FAVORITE"])    |
+-------------------------------------------------------------------------+
```

### Field Existence & Availability Status

| Field Name | Exists in Current Repo? | Source Module / Origin | Status |
| :--- | :---: | :--- | :--- |
| `candidate_id` | 🟡 (Partially) | Hash of fixture + market | Synthesized |
| `event_id` | 🟢 (Yes) | `MappedSportyBetSelection.event_id` | Active |
| `sport`, `league` | 🟢 (Yes) | `DiscoveredFixture`, `MappedSportyBetSelection` | Active |
| `home_team`, `away_team` | 🟢 (Yes) | `DiscoveredFixture`, `MappedSportyBetSelection` | Active |
| `kickoff_time` | 🟢 (Yes) | `DiscoveredFixture.kickoff_time` | Active |
| `market_id`, `outcome_id` | 🟢 (Yes) | `MappedSportyBetSelection` | Active |
| `decimal_odds` | 🟢 (Yes) | `MappedSportyBetSelection.odds` | Active |
| `bookmaker_implied_prob` | 🟢 (Yes) | `ImpliedProbabilityFilter` | Active |
| `model_probability` | 🟡 (Partially) | `ConsensusPrediction` (Static lookup) | Needs statistical upgrade |
| `model_confidence` | 🔴 (No) | Future uncertainty estimation | **Future Requirement** |
| `expected_value` | 🔴 (No) | Calculable from odds & model prob | **Future Requirement** |
| `source_name`, `source_type` | 🟢 (Yes) | `DiscoveredFixture.source`, `RawPrediction.source`| Active |
| `source_historical_accuracy` | 🔴 (No) | Requires settlement tracking | **Future Requirement** |
| `source_sample_size` | 🟡 (Partially) | `tipster_market_learnings.occurrence_count` | Partially Active |
| `ingested_at` | 🟡 (Partially) | Timestamps in catalog/logs | Needs normalization |
| `is_eligible`, `composite_score` | 🔴 (No) | Engine internal state | **Future Requirement** |

---

## 11. Engine Input Contract (`BetConstructionRequest`)

The input contract strictly partitions **User Configuration** from **System Safety Constraints**:

```
+-------------------------------------------------------------------------+
|                        BetConstructionRequest                           |
+-------------------------------------------------------------------------+
| [User Configuration]                                                    |
|  - request_id: str                      (UUID)                          |
|  - workflow: WorkflowType               (BET_BUILDER | SCAN_CHANNELS)   |
|  - risk_profile: RiskProfile            (CONSERVATIVE | BALANCED | ...) |
|  - target_combined_odds: Optional[float] (e.g. 3.0x)                    |
|  - min_combined_odds: float             (e.g. 2.0x)                     |
|  - max_combined_odds: float             (e.g. 7.0x)                     |
|  - desired_game_count: int              (e.g. 5)                        |
|  - min_game_count: int                  (e.g. 3)                        |
|  - max_game_count: int                  (e.g. 25)                       |
|  - target_date: str                     ("Today", "Tomorrow", "YYYY-MM")|
|  - target_sports: List[str]             (["Football", "Basketball"])    |
|  - min_selection_probability: float     (e.g. 75.0%)                    |
|  - preferred_markets: List[str]         (["Double Chance", "Over 1.5"]) |
|  - excluded_leagues: List[str]          (Optional blacklist)            |
|  - stake_amount: float                  (Default: 1000.0)               |
+-------------------------------------------------------------------------+
| [System Safety Constraints]                                             |
|  - max_match_correlation: float         (Max 1 pick per match)          |
|  - max_league_exposure_pct: float       (Max 40% legs from same league) |
|  - max_sport_exposure_pct: float        (Max 70% legs from same sport)  |
|  - odds_freshness_ttl_sec: int          (Max 300s since catalog fetch)  |
|  - min_source_sample_size: int          (Min 10 historical picks)       |
|  - require_positive_ev: bool            (True for Balanced/Conservative)|
|  - allow_fallback_reduction: bool       (Allow return of fewer legs)    |
+-------------------------------------------------------------------------+
```

---

## 12. Engine Output Contract (`BetConstructionResult`)

```
+-------------------------------------------------------------------------+
|                         BetConstructionResult                           |
+-------------------------------------------------------------------------+
| [Execution Status]                                                      |
|  - request_id: str                      (Matches request UUID)          |
|  - success: bool                        (True if valid slip formed)     |
|  - status_code: ConstructionStatusCode  (OPTIMAL | SUB_OPTIMAL | FAILED)|
|  - risk_profile_applied: RiskProfile                                    |
+-------------------------------------------------------------------------+
| [Constructed Accumulator Slip]                                          |
|  - selected_candidates: List[SelectedBetLeg]                            |
|  - total_combined_odds: float           (Product of leg odds)           |
|  - estimated_joint_probability: float   (Joint win probability %)       |
|  - estimated_slip_ev: float             (Accumulator Expected Value)    |
|  - recommended_stake: float             (Fractional Kelly sizing)       |
|  - sportybet_bonus_pct: float           (Estimated accumulator bonus)   |
|  - estimated_total_payout: float        (Stake * Odds + Bonus)          |
+-------------------------------------------------------------------------+
| [Transparency & Audit Trail]                                            |
|  - total_candidates_evaluated: int                                      |
|  - accepted_count: int                                                  |
|  - rejected_candidates: List[RejectedCandidate]                         |
|  - optimization_warnings: List[str]                                     |
|  - fallback_applied: bool                                               |
|  - explanation_summary: str             (User-facing Telegram Markdown) |
|  - debug_metadata: Dict[str, Any]       (Scoring metrics & timestamps)  |
+-------------------------------------------------------------------------+
```

---

## 13. Candidate Scoring Model

The candidate scoring model computes a normalized **Composite Utility Score** ($S \in [0.0, 1.0]$) for every eligible candidate:

$$S = w_{\text{prob}} \cdot f(P_{\text{model}}) + w_{\text{ev}} \cdot g(\text{EV}) + w_{\text{source}} \cdot h(\text{Source}) + w_{\text{mkt}} \cdot m(\text{Market}) + w_{\text{fresh}} \cdot q(\Delta t) - P_{\text{unc}} - P_{\text{corr}}$$

Where the factor weights satisfy $\sum w_i = 1.0$.

### Detailed Factor Specifications

| Factor | What it Measures | Exists Now? | Origin Module | Normalization Formula | Role | Default Weight | Calibration Approach |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: | :--- |
| **Model Prob $f(P)$** | Win likelihood | 🟡 | `analyzer.py` | $f(P) = \frac{P - P_{\text{min}}}{1.0 - P_{\text{min}}}$ | Score Factor | $0.35$ | Brier score minimization on historical outcomes. |
| **Expected Value $g(\text{EV})$** | Mathematical edge | 🔴 | Derived | $g(\text{EV}) = \frac{1}{1 + e^{-15 \cdot \text{EV}}}$ | Score Factor | $0.25$ | Thresholded by risk profile ($\text{EV} \ge \text{EV}_{\text{min}}$). |
| **Source Reliability $h(\text{Src})$** | Source credibility | 🟡 | `tipster_learning.py` | $h = R_{\text{source}} \cdot (1 - e^{-N/30})$ | Score Factor | $0.15$ | Bayesian shrinkage parameter $K$ tuned via cross-validation. |
| **Market Reliability $m(\text{Mkt})$** | Market liquidity/safety| 🟢 | `learning_engine.py` | Lookup: DC=$1.0$, O1.5=$0.9$, DNB=$0.8$, 1X2=$0.6$ | Score Factor | $0.15$ | Empirical market variance from historical settlement data. |
| **Data Freshness $q(\Delta t)$** | Age of odds/data | 🟡 | Logs/Timestamps | $q(\Delta t) = \max(0, 1.0 - \frac{\Delta t}{600})$ | Score Factor | $0.10$ | Exponential half-life based on odds volatility curves. |
| **Uncertainty $P_{\text{unc}}$** | Prediction variance | 🔴 | Future ML Model | $P_{\text{unc}} = (1.0 - \text{Confidence}) \times 0.20$ | Penalty | Penalty | Standard error of ensemble predictions. |
| **Correlation $P_{\text{corr}}$** | Multi-leg co-dependence| 🟢 | Deduping logic | $P_{\text{corr}} = \text{Exposure Ratio} \times 0.15$ | Penalty | Penalty | Cross-market covariance matrix. |

---

## 14. Expected Value

### 14.1 Mathematical Formulation
$$\text{EV} = (P_{\text{model}} \times \text{Decimal Odds}) - 1.0$$
* $\text{EV} > 0$: **Positive Expected Value (+EV)** — Long-term profitable proposition.
* $\text{EV} = 0$: **Fair / Neutral Value**.
* $\text{EV} < 0$: **Negative Expected Value (-EV)** — Long-term losing proposition.

### 14.2 Probability vs. Expected Value
A high probability does **not** ensure positive value. For example:
* $P_{\text{model}} = 85.0\%$ at Decimal Odds $1.10 \implies \text{EV} = (0.85 \times 1.10) - 1.0 = -0.065$ (**$-6.5\%$ Negative EV**).
* $P_{\text{model}} = 65.0\%$ at Decimal Odds $1.70 \implies \text{EV} = (0.65 \times 1.70) - 1.0 = +0.105$ (**$+10.5\%$ Positive EV**).

### 14.3 Overround & De-vigging
$$\text{Overround } M = \left(\sum_{i=1}^{k} \frac{1}{\text{Odds}_i}\right) - 1.0, \quad P_{\text{devigged}} = \frac{\frac{1}{\text{Odds}_i}}{1.0 + M}$$

---

## 15. Risk Profiles

```
+-------------------------------------------------------------------------------------------------------+
|                                      RISK PROFILE SPECTRUM                                            |
|                                                                                                       |
|  CONSERVATIVE         BALANCED              AGGRESSIVE          VERY AGGRESSIVE           CUSTOM      |
|  [P: 85%-98%]     [P: 75%-90%]             [P: 60%-80%]          [P: 50%-75%]         [User Defined]  |
|  [Odds: 1.05-1.25][Odds: 1.15-1.45]        [Odds: 1.30-1.85]     [Odds: 1.50-2.50]    [User Bounds]   |
|  Min Variance     Optimal Sharpe / EV      Max Growth Edge       High Multiplier      Flexible        |
+-------------------------------------------------------------------------------------------------------+
```

### Detailed Risk Profile Invariants

| Dimension | CONSERVATIVE | BALANCED (Default) | AGGRESSIVE | VERY AGGRESSIVE | CUSTOM |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Primary Objective** | Capital preservation; maximize joint probability; minimize variance. | Maximize Risk-Adjusted Expected Value (Sharpe ratio equivalent). | Exploit positive expected value with higher variance tolerance. | Maximize long-shot accumulator multiplier under strict safety caps. | User-specified objective weights. |
| **Leg Probability Range** | **$85.0\% - 98.0\%$** | **$75.0\% - 90.0\%$** | **$60.0\% - 80.0\%$** | **$50.0\% - 75.0\%$** | User bounded ($P_{\text{min}} - P_{\text{max}}$). |
| **Leg Decimal Odds Range** | **$1.05 - 1.25$** | **$1.15 - 1.45$** | **$1.30 - 1.85$** | **$1.50 - 2.50$** | User bounded ($\text{Odds}_{\text{min}} - \text{Odds}_{\text{max}}$). |
| **Expected Value Invariant** | $\text{EV} \ge -0.02$ | $\text{EV} \ge +0.00$ | $\text{EV} \ge +0.03$ | $\text{EV} \ge +0.05$ | User configured threshold. |
| **Target Combined Odds** | $1.50\text{x} - 3.00\text{x}$ | $2.50\text{x} - 5.00\text{x}$ | $5.00\text{x} - 15.00\text{x}$ | $15.00\text{x} - 50.00\text{x}+$ | User target ($2.0\text{x} - 7.0\text{x}$). |
| **Recommended Leg Count** | $3 - 5$ legs | $4 - 8$ legs | $5 - 12$ legs | $8 - 20$ legs | $3 - 25$ legs. |
| **Kelly Stake Sizing** | Eighth Kelly ($f = 0.125$) | Quarter Kelly ($f = 0.25$) | Half Kelly ($f = 0.50$) | Fixed fractional ($\le 1.0\%$) | Configured fraction. |
| **Correlation Tolerance** | Strict (Zero shared fixtures, max 2 per league). | Moderate (Max 1 pick per fixture, max 3 per league). | Moderate (Max 1 pick per fixture, max 4 per league). | Flexible (Allows independent markets from same league). | User constraint limits. |
| **Fallback Behavior** | Drop leg count immediately if quality candidates $< 85\%$. | Return best valid slip; explain shortfall. | Seek higher value single legs; warn user. | Return highest EV subset; explain high variance. | User choice: Trim slip or Abort. |

*Note: The numerical thresholds above represent **DEFAULT CONFIGURATION**. All thresholds will be marked `[CALIBRATION REQUIRED]` until empirical backtesting is executed on settled historical data.*

---

## 16. Hard Constraints

The engine executes a binary pass/fail rejection gate before any scoring or optimization:
1. **Kickoff Timing:** Event kickoff timestamp must be strictly $> \text{Current Time} + 120\text{s}$.
2. **Valid Odds & Market:** Selection must have active decimal odds $\ge 1.01$ and a recognized SportyBet `outcomeId`.
3. **Odds Quality Bounds:** Selection odds must lie within the active risk profile's $[\text{Odds}_{\text{min}}, \text{Odds}_{\text{max}}]$.
4. **Single Selection per Event:** A final betslip must never contain more than one selection from the same event ID.
5. **No Negative EV in Disciplined Profiles:** Balanced and Conservative profiles must reject any candidate where $\text{EV} < \text{EV}_{\text{threshold}}$.
6. **Data Freshness:** Candidates derived from catalog fetches older than $300\text{s}$ are rejected.
7. **Maximum Selections:** Slip leg count must never exceed configured maximum (25 legs).

---

## 17. Soft Objectives

Eligible candidates passing hard constraints are optimized against competing objectives:
1. **Target Combined Odds Convergence:** Approach the user's requested accumulator multiplier without sacrificing leg quality.
2. **Joint Win Probability Maximization:** Maximize $P_{\text{joint}} = \prod P_i$.
3. **Accumulator Expected Value Maximization:** Maximize $\text{EV}_{\text{slip}} = (\prod P_i \times \prod \text{Odds}_i) - 1.0$.
4. **Sport & League Diversification:** Distribute legs across distinct leagues and sports to mitigate correlated matchday factors.
5. **Source Credibility Preference:** Prioritize candidates from sources with higher sample sizes and proven empirical accuracy.

---

## 18. Selection Algorithm

```
 [Stage 1: Ingestion & Normalization]
      ↓
 [Stage 2: Hard Constraint Filter]
      ↓
 [Stage 3: Metric Enrichment (EV, Implied Prob, De-vigging)]
      ↓
 [Stage 4: Candidate Scoring (Composite Utility S)]
      ↓
 [Stage 5: Conflict Graph Construction (Co-dependent event mapping)]
      ↓
 [Stage 6: Combinatorial Slip Optimization (Target odds & leg solver)]
      ↓
 [Stage 7: Accumulator Metric Evaluation (Bonus & Kelly stake calculation)]
      ↓
 [Stage 8: Risk Profile Invariant Verification]
      ↓
 [Stage 9: Explainability & Audit Generation]
      ↓
 [Stage 10: Persist & Deliver Result]
```

---

## 19. Slip Optimization: Candidate Ranking vs. Combination Optimization

Selecting the top $k$ highest-ranked individual candidates does **not** necessarily produce the best accumulator betslip.

### Mathematical Formulation
$$\max_{C \subseteq \text{Candidates}} \left[ \sum_{j \in C} S_j + \alpha \cdot \ln(1 + \text{Bonus}(|C|)) - \lambda \cdot |\ln(\prod_{j \in C} \text{Odds}_j) - \ln(\text{Target Odds})| - \beta \cdot \text{ExposurePenalty}(C) \right]$$
Subject to:
* $\text{min\_game\_count} \le |C| \le \text{max\_game\_count}$
* $\text{min\_combined\_odds} \le \prod_{j \in C} \text{Odds}_j \le \text{max\_combined\_odds}$
* For all $u, v \in C$, $\text{event\_id}(u) \ne \text{event\_id}(v)$

---

## 20. Correlation & Inter-Selection Dependency

1. **Intra-Match Dependency (Hard Block):** Exactly one selection allowed per event ID.
2. **Team Multi-Leg Exposure (Hard Block):** A team cannot appear in multiple fixtures within the same slip.
3. **League Concentration Limit (Soft Penalty):** Maximum 40% of total slip legs from a single league.
4. **Time-Window Clustering (Soft Diversification):** Spreads kickoff times across distinct matchday windows.

---

## 21. Learning Engine Integration

```
Historical Results ➔ Learning Engine ➔ Performance Metrics ➔ Risk Engine ➔ Candidate Scoring ➔ Slip Optimizer
```
* **EXISTING DATA:** Hourly catalog market index (`StrategyLearningEngine._discovered_markets`), tipster regex pattern counts (`tipster_market_learnings`).
* **DATA REQUIRING TRANSFORMATION:** Calculating empirical popularity percentages and static combination rule boosts.
* **DATA NOT CURRENTLY AVAILABLE:** Post-match result settlement table (`match_settlements`), slip win/loss tracking, empirical Brier calibration curves.

---

## 22. Tipster & Channel Reliability Framework

A source with a $90\%$ win rate across 10 tips must **not** outrank a source with a $78\%$ win rate across 5,000 tips.

### Bayesian Regressed Reliability Formula
$$R_{\text{source}} = \frac{N}{N + K} \cdot \mu_{\text{empirical}} + \frac{K}{N + K} \cdot \mu_{\text{prior}}$$
Where $N$ = total graded predictions, $\mu_{\text{empirical}} = \frac{\text{Wins}}{N}$, $\mu_{\text{prior}} = 0.75$, and shrinkage parameter $K = 25$.

### Recency Decay
$$W_{\text{recency}} = e^{-\lambda \cdot (\text{Days Since Last Post})}, \quad \lambda = 0.023$$

---

## 23. Data Quality Controls

* **Fixture Validity:** Unstarted status verified via `LiveScoreClient.is_unstarted_match` (`status="NS"`).
* **Odds Validity:** Numeric odds $\ge 1.01$ and $\le 100.0$.
* **Market Mapping:** Recognized SportyBet `marketId` and `outcomeId`.
* **Team Similarity:** Fuzzy matching ratio $\ge 0.65$ (`SequenceMatcher`).
* **Missing Data Action:** Drop candidate; never extrapolate or hallucinate missing prices.

---

## 24. Data Freshness Controls

* **Odds TTL:** Maximum 300 seconds ($5$ minutes) from catalog query timestamp.
* **Stale Odds Action:** Trigger background catalog refresh; if unavailable, exclude candidate from slip construction.
* **Kickoff Cutoff:** Candidate dropped if kickoff is within 120 seconds of evaluation.

---

## 25. Fallback Behaviour & Graceful Degradation

| Scenario | Engine Action | Safety Invariant | User Notification |
| :--- | :--- | :--- | :--- |
| **A. Insufficient Fixtures** | Return `NO_FIXTURES`. | Zero fake fixtures. | Suggest switching date to Tomorrow or sport to All. |
| **B. Insufficient Candidates** | Form smaller slip ($\ge 3$ legs) or abort ($< 3$ legs). | Never lower quality threshold. | Explain reduced leg count transparently. |
| **C. Missing / Stale Odds** | Drop candidate; re-query catalog. | Never use default fallback odds. | Drop unpriced matches from slip. |
| **D. Missing Predictions** | Fallback to bookmaker-implied probability. | Explicitly label as implied prob. | Display "Bookmaker-Implied Probability" badge. |
| **E. Insufficient Learning** | Apply uninformative Bayesian prior ($\mu_{\text{prior}}$). | Shrink small sample sizes. | Label source as "Uncalibrated / New". |
| **F. SportyBet Catalog Offline** | Return verified LiveScore picks with manual guide. | Never generate fake IDs. | Provide direct web app link for manual booking. |
| **G. Target Odds Impossible** | Return best achievable odds slip. | Quality takes priority over odds. | Explain why target odds were not reached. |
| **H. Share API Rejection** | Return clean recreation summary. | Never fabricate share code string. | Instruct manual pick selection on SportyBet. |

---

## 26. Bet Builder Integration

`handlers/slip_handlers.py` constructs a `BetConstructionRequest` from wizard inputs (`wiz["date"]`, `wiz["sport"]`, `wiz["odds"]`, `wiz["count"]`, `wiz["prob"]`), invokes `BetConstructionEngine.build_bet_slip(request)`, and renders the resulting `BetConstructionResult`.

---

## 27. Scan Channels Integration

`handlers/scan_handlers.py` and `channel_siever.py` ingest channel picks, normalize them into `List[BetCandidate]`, and submit them to the exact same `BetConstructionEngine.build_bet_slip(request)` entrypoint.

---

## 28. Explainability Model

### Machine-Readable Reason Codes
* Acceptance: `HIGH_MODEL_PROBABILITY`, `POSITIVE_EXPECTED_VALUE`, `HIGH_SOURCE_ACCURACY`, `PREFERRED_MARKET`.
* Rejection: `ODDS_TOO_LOW`, `ODDS_TOO_HIGH`, `PROB_BELOW_THRESHOLD`, `NEGATIVE_EV`, `CORRELATED_EVENT`, `STALE_DATA`.

---

## 29. Observability & Audit Logging

The engine emits structured JSON log events for every construction request containing `request_id`, `workflow`, `risk_profile`, candidate pool counts, total odds, EV, and latency, strictly omitting user PII.

---

## 30. Configuration Model

* **User Config:** `target_date`, `target_sports`, `risk_profile`, `target_odds`, `game_count`.
* **System Config:** `odds_freshness_ttl_sec`, `livescore_timeout`, `sportybet_timeout`, `db_path`.
* **Model Parameters:** $w_{\text{prob}}, w_{\text{ev}}, w_{\text{source}}, w_{\text{mkt}}, w_{\text{fresh}}$, Bayesian $K$, decay $\lambda$.
* **Safety Limits:** `max_custom_legs=25`, `min_odds=1.01`, `max_target_odds=7.0`.

---

## 31. Historical Backtesting Framework

* **Replay Invariant:** At historical simulated time $T$, the engine only accesses data where `created_at < T`.
* **Settlement Verification:** Grades all outcomes against true final match scores stored in `match_settlements`.
* **Output Metrics:** Brier Score ($BS = \frac{1}{N}\sum(P_i - y_i)^2$), Cumulative ROI, Maximum Drawdown (MDD), Profit Factor.

---

## 32. Performance Metrics & Monitoring

* **Selection-Level:** Hit Rate ($> 85\%$ Conservative, $> 75\%$ Balanced), Brier Score ($< 0.15$), Average EV ($\ge +4.0\%$).
* **Slip-Level:** Accumulator Win Rate ($> 40\%$ for 3-leg Balanced), Portfolio ROI ($> +12\%$), Drawdown ($< 25\%$).
* **Source-Level:** Graded tipster and channel accuracy tracked over time.

---

## 33. Temporal Integrity & Data Leakage Safeguards

* **Timestamp Watermarking:** All candidates watermarked with `ingested_at < kickoff_time`.
* **No Future Data:** Strict prohibition of post-match statistics or in-play odds in pre-match slip construction.
* **Model Versioning:** Historical replays bind to the exact model parameters active at simulated timestamp $T$.

---

## 34. Safety Against Overconfidence

* **Explicit Labeling:** All odds-derived percentages labeled as "Bookmaker-Implied Probability".
* **Banned Language:** Zero tolerance for terms like "100% Sure", "Fixed Match", or "Guaranteed Win".
* **Joint Probability Display:** Multi-leg accumulators always display joint win probability alongside payout odds.

---

## 35. Current vs. Future Capability Matrix

| Capability | Current Implementation | Available Data | Gap | Future Requirement |
| :--- | :--- | :--- | :--- | :--- |
| **Fixture Filtering** | `LiveScoreClient.fetch_unstarted_fixtures` | Real unstarted fixtures across 4 sports | No unique match ID | Standardize fixture ID hash |
| **Odds Ingestion** | `SportyBetCatalogService.extract_selections` | Live SportyBet catalog decimal odds | Snapshot odds only | Ingest opening/closing lines |
| **Implied Probability**| `ImpliedProbabilityFilter` | $(1 / \text{odds}) \times 100\%$ | Overround not separated | De-vig market books |
| **Model Probability** | `analyzer.py` (Static tables) | Synthetic lookup values (1.10–1.25) | No statistical ML model | Train calibrated ML model |
| **Expected Value** | None | Raw odds and probabilities | No EV calculation | $(P_{\text{model}} \cdot \text{Odds}) - 1$ engine |
| **Risk Profiles** | Flat probability thresholds | Basic percentage UI buttons | No formal invariants | Formally bounded risk profiles |
| **Candidate Scoring** | Sort by implied probability | Odds only | No composite scoring | Multi-factor utility formula |
| **Correlation Defense**| Single-event fuzzy matching check | Match team names | No cross-market graph | Intra-match conflict graph |
| **Slip Optimization** | Slices top-$k$ candidates | Unordered list of top picks | No target odds optimizer | Bounded Knapsack optimizer |
| **Settlement Tracking**| None | None (Scores unrecorded) | Post-match scores missing | `match_settlements` DB table |
| **Backtesting Engine** | None | None | No replay test harness | Historical backtesting suite |
| **Explainability** | String markdown reports | Human-readable summaries | No machine-readable trace | JSON acceptance/rejection schemas |
| **Observability** | Standard Python logging | Text log streams | No structured JSON logs | Structured audit log emitter |

---

## 36. Proposed Architecture

```
                                  TELEGRAM UI LAYER
                  (handlers/slip_handlers.py, handlers/scan_handlers.py)
                                          │
                                          ▼
                             APPLICATION SERVICES LAYER
                         (BettingService, CustomSlipBuilder)
                                          │
                                          ▼
                      =========================================
                      ||   RISK / BET CONSTRUCTION ENGINE    ||
                      =========================================
                                          │
              ┌───────────────────────────┼───────────────────────────┐
              ▼                           ▼                           ▼
      Fixture Gateway             Catalog Gateway             Learning Gateway
    (LiveScoreClient)          (SportyBetCatalogService)    (TipsterMarketLearner)
              │                           │                           │
              └───────────────────────────┼───────────────────────────┘
                                          │
                                          ▼
                               CANDIDATE POOL (Normalized)
                                          │
                                          ▼
                            HARD SAFETY CONSTRAINTS FILTER
                                          │
                                          ▼
                             COMPOSITE SCORING ENGINE
                                          │
                                          ▼
                            COMBINATORIAL SLIP OPTIMIZER
                                          │
                                          ▼
                               BetConstructionResult
                                          │
              ┌───────────────────────────┴───────────────────────────┐
              ▼                                                       ▼
    Official Booking Client                               Persistence Repository
   (SportyBetBookingClient)                               (DatabaseService / SQLite)
```

---

## 37. Implementation Phases & Roadmap

```
  Phase 1: Domain Contracts (BetCandidate, Request, Result)
     │
     ▼
  Phase 2: Hard Constraint Filter & Rejection Evaluator
     │
     ▼
  Phase 3: Expected Value & Margin De-vigging Module
     │
     ▼
  Phase 4: Multi-Factor Candidate Scoring Engine
     │
     ▼
  Phase 5: Formal Risk Profile Definitions & Invariants
     │
     ▼
  Phase 6: Conflict Graph & Correlation Defense Engine
     │
     ▼
  Phase 7: Combinatorial Slip Optimizer (Knapsack Solver)
     │
     ▼
  Phase 8: Bayesian Source Credibility & Learning Integration
     │
     ▼
  Phase 9: Match Settlement Database & Historical Backtesting
     │
     ▼
  Phase 10: Telegram Workflow Integration & UI Binding
     │
     ▼
  Phase 11: Production Monitoring & Audit Logging
```

### Phase Details

| Phase | Description | Dependencies | Files Likely Affected | Tests Required | Risk Level |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Phase 1** | Data Contracts | None | `models/bet_candidate.py`, `models/engine_contracts.py` | Unit tests for contract instantiation & validation | **LOW** |
| **Phase 2** | Hard Constraints | Phase 1 | `engine/constraint_filter.py` | Tests for kickoff, odds, and freshness rejections | **LOW** |
| **Phase 3** | Expected Value | Phase 1 | `engine/ev_calculator.py` | Tests for $(P \cdot \text{Odds})-1$ and de-vigging | **LOW** |
| **Phase 4** | Candidate Scoring | Phases 1–3 | `engine/scoring_model.py` | Tests for multi-factor weights & normalization | **MEDIUM** |
| **Phase 5** | Risk Profiles | Phases 1–4 | `engine/risk_profiles.py` | Invariant tests for Conservative, Balanced, Aggressive | **LOW** |
| **Phase 6** | Correlation Defense | Phase 1 | `engine/correlation_manager.py` | Intra-match and exposure penalty tests | **MEDIUM** |
| **Phase 7** | Slip Optimizer | Phases 1–6 | `engine/slip_optimizer.py` | Knapsack target odds convergence tests | **HIGH** |
| **Phase 8** | Learning Integration | Phase 4 | `tipster_learning.py`, `learning_engine.py` | Bayesian credibility shrinkage tests | **MEDIUM** |
| **Phase 9** | Settlement & Backtest| Phases 1–7 | `database.py`, `engine/backtest_runner.py` | Replay simulation & Brier calibration tests | **MEDIUM** |
| **Phase 10**| Workflow Integration | Phases 1–8 | `betting_service.py`, `builder.py`, `handlers/` | End-to-end integration tests with mock APIs | **HIGH** |
| **Phase 11**| Observability | Phase 10 | `engine/audit_logger.py` | Log format and latency benchmark tests | **LOW** |

---

## 38. Open Questions (DECISION REQUIRED)

The following items require project owner confirmation before beginning Phase 1 implementation:

1. `[DECISION REQUIRED]` **Candidate Scoring Weights:** Confirm baseline weights ($w_{\text{prob}}=0.35, w_{\text{ev}}=0.25, w_{\text{source}}=0.15, w_{\text{mkt}}=0.15, w_{\text{fresh}}=0.10$).
2. `[DECISION REQUIRED]` **Conservative Minimum Probability Threshold:** Confirm baseline ($85.0\%$ vs $90.0\%$).
3. `[DECISION REQUIRED]` **Target Odds Tolerance Band:** Confirm acceptable tolerance around target combined odds ($\pm 15\%$).
4. `[DECISION REQUIRED]` **Match Settlement Result Scraper:** Confirm whether a background scraper job should harvest finished match scores (`Eps="FT"`) from LiveScore into `match_settlements`.
5. `[DECISION REQUIRED]` **In-Memory Fixture Cache TTL:** Confirm caching duration ($60\text{s} - 120\text{s}$) for catalog responses.

---

## 39. Recommended Next Step

**Execute Phase 1:** Define the pure data contracts (`BetCandidate`, `BetConstructionRequest`, `BetConstructionResult`, `ConstructionStatusCode`, `RejectionCategory`) and unit tests in an isolated module branch without modifying existing handlers or database schemas.

---

# PART II: ENGINEERING FEASIBILITY & IMPLEMENTATION TIERS

---

## 40. Feasibility Matrix & Capability Classification

Every major engine capability specified in Part I is evaluated against the active repository's data structures, database schemas, network APIs, and mathematical reality:

| Capability | Feasibility Status | Existing Evidence / Module | Missing Dependency / Reality Gap | Recommendation for Engineering |
| :--- | :---: | :--- | :--- | :--- |
| **BetCandidate Normalization** | **IMPLEMENTABLE NOW** | `MappedSportyBetSelection`, `DiscoveredFixture` | None (pure domain dataclass abstraction) | Implement in `models/` or `engine/contracts.py` as V1 foundation. |
| **BetConstructionRequest Contract** | **IMPLEMENTABLE NOW** | Wizard params in `handlers/slip_handlers.py` | None | Formalize typed request dataclass separating user config from safety limits. |
| **BetConstructionResult Contract** | **IMPLEMENTABLE NOW** | `CustomSlipResult`, `BookingSlipResponse` | None | Formalize typed accumulator output with explainability metadata. |
| **Hard Safety Constraints** | **IMPLEMENTABLE NOW** | `LiveScoreClient.is_unstarted_match` | None | Implement binary pass/fail filter for kickoff, odds bounds, and freshness TTL. |
| **Fixture-Status Validation** | **IMPLEMENTABLE NOW** | `LiveScoreClient` status (`"NS"`) | None | Hard rejection of started, live, or settled matches ($> \text{Now} + 120\text{s}$). |
| **Decimal Odds Validation** | **IMPLEMENTABLE NOW** | `MappedSportyBetSelection.odds` | None | Enforce $\ge 1.01$ and risk profile bounds ($\text{Odds}_{\text{min}} \le \text{Odds} \le \text{Odds}_{\text{max}}$). |
| **Odds Freshness TTL** | **IMPLEMENTABLE NOW** | Snapshot timestamps | In-memory cache timestamp | Track `ingested_at` timestamp; drop candidates older than 300s. |
| **Implied Probability** | **IMPLEMENTABLE NOW** | `ImpliedProbabilityFilter` | None | Standardize $(1.0 / \text{Odds}) \times 100\%$ with explicit bookmaker label. |
| **Candidate Ranking** | **IMPLEMENTABLE NOW** | `builder.py`, `analyzer.py` | Multi-factor weighting | Implement composite utility score sorting. |
| **Same-Match Conflict Detection** | **IMPLEMENTABLE NOW** | `event_id` in `MappedSportyBetSelection` | None | Strictly enforce maximum 1 selection per match event ID. |
| **Team Multi-Leg Exposure** | **IMPLEMENTABLE NOW** | `home_team`, `away_team` strings | None | Deduplicate teams across slip legs. |
| **League Concentration Limits** | **IMPLEMENTABLE NOW** | `league` field in selections | None | Apply soft penalty if $> 40\%$ legs originate from one league. |
| **Sport Concentration Limits** | **IMPLEMENTABLE NOW** | `sport` field in selections | None | Apply soft penalty if $> 70\%$ legs originate from one sport. |
| **Configuration Risk Profiles** | **IMPLEMENTABLE NOW** | UI threshold buttons (`85%`, `90%`) | Statistical calibration | Use configuration-based boundaries (Conservative, Balanced, Aggressive). |
| **Target Odds Convergence** | **IMPLEMENTABLE NOW** | `BetCalculator.calculate_accumulator` | Multi-objective solver | Constrained greedy beam search converging toward target combined odds. |
| **Selection Count Shortfall** | **IMPLEMENTABLE NOW** | `builder.py` fallback slicing | None | Enforce "No Bad Bets" rule; return best valid subset and warn user. |
| **Explainability Reason Codes** | **IMPLEMENTABLE NOW** | Markdown string formatters | None | Emit machine-readable acceptance/rejection enum codes. |
| **Safe Fallback Degradation** | **IMPLEMENTABLE NOW** | `SportyBetBookingClient` fallback | None | Zero data fabrication; return clean structured explanations on API denial. |
| **Bookmaker Overround De-vigging**| **PREREQUISITE REQUIRED** | `SportyBetCatalogService` | Full 2-way/3-way market book | Calculate $\sum (1/\text{Odds}_i) - 1.0$ when full market outcomes are fetched. |
| **Normalized Historical Bet Legs** | **PREREQUISITE REQUIRED** | `generated_slips` (Monolithic string) | Child relational schema | Add `slip_legs` child table storing candidate IDs, odds, and timestamps. |
| **Settlement Tracking** | **PREREQUISITE REQUIRED** | None | Post-match score scraper | Create `match_settlements` table and scrape finished scores from LiveScore. |
| **Empirical Source Reliability** | **PREREQUISITE REQUIRED** | `tipster_market_learnings` | Graded win/loss counts | Link tipster posts to settlement results to record true hit rate. |
| **Bayesian Sample-Size Shrinkage** | **PREREQUISITE REQUIRED** | Occurrence count only | Graded historical trials | Implement $R = \frac{N}{N+K}\mu_{\text{data}} + \frac{K}{N+K}\mu_{\text{prior}}$ once settlements exist. |
| **Time Decay on Inactivity** | **PREREQUISITE REQUIRED** | `last_seen` timestamp in DB | None | Apply exponential decay $e^{-\lambda \Delta t}$ based on activity gap. |
| **Genuine Model Probability** | **FUTURE INFRASTRUCTURE** | `analyzer.py` (Static lookups) | Trained ML prediction model | Train logistic regression / XGBoost model on historical feature sets. |
| **True Expected Value ($\text{EV}$)** | **FUTURE INFRASTRUCTURE** | None (Assumes $P_{\text{model}} \approx P_{\text{implied}}$) | Calibrated ML probability | Compute $\text{EV} = (P_{\text{ML}} \cdot \text{Odds}) - 1.0$ after ML model is deployed. |
| **Probability Calibration (Brier)**| **FUTURE INFRASTRUCTURE** | None | Settled outcome dataset | Calibrate model probabilities using Platt scaling / isotonic regression. |
| **Historical Odds Timeline** | **FUTURE INFRASTRUCTURE** | Snapshot catalog only | Time-series odds database | Capture opening vs closing odds movements over time. |
| **Historical Prediction Snapshots**| **FUTURE INFRASTRUCTURE** | None | Immutable snapshot store | Store point-in-time feature snapshots at decision timestamp $T$. |
| **Historical Backtesting Engine** | **FUTURE INFRASTRUCTURE** | None | Backtest harness & data | Deterministic replay simulator evaluating ROI, hit rate, and drawdowns. |
| **Empirical Covariance Graph** | **FUTURE INFRASTRUCTURE** | None | Multi-match outcome covariance | Statistical dependency modeling across leagues and referee assignments. |
| **Learned Risk Profiles** | **FUTURE INFRASTRUCTURE** | Static configuration | Reinforcement / Bayesian tuning| Automatically optimize profile thresholds based on realized bankroll Sharpe. |

---

## 41. Probability Reality Audit

A meticulous code trace through [`analyzer.py`](file:///c:/Users/WALE/TELEGRAM-bot/analyzer.py), [`aggregator.py`](file:///c:/Users/WALE/TELEGRAM-bot/aggregator.py), [`probability_filter.py`](file:///c:/Users/WALE/TELEGRAM-bot/probability_filter.py), and [`builder.py`](file:///c:/Users/WALE/TELEGRAM-bot/builder.py) reveals the exact origins of probability in the active system:

```
[SportyBet Live Catalog] ────────► Decimal Odds (e.g. 1.25)
                                          │
                                          ▼
                               [probability_filter.py]
                   Implied Probability = (1.0 / Odds) * 100% = 80.0%
                        (GENUINE BOOKMAKER-IMPLIED PROBABILITY)
                                          ▲
                                          │
[LiveScore Discovered Match] ────► [analyzer.py / aggregator.py]
                               Static Lookup Dictionary:
                               "Home Win" -> "Double Chance (1X)" @ 1.18 (85.0%)
                               (STATIC MARKET MAPPING / SYNTHETIC HEURISTIC)
```

### Engineering Verdict on Probability
1. **Bookmaker-Implied Probability is Genuine:** [`probability_filter.py`](file:///c:/Users/WALE/TELEGRAM-bot/probability_filter.py) accurately calculates mathematical implied probability $(1.0 / \text{odds}) \times 100\%$. This represents the bookmaker's pricing (inclusive of margin).
2. **Consensus Probability is a Static Heuristic:** [`analyzer.py`](file:///c:/Users/WALE/TELEGRAM-bot/analyzer.py) assigns static probabilities from hardcoded dictionaries (e.g. Double Chance $= 85\%$, Over 1.5 $= 90\%$, Draw No Bet $= 80\%$) with synthetic odds ($1.15 - 1.25$). It does **NOT** run statistical machine learning, logistic regression, or dynamic match forecasting.
3. **Implications for V1 Risk Engine:**
   * In V1, the engine must **never** claim to possess "AI/ML predicted probability".
   * V1 must explicitly use **Bookmaker-Implied Probability (de-vigged where book is available)** as the primary probability baseline.
   * V1 will allow consensus heuristic scores as a secondary preference factor, clearly labeled as `Consensus Heuristic`.

---

## 42. Learning Reality Audit

A trace through [`learning_engine.py`](file:///c:/Users/WALE/TELEGRAM-bot/learning_engine.py) and [`tipster_learning.py`](file:///c:/Users/WALE/TELEGRAM-bot/tipster_learning.py) establishes what the system is currently learning:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                WHAT THE SYSTEM ACTUALLY DOES                           │
├───────────────────────────────────┬────────────────────────────────────────────────────┤
│ Subsystem                         │ Concrete Implementation Reality                    │
├───────────────────────────────────┼────────────────────────────────────────────────────┤
│ StrategyLearningEngine            │ Market Discovery: Ingests SportyBet catalog hourly │
│ (learning_engine.py)              │ to record newly active marketId / outcomeId keys.  │
│                                   │ Static Rules: Holds hardcoded combination tuples   │
│                                   │ (e.g. DC + Over 1.5 Goals with static win rate).   │
├───────────────────────────────────┼────────────────────────────────────────────────────┤
│ TipsterMarketLearner              │ Frequency Tracking: Parses regex keywords from     │
│ (tipster_learning.py)             │ forwarded Telegram channel posts and increments    │
│                                   │ occurrence_count in tipster_market_learnings.      │
├───────────────────────────────────┼────────────────────────────────────────────────────┤
│ Predictive Learning               │ NON-EXISTENT: Does NOT track whether tips won/lost,│
│                                   │ does NOT compute Brier calibration, does NOT update│
│                                   │ model weights dynamically based on match outcomes. │
└───────────────────────────────────┴────────────────────────────────────────────────────┘
```

### Engineering Verdict on Learning
* Market occurrence count measures **tipster popularity**, not **tipster accuracy**.
* High frequency $\ne$ high win rate.
* **Implications for V1:** The V1 engine must not use fake Bayesian accuracy. It will use occurrence counts strictly as a `Market Popularity / Provenance Factor` ($w_{\text{source}}$), while true Bayesian predictive learning is scheduled for V1.5 (after settlement tracking is deployed).

---

## 43. Historical Data & Schema Audit

An inspection of [`database.py`](file:///c:/Users/WALE/TELEGRAM-bot/database.py) and the SQLite schema reveals the current data storage state:

```sql
-- CURRENT SCHEMA STATE (database.py)
generated_slips (id, user_id, match_date, sport, game_count, target_odds, actual_odds, min_probability, booking_code, summary_text, created_at)
code_conversions (id, user_id, source_code, source_bookmaker, sportybet_code, provider_used, created_at)
user_preferences (user_id, target_date, target_sport, updated_at)
tipster_market_learnings (id, market_name, sport, occurrence_count, last_seen)
```

### Missing Historical Fields Required for Advanced Intelligence
* ❌ **Normalized Bet Legs:** Individual legs are locked in `summary_text` (monolithic Markdown); cannot query legs by market ID or odds.
* ❌ **Point-in-Time Odds Snapshot:** No record of opening vs closing odds movements.
* ❌ **Point-in-Time Probability Snapshot:** No recording of candidate model probabilities at decision time.
* ❌ **Match Settlement Results:** Match scores are unrecorded post-match; betslips are never marked WON, LOST, or VOID.

---

## 44. Backtesting Feasibility

### Can the System Honestly Execute Historical Backtests Today?
**NO.** The current repository cannot execute a valid historical replay backtest because:
1. Historical odds snapshots at time $T$ are not stored.
2. Historical match outcomes (final scores) are not collected.
3. Simulating on current live odds introduces severe **Look-Ahead Bias** and **Survivorship Bias**.

### Minimum Data Model Required for Backtesting (V1.5 / V2 Prerequisite)
To make genuine backtesting possible, the system will introduce:
1. `match_settlements`: `(event_id, home_team, away_team, home_score, away_score, status, settled_at)`.
2. `historical_candidate_snapshots`: `(snapshot_id, event_id, market_id, outcome_id, odds, implied_prob, recorded_at)`.
3. `slip_settlement_history`: `(slip_id, leg_id, candidate_id, settled_outcome, profit_loss)`.

---

## 45. Risk Profile Realism: Configuration vs. Calibration

* **V1 Reality (Configuration-Based):** Risk profiles will be implemented using **strictly bounded configuration rules** (Conservative: Prob $85\%-98\%$, Odds $1.05-1.25$; Balanced: Prob $75\%-90\%$, Odds $1.15-1.45$; Aggressive: Prob $60\%-80\%$, Odds $1.30-1.85$). This is 100% deterministic, testable, and immediately functional.
* **V2 Target (Data-Calibrated):** Once 1,000+ settled match outcomes are accumulated, thresholds will be calibrated to minimize portfolio variance and maximize realized Sharpe ratio.

---

## 46. Expected Value Realism in V1

$$\text{EV} = (P_{\text{model}} \times \text{Odds}) - 1.0$$
* If $P_{\text{model}} = P_{\text{implied}} = \frac{1}{\text{Odds}}$, then $\text{EV} \equiv 0.0$.
* If market overround $M > 0$ is removed via proportional de-vigging:
  $$P_{\text{devigged}} = \frac{1 / \text{Odds}}{1.0 + M} \implies \text{EV} = (P_{\text{devigged}} \times \text{Odds}) - 1.0 = -\frac{M}{1.0 + M} < 0$$
* **V1 Handling:** V1 will compute **De-vigged Theoretical Edge** or allow user consensus probabilities to express relative preference, while marking EV as a heuristic score component rather than absolute ground truth until ML model training in V2.

---

## 47. Correlation Defense Realism

* **Implementable Now (V1):**
  * Same-match exclusion (`event_id` uniqueness) $\implies$ **100% Achievable**.
  * Single-team appearance across slip legs $\implies$ **100% Achievable**.
  * Portfolio exposure caps (Max 40% legs from same league, Max 70% from same sport) $\implies$ **100% Achievable**.
* **Deferred to V2:** Empirical cross-match covariance matrices (e.g. predicting correlation between two different Premier League matches based on weather or table standings).

---

## 48. Optimizer Complexity & Algorithm Comparison

| Algorithm | Computational Complexity | Target Odds Convergence | Testability & Explainability | Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| **Greedy Top-K Sorting** | $O(N \log N)$ | Poor (Ignores combined multiplier) | High | Too simplistic; misses target odds. |
| **Constrained Greedy / Beam Search** | $O(B \cdot N \cdot K)$ | **Excellent** | **Very High** | **RECOMMENDED FOR V1** (Beam width 20-50). |
| **Dynamic Programming Knapsack** | $O(N \cdot W)$ | Moderate (Requires discretized odds) | Medium | Complex odds discretization. |
| **Integer Linear Programming (ILP)**| $O(2^N)$ worst case | Excellent | Low (Requires solver dependencies) | Over-engineered for 5-25 leg slips. |

**V1 Decision:** Implement **Constrained Greedy with Bounded Beam Search (Beam Width $= 50$)**. It guarantees sub-millisecond execution, deterministic results, zero external solver dependencies, and full testability.

---

## 49. Over-Engineering Audit

| Proposed Feature in Part I | Complexity Evaluation | V1 Classification | Rationale |
| :--- | :--- | :---: | :--- |
| **Bayesian Source Credibility ($K=25$)**| Requires graded trial history | **SIMPLIFY FOR V1** | Use sample-size saturation curve $1 - e^{-N/30}$ on occurrence counts in V1; deploy full Bayesian shrinkage in V1.5. |
| **Brier Score Probability Calibration** | Requires settled outcome database | **DEFER TO V1.5** | Cannot compute $(P_i - y_i)^2$ without match final scores $y_i \in \{0, 1\}$. |
| **Combinatorial Knapsack Optimizer** | Discretized multi-choice DP | **SIMPLIFY FOR V1** | Bounded beam search ($W=50$) provides identical accuracy with zero solver overhead. |
| **Intra-Match Conflict Graph** | Event ID + Team deduping | **IMPLEMENT NOW** | Simple, robust, and completely prevents duplicate match legs. |
| **Configurable Risk Profiles** | Boundary invariants & Kelly sizing | **IMPLEMENT NOW** | Deterministic mathematical rules requiring zero external infrastructure. |
| **Machine-Readable Reason Codes** | JSON enum audit trail | **IMPLEMENT NOW** | Immediate transparency with zero external dependencies. |
| **Historical Replay Simulator** | Requires historical time series | **DEFER TO V2** | Requires historical snapshot ingestion pipeline. |

---

## 50. V1 Minimum Viable Risk Engine Architecture

```
                                  INCOMING REQUEST
             (Bet Builder Wizard / Channel Scanner / CLI / Code Editor)
                                         │
                                         ▼
                             V1 CANDIDATE NORMALIZER
         (Transforms MappedSportyBetSelection / ConsensusPrediction to BetCandidate)
                                         │
                                         ▼
                            V1 HARD SAFETY FILTER
     (Rejects: Kickoff < 120s, Odds < 1.01, Odds > Profile Max, Stale Data > 300s)
                                         │
                                         ▼
                            V1 METRIC ENRICHMENT
         (Calculates Implied Prob %, Fair De-vigged Prob, and Heuristic EV)
                                         │
                                         ▼
                            V1 MULTI-FACTOR SCORER
       (Scores Candidates: S = 0.35*f(P) + 0.25*g(EV) + 0.15*h(Src) + 0.15*m(Mkt) + 0.10*q(Fresh))
                                         │
                                         ▼
                           V1 CORRELATION DEFENDER
              (Eliminates duplicate event IDs & same-team appearances)
                                         │
                                         ▼
                        V1 CONSTRAINED SLIP OPTIMIZER
     (Beam Search W=50 converging on Target Odds without violating candidate quality)
                                         │
                                         ▼
                             V1 EXPLAINABILITY & AUDIT
       (Assembles SelectedBetLeg list, Kelly recommended stake, Bonus %, and Summary)
                                         │
                                         ▼
                               BetConstructionResult
```

---

## 51. V1 Data Contract Specification

```
+-----------------------------------------------------------------------------------+
|                             V1 BetCandidate Contract                              |
+-----------------------------------------------------------------------------------+
| Field Name                  | Type             | V1 Status | Description          |
+-----------------------------+------------------+-----------+----------------------+
| candidate_id                | str              | REQUIRED  | Unique Leg Identifier|
| event_id                    | str              | REQUIRED  | Match Event ID       |
| sport                       | str              | REQUIRED  | Sport Category       |
| league                      | str              | REQUIRED  | Competition Name     |
| home_team                   | str              | REQUIRED  | Home Participant     |
| away_team                   | str              | REQUIRED  | Away Participant     |
| kickoff_time                | Optional[datetime| REQUIRED  | Match Start Time     |
| market_id                   | str              | REQUIRED  | Bookmaker Market ID  |
| market_name                 | str              | REQUIRED  | Market Title         |
| outcome_id                  | str              | REQUIRED  | Selection Outcome ID |
| outcome_name                | str              | REQUIRED  | Selection Pick Name  |
| decimal_odds                | float            | REQUIRED  | Current Decimal Odds |
| specifier                   | Optional[str]    | OPTIONAL  | Market Specifier     |
| bookmaker_implied_prob      | float            | REQUIRED  | (1.0 / Odds) * 100%  |
| model_probability           | float            | REQUIRED  | Normalized Prob (0-1)|
| expected_value              | float            | OPTIONAL  | (Prob * Odds) - 1.0  |
| model_confidence            | float            | OPTIONAL  | Default: 1.0         |
| source_type                 | SourceType       | REQUIRED  | SPORTYBET / TIPSTER  |
| source_name                 | str              | REQUIRED  | Origin Source Name   |
| source_sample_size          | int              | OPTIONAL  | Historical Post Count|
| data_freshness_seconds      | float            | OPTIONAL  | Age of Odds Snapshot |
| is_eligible                 | bool             | REQUIRED  | Hard Filter State    |
| composite_score             | float            | REQUIRED  | Calculated Ranking S |
| source_historical_accuracy  | float            | FUTURE    | Graded Win Rate (V1.5|
+-----------------------------------------------------------------------------------+
```

---

## 52. Implementation Tiers Breakdown

### Tier 1: V1 — IMPLEMENT NOW (Core Engine)
* Pure domain contracts (`BetCandidate`, `BetConstructionRequest`, `BetConstructionResult`).
* Hard safety constraint filtering (kickoff buffer, odds bounds, freshness).
* Bookmaker-implied probability and market overround de-vigging.
* Multi-factor candidate scoring model.
* Configuration-based risk profiles (Conservative, Balanced, Aggressive, Very Aggressive, Custom) with Fractional Kelly sizing.
* Intra-match correlation defense (event ID and team deduplication).
* Constrained greedy beam search slip optimizer.
* Machine-readable explainability and structured reason codes.
* Safe fallback degradation without data fabrication.

### Tier 2: V1.5 — PREREQUISITES (Persistence & Learning Feedback)
* Relational child table `slip_legs` in SQLite to store individual slip selections.
* `match_settlements` table in SQLite.
* Automated background settlement scraper harvesting finished scores (`Eps="FT"`).
* Tipster win/loss grading and true empirical accuracy calculation.
* Full Bayesian shrinkage model ($K=25$) on verified prediction histories.

### Tier 3: V2 — FUTURE INFRASTRUCTURE (ML & Backtesting)
* Statistical machine learning model (Logistic Regression / XGBoost) trained on historical match features.
* Calibrated true model probabilities (Brier score minimization).
* Historical point-in-time snapshot database (odds and feature time series).
* Deterministic backtesting and replay simulation harness.
* Cross-match empirical covariance matrices.

---

## 53. Explicit "DO NOT IMPLEMENT YET IN V1" Registry

To prevent over-engineering and ungrounded implementations, the following features **MUST NOT BE IMPLEMENTED IN V1**:
1. 🚫 **DO NOT** implement statistical ML model training or pretend that `analyzer.py` is an AI neural network.
2. 🚫 **DO NOT** implement Brier score calibration without a settled match outcome database.
3. 🚫 **DO NOT** implement complex Integer Linear Programming (ILP) solvers requiring external C/C++ libraries.
4. 🚫 **DO NOT** simulate fake historical backtests on live odds snapshots.
5. 🚫 **DO NOT** claim tipster occurrence frequency in SQLite is equivalent to prediction accuracy.
6. 🚫 **DO NOT** hardcode synthetic odds when live SportyBet catalog prices are unavailable.

---

## 54. Approved Next Implementation Step

**Execute Tier 1 (V1 Domain Package):**
Implement the standalone domain package under `engine/` containing pure data contracts, hard constraint filters, candidate scoring, configuration risk profiles, correlation defense, and bounded beam search slip optimizer, fully backed by 100% unit test coverage in `tests/`, without modifying Telegram UI handlers or database schemas until domain tests pass cleanly.

---

## 55. Current Implementation Limitations & Semantic Hardening

To ensure complete engineering transparency and prevent misleading claims regarding system capabilities, the following implementation realities and semantic boundaries are strictly established:

1. **Model Probability Availability:**
   - Predictive machine learning models are **NOT YET IMPLEMENTED** in V1.
   - The field `BetCandidate.model_probability` is strictly nullable (`None`) in V1 unless produced by a future genuine ML model.
   - The engine explicitly introduces `ProbabilitySource` enum (`BOOKMAKER_IMPLIED`, `CONSENSUS_HEURISTIC`, `PREDICTIVE_MODEL`, `UNKNOWN`) to prevent conflating implied odds or static tables with predictive AI.

2. **Expected Value (EV) Semantics:**
   - When only bookmaker odds are available, Expected Value is **NOT FABRICATED**; it is marked as `0.0` (market equilibrium) with `is_heuristic = True`.
   - When consensus heuristic probabilities are available, EV is explicitly labeled as `Heuristic Value Edge`.
   - True statistical positive EV requires genuine calibrated predictive probabilities (V2).

3. **Source Reliability Status:**
   - `SourceReliabilityModel` provides a mathematically sound Bayesian shrinkage model ($K=25$).
   - In V1, because settled outcome tracking is not yet active, tipster reliability is treated as heuristic metadata until historical settled trials are recorded (V1.5).

4. **Historical Backtesting Engine:**
   - `BacktestRunner` serves as a deterministic rule evaluation harness for settlement logic and Brier loss calculations.
   - It is **NOT VALIDATED FOR EMPIRICAL HISTORICAL BACKTESTING** until continuous point-in-time time-series snapshots and settled score databases are populated.

5. **Risk Profile Thresholds:**
   - Probability thresholds and Kelly staking fractions in `RiskProfileManager` are **ENGINEERING DEFAULTS** derived from betting domain heuristics, pending empirical calibration against settled match outcomes.

6. **Correlation Defense:**
   - `CorrelationManager` enforces deterministic intra-match single selection rules (conflict graph) and basic portfolio concentration bounds.
   - Cross-fixture statistical covariance modeling is deferred to future infrastructure (V2).

7. **Learning Engine Reality:**
   - `StrategyLearningEngine` and `TipsterMarketLearner` currently track market posting frequency and regex patterns, **NOT PREDICTIVE ACCURACY**. Market frequency is not treated as empirical win rate.


