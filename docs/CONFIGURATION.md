# Telegram Bot Configuration Reference

This document provides a comprehensive guide to environment variables, system settings, and business rule constants configured in [`config.py`](file:///c:/Users/WALE/TELEGRAM-bot/config.py).

## Environment Variables & Secrets

All sensitive credentials and environment-specific settings are loaded safely via `os.getenv` into `EnvironmentConfig`:

| Environment Variable | Category | Required | Description | Placeholder / Example |
| :--- | :--- | :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | Secrets | **Yes** | Auth token issued by BotFather for Telegram API connection. | `TELEGRAM_BOT_TOKEN=<your-token>` |
| `ADMIN_USER_ID` | Authorization | No | Numeric Telegram user ID permitted to execute `/admin` dashboard. | `ADMIN_USER_ID=12345678` |
| `RAPIDAPI_KEY` | Conversion API | No | RapidAPI key for ConvertBetCodes live conversion API. | `RAPIDAPI_KEY=<rapidapi-key>` |
| `BETLOY_API_KEY` | Conversion API | No | Betloy API key fallback for live bet code conversions. | `BETLOY_API_KEY=<betloy-key>` |
| `LOG_LEVEL` | Application | No | Logging verbosity (`INFO`, `DEBUG`, `WARNING`, `ERROR`). | `LOG_LEVEL=INFO` |

---

## External Service Configuration

Configured under `ExternalServiceConfig`:

- **LiveScore CDN Request Timeout:** `8.0` seconds.
- **SportyBet Catalog Request Timeout:** `8.0` seconds.
- **SportyBet Orders Share API Timeout:** `10.0` seconds.
- **RapidAPI / Betloy Conversion API Timeout:** `10.0` seconds.
- **LiveScore Endpoints:** Multi-candidate CDN URL templates for `soccer`, `basketball`, `tennis`, and `hockey`.
- **SportyBet factsCenter API:** Popular events (`/api/ng/factsCenter/popularEvents`) & query (`/api/ng/factsCenter/query`).
- **SportyBet Share Endpoint:** `/api/ng/orders/share`.

---

## Betting Engine Configuration

Configured under `BettingEngineConfig`:

- **Bookmaker-Implied Probability Bounds:** `60.0%` (Min) to `95.0%` (Max).
- **Default Probability Safety Threshold:** `85.0%`.
- **Default Scan Leg Count:** `5` matches.
- **Maximum Custom Slip Leg Count:** `25` matches.
- **Target Accumulator Odds Bounds:** `2.00x` (Min) to `7.00x` (Max).
- **Default Bet Stake:** `₦1,000.00`.
- **Default Country Code:** `"ng"` (Nigeria).

---

## Application & Persistence Settings

Configured under `ApplicationConfig`:

- **SQLite Database Path:** `db/bot_history.db`.
- **Hourly Harvester Job Interval:** `3600` seconds (60 minutes).

---

## Domain Constants

Configured under `DomainConstants`:

- **Supported Sports:** Football, Basketball, Tennis, Ice Hockey.
- **SportyBet Supported Country Domains:** Nigeria (`ng`), Ghana (`gh`), Kenya (`ke`), Uganda (`ug`), Tanzania (`tz`), Zambia (`zm`).
