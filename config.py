"""
Centralized Configuration & Application Settings Module
Provides typed, immutable, validated configuration classes for environment secrets,
external service endpoints & timeouts, betting engine constraints, application paths,
and domain constants.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


def parse_bool(val: Optional[str], default: bool = False) -> bool:
    """Safely parse boolean environment variable string values."""
    if val is None:
        return default
    return str(val).strip().lower() in ("true", "1", "yes", "on", "t")


@dataclass(frozen=True)
class EnvironmentConfig:
    telegram_bot_token: Optional[str] = field(
        default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN")
    )
    rapidapi_key: Optional[str] = field(
        default_factory=lambda: os.getenv("RAPIDAPI_KEY") or os.getenv("CONVERTBETCODES_API_KEY")
    )
    betloy_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("BETLOY_API_KEY")
    )
    admin_user_id: Optional[str] = field(
        default_factory=lambda: os.getenv("ADMIN_USER_ID")
    )


@dataclass(frozen=True)
class ExternalServiceConfig:
    livescore_timeout: float = 8.0
    sportybet_timeout: float = 8.0
    booking_api_timeout: float = 10.0
    conversion_api_timeout: float = 10.0
    livescore_candidate_urls: List[str] = field(
        default_factory=lambda: [
            "https://prod-cdn-mev-api.livescore.com/v1/api/app/date/{sport}/{date}/1?locale=en",
            "https://prod-public-api.livescore.com/v1/api/react/date/{sport}/{date}/0.00?MD=1",
            "https://prod-public-api.livescore.com/v1/api/app/date/{sport}/{date}/0",
        ]
    )
    sportybet_popular_url: str = "https://www.sportybet.com/api/ng/factsCenter/popularEvents"
    sportybet_query_url: str = "https://www.sportybet.com/api/ng/factsCenter/query"
    sportybet_share_url: str = "https://www.sportybet.com/api/ng/orders/share"
    rapidapi_convert_url: str = "https://convert-bet-codes-api1.p.rapidapi.com/v1/convert"
    rapidapi_host: str = "convert-bet-codes-api1.p.rapidapi.com"
    betloy_convert_url: str = "https://api.betloy.com/v1/convert"


@dataclass(frozen=True)
class BettingEngineConfig:
    min_implied_probability: float = 60.0
    max_implied_probability: float = 95.0
    default_min_probability: float = 85.0
    default_scan_legs: int = 5
    max_custom_legs: int = 25
    min_odds: float = 1.01
    min_target_odds: float = 2.00
    max_target_odds: float = 7.00
    default_stake: float = 1000.0
    default_country_code: str = "ng"


@dataclass(frozen=True)
class ApplicationConfig:
    db_dir: str = field(
        default_factory=lambda: os.path.join(os.path.dirname(os.path.abspath(__file__)), "db")
    )
    db_path: str = field(
        default_factory=lambda: os.path.join(os.path.dirname(os.path.abspath(__file__)), "db", "bot_history.db")
    )
    hourly_market_scan_interval: int = 3600
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper()
    )


@dataclass(frozen=True)
class DomainConstants:
    supported_sports: List[str] = field(
        default_factory=lambda: ["Football", "Basketball", "Tennis", "Ice Hockey"]
    )
    sport_id_map: Dict[str, str] = field(
        default_factory=lambda: {
            "football": "sr:sport:1",
            "soccer": "sr:sport:1",
            "basketball": "sr:sport:2",
            "tennis": "sr:sport:5",
            "ice hockey": "sr:sport:4",
            "hockey": "sr:sport:4",
        }
    )
    livescore_sport_map: Dict[str, str] = field(
        default_factory=lambda: {
            "football": "soccer",
            "soccer": "soccer",
            "basketball": "basketball",
            "tennis": "tennis",
            "ice hockey": "hockey",
            "hockey": "hockey",
        }
    )
    sportybet_domain_map: Dict[str, str] = field(
        default_factory=lambda: {
            "ng": "https://www.sportybet.com/ng/",
            "gh": "https://www.sportybet.com/gh/",
            "ke": "https://www.sportybet.com/ke/",
            "ug": "https://www.sportybet.com/ug/",
            "tz": "https://www.sportybet.com/tz/",
            "zm": "https://www.sportybet.com/zm/",
        }
    )


@dataclass(frozen=True)
class Config:
    env: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    services: ExternalServiceConfig = field(default_factory=ExternalServiceConfig)
    betting: BettingEngineConfig = field(default_factory=BettingEngineConfig)
    app: ApplicationConfig = field(default_factory=ApplicationConfig)
    domain: DomainConstants = field(default_factory=DomainConstants)

    def validate(self) -> None:
        """Validates critical business constraints and configuration invariants."""
        if not (0.0 <= self.betting.min_implied_probability <= 100.0):
            raise ValueError("min_implied_probability must be between 0.0 and 100.0")
        if not (0.0 <= self.betting.max_implied_probability <= 100.0):
            raise ValueError("max_implied_probability must be between 0.0 and 100.0")
        if self.betting.max_implied_probability < self.betting.min_implied_probability:
            raise ValueError("max_implied_probability cannot be less than min_implied_probability")
        if self.betting.default_scan_legs <= 0:
            raise ValueError("default_scan_legs must be positive")
        if self.services.livescore_timeout <= 0:
            raise ValueError("livescore_timeout must be positive")
        if self.services.sportybet_timeout <= 0:
            raise ValueError("sportybet_timeout must be positive")
        if self.services.booking_api_timeout <= 0:
            raise ValueError("booking_api_timeout must be positive")
        if self.services.conversion_api_timeout <= 0:
            raise ValueError("conversion_api_timeout must be positive")


# Global application configuration instance
config = Config()
config.validate()
