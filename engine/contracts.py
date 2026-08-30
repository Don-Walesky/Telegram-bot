"""
Domain Data Contracts for the Risk and Bet Construction Engine
Defines typed enums, normalized candidate models, input requests, selected legs,
rejection traces, and complete accumulator construction results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class WorkflowType(str, Enum):
    BET_BUILDER = "BET_BUILDER"
    SCAN_CHANNELS = "SCAN_CHANNELS"
    STANDARD_SCAN = "STANDARD_SCAN"
    CODE_EDITOR = "CODE_EDITOR"
    CLI = "CLI"


class RiskProfile(str, Enum):
    CONSERVATIVE = "CONSERVATIVE"
    BALANCED = "BALANCED"
    AGGRESSIVE = "AGGRESSIVE"
    VERY_AGGRESSIVE = "VERY_AGGRESSIVE"
    CUSTOM = "CUSTOM"


class SourceType(str, Enum):
    LIVESCORE = "LIVESCORE"
    SPORTYBET = "SPORTYBET"
    TIPSTER = "TIPSTER"
    CONSENSUS = "CONSENSUS"
    EXTERNAL_CODE = "EXTERNAL_CODE"


class ConstructionStatusCode(str, Enum):
    OPTIMAL = "OPTIMAL"
    SUB_OPTIMAL = "SUB_OPTIMAL"
    INSUFFICIENT_CANDIDATES = "INSUFFICIENT_CANDIDATES"
    NO_FIXTURES = "NO_FIXTURES"
    CATALOG_OFFLINE = "CATALOG_OFFLINE"
    TARGET_ODDS_UNMET = "TARGET_ODDS_UNMET"
    FAILED = "FAILED"


class RejectionCategory(str, Enum):
    MATCH_ALREADY_STARTED = "MATCH_ALREADY_STARTED"
    INVALID_ODDS = "INVALID_ODDS"
    ODDS_TOO_LOW = "ODDS_TOO_LOW"
    ODDS_TOO_HIGH = "ODDS_TOO_HIGH"
    PROBABILITY_BELOW_THRESHOLD = "PROBABILITY_BELOW_THRESHOLD"
    NEGATIVE_EV = "NEGATIVE_EV"
    STALE_DATA = "STALE_DATA"
    UNMAPPED_MARKET = "UNMAPPED_MARKET"
    LOW_SIMILARITY_MATCH = "LOW_SIMILARITY_MATCH"
    CORRELATED_EVENT = "CORRELATED_EVENT"
    LEAGUE_EXPOSURE_EXCEEDED = "LEAGUE_EXPOSURE_EXCEEDED"
    SPORT_EXPOSURE_EXCEEDED = "SPORT_EXPOSURE_EXCEEDED"
    EXCLUDED_LEAGUE = "EXCLUDED_LEAGUE"
    UNSPECIFIED = "UNSPECIFIED"


@dataclass
class BetCandidate:
    # Identity & Fixture Context
    candidate_id: str
    event_id: str
    sport: str
    league: str
    home_team: str
    away_team: str
    kickoff_time: Optional[datetime]

    # Market & Selection Context
    market_id: str
    market_name: str
    outcome_id: str
    outcome_name: str
    decimal_odds: float
    specifier: Optional[str] = None

    # Probabilities & Value Metrics
    bookmaker_implied_prob: float = 0.0  # Percentage (e.g. 80.0)
    model_probability: float = 0.0       # Decimal probability (0.0 - 1.0)
    model_confidence: float = 1.0        # Confidence / uncertainty (0.0 - 1.0)
    expected_value: float = 0.0          # (model_prob * odds) - 1.0

    # Source & Provenance
    source_type: SourceType = SourceType.SPORTYBET
    source_name: str = "SportyBet Catalog"
    source_historical_accuracy: float = 0.75
    source_sample_size: int = 10
    ingested_at: datetime = field(default_factory=datetime.now)
    data_freshness_seconds: float = 0.0

    # Derived Scoring & State
    is_eligible: bool = True
    composite_score: float = 0.0
    flags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.decimal_odds > 0 and self.bookmaker_implied_prob == 0.0:
            self.bookmaker_implied_prob = round((1.0 / self.decimal_odds) * 100.0, 2)
        if self.model_probability == 0.0 and self.bookmaker_implied_prob > 0.0:
            self.model_probability = round(self.bookmaker_implied_prob / 100.0, 4)
        if self.expected_value == 0.0 and self.model_probability > 0.0 and self.decimal_odds > 0:
            self.expected_value = round((self.model_probability * self.decimal_odds) - 1.0, 4)

    @property
    def fixture_title(self) -> str:
        return f"{self.home_team} vs {self.away_team}"


@dataclass
class BetConstructionRequest:
    # User Configuration
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow: WorkflowType = WorkflowType.BET_BUILDER
    risk_profile: RiskProfile = RiskProfile.BALANCED
    target_combined_odds: Optional[float] = 3.00
    min_combined_odds: float = 1.50
    max_combined_odds: float = 10.00
    desired_game_count: int = 5
    min_game_count: int = 3
    max_game_count: int = 25
    target_date: str = "Today"
    target_sports: List[str] = field(default_factory=lambda: ["Football", "Basketball", "Tennis", "Ice Hockey"])
    min_selection_probability: float = 75.0  # Percentage
    preferred_markets: List[str] = field(default_factory=list)
    excluded_leagues: List[str] = field(default_factory=list)
    stake_amount: float = 1000.0
    candidates: List[BetCandidate] = field(default_factory=list)

    # System Safety Constraints
    max_match_correlation: int = 1
    max_league_exposure_pct: float = 0.40
    max_sport_exposure_pct: float = 0.70
    odds_freshness_ttl_sec: int = 300
    min_source_sample_size: int = 5
    require_positive_ev: bool = True
    allow_fallback_reduction: bool = True


@dataclass
class SelectedBetLeg:
    candidate_id: str
    fixture: str
    league: str
    sport: str
    kickoff_time: Optional[datetime]
    market_name: str
    outcome_name: str
    odds: float
    implied_probability_pct: float
    model_probability_pct: float
    expected_value_pct: float
    composite_score: float
    acceptance_reasons: List[str] = field(default_factory=list)
    specifier: Optional[str] = None
    event_id: str = ""
    market_id: str = ""
    outcome_id: str = ""


@dataclass
class RejectedCandidate:
    candidate_id: str
    fixture: str
    market_name: str
    odds: float
    rejection_category: RejectionCategory
    rejection_reason: str
    event_id: str = ""


@dataclass
class BetConstructionResult:
    # Execution Status
    request_id: str
    success: bool
    status_code: ConstructionStatusCode
    risk_profile_applied: RiskProfile

    # Constructed Accumulator Slip
    selected_candidates: List[SelectedBetLeg]
    total_combined_odds: float
    estimated_joint_probability: float  # Percentage
    estimated_slip_ev: float           # Percentage (e.g. +12.5%)
    recommended_stake: float
    sportybet_bonus_pct: float
    estimated_total_payout: float

    # Transparency & Audit Trail
    total_candidates_evaluated: int
    accepted_count: int
    rejected_candidates: List[RejectedCandidate]
    optimization_warnings: List[str] = field(default_factory=list)
    fallback_applied: bool = False
    explanation_summary: str = ""
    debug_metadata: Dict[str, Any] = field(default_factory=dict)
    booking_code: Optional[str] = None
    share_url: Optional[str] = None
