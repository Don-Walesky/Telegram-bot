"""
Domain Model: BetCandidate
Defines the standard normalized betting opportunity ingested from any data source
(LiveScore fixture discovery, SportyBet live catalog, or Telegram tipster channels).

Phase 1 Domain Contract — Contains NO engine scoring, EV logic, or Telegram dependencies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class SourceType(str, Enum):
    """Origin source of the betting opportunity."""
    LIVESCORE = "LIVESCORE"
    SPORTYBET = "SPORTYBET"
    TIPSTER = "TIPSTER"
    CONSENSUS = "CONSENSUS"
    EXTERNAL_CODE = "EXTERNAL_CODE"


@dataclass
class BetCandidate:
    """
    Standard Normalized Candidate Betting Selection.

    Field Availability Status in Current Codebase:
    - Currently Available: candidate_id, event_id, sport, league, home_team, away_team,
      kickoff_time, market_id, market_name, outcome_id, outcome_name, decimal_odds,
      bookmaker_implied_prob, source_type, source_name.
    - Intentionally Optional / Future Infrastructure: model_probability, model_confidence,
      expected_value, source_historical_accuracy, source_sample_size, composite_score.
      These are nullable so the contract does not fabricate non-existent data.
    """

    # Identity & Fixture Context (REQUIRED)
    candidate_id: str
    event_id: str
    sport: str
    league: str
    home_team: str
    away_team: str
    kickoff_time: Optional[datetime]

    # Market & Selection Context (REQUIRED)
    market_id: str
    market_name: str
    outcome_id: str
    outcome_name: str
    decimal_odds: float
    specifier: Optional[str] = None

    # Probability & Value Metrics
    # bookmaker_implied_prob is required (e.g. 80.0 for 1.25 odds)
    bookmaker_implied_prob: float = 0.0
    # model_probability, model_confidence, expected_value are Optional (None when no ML model exists)
    model_probability: Optional[float] = None
    model_confidence: Optional[float] = None
    expected_value: Optional[float] = None

    # Source & Provenance
    source_type: SourceType = SourceType.SPORTYBET
    source_name: str = "SportyBet Catalog"
    source_historical_accuracy: Optional[float] = None  # None until settlement tracking exists
    source_sample_size: Optional[int] = None
    ingested_at: datetime = field(default_factory=datetime.now)
    data_freshness_seconds: float = 0.0

    # Derived Engine State
    is_eligible: bool = True
    composite_score: Optional[float] = None
    flags: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Lightweight structural invariant validation."""
        if self.decimal_odds <= 0.0:
            raise ValueError(f"Decimal odds must be strictly positive (> 0), got {self.decimal_odds}.")

        # Auto-compute bookmaker implied probability if not explicitly provided
        if self.bookmaker_implied_prob == 0.0 and self.decimal_odds > 0.0:
            self.bookmaker_implied_prob = round((1.0 / self.decimal_odds) * 100.0, 2)

        if not (0.0 <= self.bookmaker_implied_prob <= 100.0):
            raise ValueError(
                f"Bookmaker implied probability must be between 0.0 and 100.0, got {self.bookmaker_implied_prob}."
            )

        if self.model_probability is not None and not (0.0 <= self.model_probability <= 1.0):
            raise ValueError(
                f"Model probability must be between 0.0 and 1.0, got {self.model_probability}."
            )

        if self.model_confidence is not None and not (0.0 <= self.model_confidence <= 1.0):
            raise ValueError(
                f"Model confidence must be between 0.0 and 1.0, got {self.model_confidence}."
            )

    @property
    def fixture_title(self) -> str:
        """Human-readable fixture title."""
        return f"{self.home_team} vs {self.away_team}"

    def to_dict(self) -> Dict[str, Any]:
        """Serializes candidate to standard dictionary representation."""
        return {
            "candidate_id": self.candidate_id,
            "event_id": self.event_id,
            "sport": self.sport,
            "league": self.league,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "kickoff_time": self.kickoff_time.isoformat() if self.kickoff_time else None,
            "market_id": self.market_id,
            "market_name": self.market_name,
            "outcome_id": self.outcome_id,
            "outcome_name": self.outcome_name,
            "decimal_odds": self.decimal_odds,
            "specifier": self.specifier,
            "bookmaker_implied_prob": self.bookmaker_implied_prob,
            "model_probability": self.model_probability,
            "model_confidence": self.model_confidence,
            "expected_value": self.expected_value,
            "source_type": self.source_type.value,
            "source_name": self.source_name,
            "source_historical_accuracy": self.source_historical_accuracy,
            "source_sample_size": self.source_sample_size,
            "ingested_at": self.ingested_at.isoformat(),
            "data_freshness_seconds": self.data_freshness_seconds,
            "is_eligible": self.is_eligible,
            "composite_score": self.composite_score,
            "flags": self.flags,
        }
