# Telegram Bot Architecture Audit

## 1. Executive Summary

This document provides a comprehensive architectural baseline, module dependency analysis, security audit, and refactoring roadmap for **Telegram-bot** ([Don-Walesky/Telegram-bot](https://github.com/Don-Walesky/Telegram-bot)).

### Key System Attributes
- **Primary Tech Stack:** Python 3.11 / 3.14, `python-telegram-bot` v22.8 (async framework), `httpx` 0.28.1, `python-dotenv`, SQLite 3.
- **Core Purpose:** Automated Telegram sports betting intelligence assistant providing LiveScore multi-sport fixture discovery (Football, Basketball, Tennis, Ice Hockey), SportyBet live catalog fuzzy matching, bookmaker-implied probability calculation, high-safety betslip construction, booking code conversion (Bet9ja, 1xBet, 22Bet to SportyBet), and tipster channel market pattern learning.
- **Current Operational Status:** Fully functional baseline. **34 / 34 unit tests pass (`OK`)** with 100% clean test execution. Deployment-ready via Docker, Docker Compose, and Heroku / Railway worker (`Procfile`).
- **Audit Findings:** The core domain logic is functional and honest (zero fake fixture injections, zero fabricated booking codes, explicit labeling of bookmaker-implied probability). However, technical debt exists in `bot.py` (which acts as a monolithic controller carrying handler, UI, and inline orchestration logic), duplicate test scripts in the root directory, per-request HTTP client instantiation, and uncalibrated learning models.

---

## 2. Current Architecture

The system follows an implicit 4-layer structure, heavily orchestrated by `bot.py`.

```
                  +-------------------------------------------------+
                  |          Telegram User Interface Layer          |
                  |     (Telegram App / Inline Keyboards / Bot)     |
                  +-----------------------+-------------------------+
                                          |
                                          v
                  +-------------------------------------------------+
                  |          Monolithic Controller (bot.py)         |
                  |   Commands, Callbacks, Wizards, Event Loop      |
                  +-------+-------------------+-----------------+---+
                          |                   |                 |
                          v                   v                 v
+-------------------------------------------------------------+
|               Application Services Layer                    |
| (BettingService, CustomSlipBuilder, ChannelSlipSiever,     |
| CodeEditor, BetCodeConverter, StrategyLearningEngine)       |
+-----------------+-------------------------------------------+
                  |                            |
                  +-----------------+----------+
                                    |
                                    v
                  +-------------------------------------------------+
                  |          External Integration Clients           |
                  | (LiveScoreClient, SportyBetCatalogService,      |
                  |  SportyBetBookingClient, RapidAPI, Betloy)      |
                  +-------------------------------------------------+
```

---

## 3. Module Responsibility Map

| Module | Responsibility | Dependencies | Risk | Future Role |
| :--- | :--- | :--- | :--- | :--- |
| [`bot.py`](file:///c:/Users/WALE/TELEGRAM-bot/bot.py) | Main entry point, Telegram application initialization, command handlers registration, background jobs. | Telegram UI modules | **LOW** | Presentation Layer / App Router |
| [`handlers/scan_handlers.py`](file:///c:/Users/WALE/TELEGRAM-bot/handlers/scan_handlers.py) | Handles standard scan commands (/today, /tomorrow, /scan, /sports) and scan callback queries. | `betting_service`, `keyboards` | **LOW** | Scan Telegram UI Handlers |
| [`keyboards.py`](file:///c:/Users/WALE/TELEGRAM-bot/keyboards.py) | Centralized UI inline keyboard builders for main menu, sport selections, wizards, and siever options. | `telegram` | **LOW** | UI Keyboard Layout Provider |
| [`betting_service.py`](file:///c:/Users/WALE/TELEGRAM-bot/betting_service.py) | Core application service orchestrating end-to-end fixture discovery, SportyBet catalog matching, implied probability filtering, and booking code generation. | `livescore_client`, `sportybet_catalog`, `probability_filter`, `sportybet_booking` | **LOW** | Core Betting Application Service |
| [`livescore_client.py`](file:///c:/Users/WALE/TELEGRAM-bot/livescore_client.py) | Ingests unstarted fixtures across 4 sports from LiveScore REST CDN endpoints. | `httpx`, `datetime`, `re` | **MEDIUM** | Ingestion Gateway Service |
| [`sportybet_catalog.py`](file:///c:/Users/WALE/TELEGRAM-bot/sportybet_catalog.py) | Queries SportyBet live catalog, flattens tournaments, fuzzy matches teams. | `httpx`, `SequenceMatcher`, `livescore_client` | **MEDIUM** | Bookmaker Catalog Gateway |
| [`probability_filter.py`](file:///c:/Users/WALE/TELEGRAM-bot/probability_filter.py) | Calculates $(1 / \text{odds}) \times 100\%$ implied probability and filters picks within safety range. | `sportybet_catalog` | **LOW** | Core Domain Calculation Service |
| [`sportybet_booking.py`](file:///c:/Users/WALE/TELEGRAM-bot/sportybet_booking.py) | Re-validates odds, submits payload to SportyBet Share API, formats summary output. | `httpx`, `probability_filter` | **MEDIUM** | Booking & Load Link Service |
| [`builder.py`](file:///c:/Users/WALE/TELEGRAM-bot/builder.py) | Generates custom slips up to 25 games for 7-day schedule window & target odds. | `analyzer`, `calculator`, `sportybet` | **MEDIUM** | Slip Construction Service |
| [`channel_siever.py`](file:///c:/Users/WALE/TELEGRAM-bot/channel_siever.py) | Scans watched channel codes/posts, sieves picks against safety thresholds (85%-95%). | `sportybet_booking`, `sportybet_catalog`, `probability_filter` | **LOW** | Channel Intelligence Service |
| [`code_converter.py`](file:///c:/Users/WALE/TELEGRAM-bot/code_converter.py) | Converts external booking codes (Bet9ja, 1xBet) to SportyBet via RapidAPI/Betloy. | `httpx`, `os`, `dotenv` | **LOW** | Code Conversion Gateway |
| [`code_editor.py`](file:///c:/Users/WALE/TELEGRAM-bot/code_editor.py) | Parses posted booking codes, filters out high-risk legs, and recalculates safe slip. | `analyzer`, `calculator`, `sportybet` | **LOW** | Slip Filtering Engine |
| [`aggregator.py`](file:///c:/Users/WALE/TELEGRAM-bot/aggregator.py) | Aggregates raw predictions derived strictly from ingested LiveScore fixtures. | `livescore_client`, `analyzer` | **LOW** | Prediction Aggregator |
| [`analyzer.py`](file:///c:/Users/WALE/TELEGRAM-bot/analyzer.py) | Groups raw predictions, calculates average consensus probability, formats reports. | `aggregator`, `sportybet` | **MEDIUM** | Prediction Analyzer Engine |
| [`calculator.py`](file:///c:/Users/WALE/TELEGRAM-bot/calculator.py) | Calculates accumulator payout, SportyBet multiple bonus ladder, and Fractional Kelly stake. | Standard Python math | **LOW** | Betting Odds Math Library |
| [`learning_engine.py`](file:///c:/Users/WALE/TELEGRAM-bot/learning_engine.py) | Runs hourly SportyBet live catalog harvester and holds combination strategy rules. | `sportybet_catalog`, `tipster_learning` | **LOW** | Market Harvester & Strategy Model |
| [`tipster_learning.py`](file:///c:/Users/WALE/TELEGRAM-bot/tipster_learning.py) | Extracts market patterns from channel posts & converted codes, persists popularity in DB. | `re`, `database` | **LOW** | Channel Pattern Learner |
| [`channel_monitor.py`](file:///c:/Users/WALE/TELEGRAM-bot/channel_monitor.py) | Tracks target Telegram channels (`@jhgfdghgdhjjj`, `@thirty9bilns`, `+uvIZ...`), reports stats. | Dataclasses | **LOW** | Channel Metadata Registry |
| [`database.py`](file:///c:/Users/WALE/TELEGRAM-bot/database.py) | SQLite connection pool, schema migrations, slip history, code conversions, tipster rankings. | `sqlite3`, `os` | **LOW** | Persistence Layer Repository |
| [`fixtures.py`](file:///c:/Users/WALE/TELEGRAM-bot/fixtures.py) | Formats daily high-probability football tips and preset rollover tickets. | `analyzer` | **LOW** | Preset Tips Service |
| [`sportybet.py`](file:///c:/Users/WALE/TELEGRAM-bot/sportybet.py) | Regex parser for SportyBet booking code formats & URL formatter for 6 country domains. | `re`, `random`, `code_converter` | **LOW** | SportyBet Utilities |

---

## 4. Telegram Interaction Architecture

User interaction flows are powered by `python-telegram-bot` async handlers:

```
[User /start Command]
        │
        ▼
[Main Menu Keyboard]
├── 1. 🛠️ Build Betslip  ──────► 5-Step Custom Wizard: Date (7-day window) ➔ Sport ➔ Odds (2.0-7.0x) ➔ Count (5-25) ➔ Safety (85-95%)
├── 2. 📡 Scan Channels  ──────► 2-Step Sieving Wizard: Safety Threshold (85-95%) ➔ Game Count (3-10)
├── 3. 📅 Today's Scan   ──────► Immediate LiveScore + SportyBet Scan (Today's Unstarted)
├── 4. 📆 Tomorrow's Scan──────► Immediate LiveScore + SportyBet Scan (Tomorrow's Unstarted)
├── 5. 📜 My Slip History──────► Fetches last 5 slips from SQLite database (generated_slips table)
├── 6. 🎟️ View Current Slip───► Displays active context slip with SportyBet load link
├── 7. 🧠 Learning Engine──────► Triggers on-demand catalog market scan & displays tipster market rankings
├── 8. 📊 System Status  ──────► Displays API health, database size, and configuration checklist
├── 9. 🔄 Convert Code   ──────► Prompts `/convert <code> [bookmaker]` (Bet9ja, 1xBet -> SportyBet)
└── 10. ℹ️ Help & Commands ────► Interactive CLI command guide
```

### Async Flow Safety
Long-running scan pipelines (`BettingService.execute_scan_pipeline`, `CustomSlipBuilder.generate_custom_slip`, `ChannelSlipSiever.scan_and_sieve_channel_slips`) are wrapped in `await asyncio.to_thread(...)` to ensure the Telegram event loop remains non-blocking.

---

## 5. Betting Intelligence Pipeline

The end-to-end data flow operates in 8 distinct stages:

```
+-----------------------------------------------------------------------------------+
| Stage 1: Fixture Discovery                                                        |
| Ingests unstarted matches from LiveScore CDN (date_param=YYYYMMDD).               |
| Filters out started matches (Eps="FT", "HT", "63'") & kickoff_dt <= datetime.now().|
+----------------------------------------+------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Stage 2: SportyBet Catalog Query & Matching                                      |
| Queries SportyBet factsCenter API across target sports.                           |
| Flattens tournament wrappers & fuzzy-matches team names (SequenceMatcher >= 0.65).|
+----------------------------------------+------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Stage 3: Market & Odds Extraction                                                 |
| Extracts market IDs (e.g. 18=Double Chance, 10=Over/Under), outcome IDs, and odds.|
+----------------------------------------+------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Stage 4: Implied Probability Calculation                                          |
| Formula: Implied Probability = (1.0 / decimal_odds) * 100%                         |
+----------------------------------------+------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Stage 5: Safety Filtering & Ranking                                               |
| Filters selections within safety range (e.g., 60.0% to 95.0%).                    |
| Sorts picks by highest implied probability.                                       |
+----------------------------------------+------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Stage 6: Bet Slip Construction & Bonus Calculation                                |
| Computes total accumulator odds: Total Odds = product(odds_i).                    |
| Calculates SportyBet Multiple Bonus & Fractional Kelly recommended stake.         |
+----------------------------------------+------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Stage 7: Official Booking Code Submission & Fallback                              |
| Submits JSON payload to SportyBet share API endpoint: /api/ng/orders/share.       |
| If HTTP 200 & bizCode 10000: Returns real share code & URL.                       |
| If HTTP 202 / Session Required: Returns clean fallback with recreation guide.     |
+----------------------------------------+------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Stage 8: Telegram Delivery & Persistence                                          |
| Formats Telegram Markdown summary with direct SportyBet load link.                |
| Saves slip record to SQLite database: db/bot_history.db.                          |
+-----------------------------------------------------------------------------------+
```

---

## 6. Database Architecture

The system uses SQLite 3 located at [`db/bot_history.db`](file:///c:/Users/WALE/TELEGRAM-bot/db/bot_history.db).

### Database Schema
```sql
-- 1. Generated Bet Slips History
CREATE TABLE IF NOT EXISTS generated_slips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    match_date TEXT,
    sport TEXT,
    game_count INTEGER,
    target_odds REAL,
    actual_odds REAL,
    min_probability REAL,
    booking_code TEXT,
    summary_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. External Code Conversions
CREATE TABLE IF NOT EXISTS code_conversions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    source_code TEXT,
    source_bookmaker TEXT,
    sportybet_code TEXT,
    provider_used TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. User Preferences
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INTEGER PRIMARY KEY,
    target_date TEXT DEFAULT 'Today',
    target_sport TEXT DEFAULT 'All',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Tipster Market Popularity Trends
CREATE TABLE IF NOT EXISTS tipster_market_learnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_name TEXT UNIQUE,
    sport TEXT DEFAULT 'Football',
    occurrence_count INTEGER DEFAULT 1,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Safety Features
- **Auto-Initialization:** `DatabaseService._get_connection()` runs schema auto-creation on the first connection call, ensuring isolated test environments succeed seamlessly.
- **Automated Backup Utility:** [`scripts/backup_db.py`](file:///c:/Users/WALE/TELEGRAM-bot/scripts/backup_db.py) generates timestamped backups in `db/backups/`.

---

## 7. Learning Architecture

The application implements a dual learning system:

```
                          ┌───────────────────────────┐
                          │   Learning Engine System  │
                          └─────────────┬─────────────┘
                                        │
           ┌────────────────────────────┴──────────────────────────┐
           ▼                                                       ▼
┌───────────────────────────────────────┐       ┌──────────────────────────────────────┐
│       StrategyLearningEngine          │       │        TipsterMarketLearner          │
│ - Scans SportyBet catalog hourly      │       │ - Parses channel posts & convert     │
│ - Discovers new active market types   │       │   codes via Regex market patterns    │
│ - Indexes market IDs & outcomes       │       │ - Tracks occurrence frequency in DB  │
│ - Ranks high-win market combos        │       │ - Computes tipster popularity %      │
└───────────────────────────────────────┘       └──────────────────────────────────────┘
```

### Machine Learning & Data Requirements
Currently, the system is **rule-based and statistical (odds-implied probability)**. To transition to predictive Machine Learning (e.g., XGBoost, Logistic Regression, or Brier-calibrated probabilities), the system will eventually require:
1. **Historical Match Results Dataset:** Storing actual final scores, halftime scores, and match statistics.
2. **Settlement Tracking Table:** Recording win/loss outcomes of generated slips against actual match results.
3. **Closing Odds Timeline:** Ingesting opening vs. closing bookmaker odds movements.

---

## 8. External Integrations

| Service / Endpoint | Purpose | Auth | Timeout | Fallback / Failure Behavior | Isolation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **LiveScore CDN** (`prod-cdn-mev-api.livescore.com`) | Ingests unstarted fixtures across 4 sports. | None (Public User-Agent) | 8.0s | Iterates through 3 candidate URLs; returns empty list if all fail. | Isolated |
| **SportyBet Popular Events** (`/factsCenter/popularEvents`) | Queries SportyBet upcoming schedule. | None (`Clientid: web`) | 8.0s | Falls back to Query endpoint; returns clear error message if catalog empty. | Isolated |
| **SportyBet Query API** (`/factsCenter/query`) | Secondary SportyBet catalog endpoint. | None (`Clientid: web`) | 8.0s | Returns empty array if unavailable. | Isolated |
| **SportyBet Share API** (`/orders/share`) | Submits selection IDs to lock official booking code. | Web Session Headers | 10.0s | If HTTP 202 / Auth required: returns clean fallback with manual recreation guide. Never fabricates codes. | Isolated |
| **RapidAPI ConvertBetCodes** (`convert-bet-codes-api1.p.rapidapi.com`) | Converts Bet9ja/1xBet codes to SportyBet. | `x-rapidapi-key` | 10.0s | Falls back to Betloy API or local fallback code generator. | Isolated |
| **Betloy API** (`api.betloy.com`) | Secondary bet code conversion service. | `Bearer` token | 10.0s | Falls back to local fallback response. | Isolated |

---

## 9. Technical Debt

| Debt Item | Risk Rank | Impact | Recommendation |
| :--- | :--- | :--- | :--- |
| **Monolithic `bot.py`** | **HIGH** | `bot.py` contains ~937 lines combining handlers, keyboard builders, wizards, background jobs, and pipeline execution. | Decompose into `handlers/`, `keyboards/`, and `services/`. |
| **Duplicate `test_*.py` files in Root Directory** | **MEDIUM** | 8 `test_*.py` files exist in the repository root alongside the canonical test files in `tests/`. Root `test_analyzer.py` contains obsolete string assertions. | Remove root `test_*.py` files and maintain `tests/` as the single source of truth. |
| **Un-cached HTTP Requests** | **MEDIUM** | Sequential calls to `LiveScoreClient` and `SportyBetCatalogService` create new HTTP connections on every scan. | Implement short-lived caching (60s-120s TTL) for fixture and catalog responses. |
| **Direct Instantiation of `httpx.Client()`** | **MEDIUM** | Re-creating `httpx.Client` contexts per method call prevents TCP connection pooling. | Use a shared singleton `httpx.AsyncClient` session. |
| **Import Cycles in Analysis Engines** | **LOW** | `aggregator.py` imports `analyzer.py` inside `get_upcoming_fixtures()`. | Move market conversion helpers to a dedicated domain module (`market_mapper.py`). |
| **Static Keyword Arguments in Legacy Functions** | **LOW** | Hardcoded default odds (`1.15`-`1.25`) in `convert_to_safe_market()` fallback logic. | Ensure live bookmaker catalog odds are always preferred. |

---

## 10. Duplication

1. **Test Files:** 8 test files (`test_analyzer.py`, `test_builder.py`, `test_code_editor.py`, `test_converter.py`, `test_learning_engine.py`, `test_multisport.py`, `test_real_mapping.py`, `test_sportybet.py`) exist in both the root directory and `tests/`.
2. **Sport Category Keyboards:** `build_sport_keyboard()` and `build_wiz_sport_keyboard()` in `bot.py` contain identical button structures.
3. **Markdown Text Sanitizer:** `clean_md()` function is defined repeatedly across `analyzer.py` and `builder.py`.

---

## 11. Reliability Risks

- **SportyBet Official Share Endpoint Authentication:** SportyBet's `/orders/share` endpoint returns HTTP 202 when called from automated IP addresses without browser session cookies. The bot handles this gracefully by returning a clean manual recreation summary, but generating direct online booking codes requires headful browser session context.
- **Date String Parsing Robustness:** `LiveScoreClient` parses `"YYYY-MM-DD"`. Standardizing date handling across all wizard callbacks ensures zero edge-case errors across month/year boundaries.

---

## 12. Security Risks

- **Secrets Handling:** Checked and verified: `.env` is listed in `.gitignore` and has **NEVER** been committed to Git history.
- **Admin Authorization:** `/admin` command checks `os.getenv("ADMIN_USER_ID")` to prevent unauthorized access to user statistics.

---

## 13. Testing Coverage

### Executed Baseline Test Results
Command executed: `python -m unittest discover -s tests -p "test_*.py"`
- **Total Tests:** 34
- **Passed:** 34
- **Failed:** 0
- **Errors:** 0
- **Test Suite Status:** **`OK` (Clean Run)**

### Test Coverage Analysis
- **Covered:** `test_analyzer`, `test_builder`, `test_channel_siever`, `test_code_editor`, `test_converter`, `test_database`, `test_learning_engine`, `test_multisport`, `test_real_mapping`, `test_sportybet`, `test_tipster_learning`.
- **Not Covered by Automated Unit Tests:** Async Telegram UI handlers in `bot.py` (require Telegram `Update` test harness or mock context).

---

## 14. Performance Opportunities

1. **Fixture & Catalog Response Caching:** Cache LiveScore fixtures (60s TTL) and SportyBet catalog responses (120s TTL) to prevent repeated network requests during high user concurrency.
2. **Persistent Async HTTP Session:** Replace per-request `with httpx.Client()` blocks with a shared `httpx.AsyncClient()` to re-use connection pools.

---

## 15. Proposed Target Architecture

The recommended modular target architecture for future phases:

```
TELEGRAM-BOT REPOSITORY
│
├── bot.py                      # Main entrypoint & Application lifecycle
├── config.py                   # Centralized configuration & environment loader
│
├── handlers/                   # Telegram UI Handlers
│   ├── start.py                # Main menu & start commands
│   ├── wizard.py               # Custom Slip & Channel Sieving Wizards
│   ├── scan.py                 # Today / Tomorrow / Custom Scan handlers
│   └── convert.py              # Code conversion handlers
│
├── services/                   # Application Services
│   ├── betting_pipeline.py    # Unified LiveScore -> Catalog -> Booking pipeline
│   ├── channel_siever.py       # Telegram Channel slip siever
│   └── code_converter.py       # External bookmaker code conversion
│
├── domain/                     # Pure Business Logic & Domain Models
│   ├── probability.py          # Bookmaker-implied probability formulas
│   ├── calculator.py           # Odds, bonus, & Kelly criterion formulas
│   └── learning.py             # Strategy learning & market trend analytics
│
├── integrations/               # External Gateways & Clients
│   ├── livescore.py            # LiveScore API Client
│   ├── sportybet_catalog.py    # SportyBet Catalog & Event Matcher
│   ├── sportybet_booking.py    # SportyBet Share API Client
│   └── conversion_api.py       # RapidAPI / Betloy Client
│
├── infrastructure/             # Persistence & System Utilities
│   ├── database.py             # SQLite Data Access Object (DAO)
│   └── http_client.py          # Shared HTTP Client Session Provider
│
└── tests/                      # Canonical Test Suite
    └── test_*.py               # All unit & integration tests
```

---

## 16. Refactoring Roadmap

- **Phase 1 — Safety & Baseline (Current Step):** Audit codebase, verify 100% clean test suite, document architecture, and remove root-level duplicate test artifacts.
- **Phase 2 — Clean Up Root Artifacts & Build Shared HTTP Client:** Remove obsolete root `test_*.py` files and establish a shared `httpx.AsyncClient` provider.
- **Phase 3 — Core Pipeline Consolidation:** Extract unified betting pipeline into a dedicated service layer (`betting_pipeline.py`).
- **Phase 4 — Telegram Handler Decomposition:** Modularize `bot.py` into separate handler files inside `handlers/`.
- **Phase 5 — Response Caching & Concurrency Optimization:** Add 60s TTL memory cache for LiveScore and SportyBet catalog responses.
- **Phase 6 — Observability & Error Monitoring:** Add structured JSON logging and health check endpoints.
- **Phase 7 — Prediction Calibration & Outcome Tracking:** Add settlement tracking to evaluate historical accuracy against real match outcomes.
- **Phase 8 — Production Scaling:** Prepare production Docker container for multi-worker container deployments.

---

## 17. Recommended Next Change

### Single Highest-Value, Lowest-Risk Next Change
**Clean up root-level duplicate test files and obsolete `.pyc` artifacts, ensuring `tests/` remains the single canonical test suite directory.**

### Exact Files Affected
1. `test_analyzer.py` (Delete root duplicate file)
2. `test_builder.py` (Delete root duplicate file)
3. `test_code_editor.py` (Delete root duplicate file)
4. `test_converter.py` (Delete root duplicate file)
5. `test_learning_engine.py` (Delete root duplicate file)
6. `test_multisport.py` (Delete root duplicate file)
7. `test_real_mapping.py` (Delete root duplicate file)
8. `test_sportybet.py` (Delete root duplicate file)
