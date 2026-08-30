"""
Domain Models & Engine Contracts: BetConstructionRequest & BetConstructionResult
Defines the request parameters, result envelopes, selection items, rejection logs, and
status enums for the Risk / Bet Construction Engine.

Phase 1 Domain Contracts — Framework-independent, zero Telegram dependencies, no engine logic.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from models.bet_candidate import BetCandidate


class WorkflowType(str, Enum):
    """User workflow invoking the Bet Construction Engine."""
    BET_BUILDER = "BET_BUILDER"
    SCAN_CHANNELS = "SCAN_CHANNELS"
    STANDARD_SCAN = "STANDARD_SCAN"
    CODE_EDITOR = "CODE_EDITOR"
    CLI = "CLI"


class RiskProfile(str, Enum):
    """
    Risk Profile classification for betslip construction.
    Defines the user's risk tolerance setting (invariants implemented in future engine phase).
    """
    CONSERVATIVE = "CONSERVATIVE"
    BALANCED = "BALANCED"
    AGGRESSIVE = "AGGRESSIVE"
    VERY_AGGRESSIVE = "VERY_AGGRESSIVE"
    CUSTOM = "CUSTOM"


class ConstructionStatusCode(str, Enum):
    """Machine-readable execution status of betslip construction."""
    OPTIMAL = "OPTIMAL"
    SUB_OPTIMAL = "SUB_OPTIMAL"
    INSUFFICIENT_CANDIDATES = "INSUFFICIENT_CANDIDATES"
    NO_FIXTURES = "NO_FIXTURES"
    CATALOG_OFFLINE = "CATALOG_OFFLINE"
    TARGET_ODDS_UNMET = "TARGET_ODDS_UNMET"
    FAILED = "FAILED"


class RejectionCategory(str, Enum):
    """Machine-readable taxonomy of candidate selection rejection reasons."""
    MATCH_ALREADY_STARTED = "MATCH_ALREADY_STARTED"
    INVALID_ODDS = "INVALID_ODDS"
    ODDS_TOO_LOW = "ODDS_TOO_LOW"
    ODDS_TOO_HIGH = "ODDS_TOO_HIGH"
    PROBABILITY_BELOW_THRESHOLD = "PROBABILITY_BELOW_THRESHOLD"
    NEGATIVE_EV = "NEGATIVE_EV"
    STALE_DATA = "STALE_DATA"
    UNMAPPED_MARKET = "UNMAPPED_MARKET"
    INVALID_FIXTURE = "INVALID_FIXTURE"
    INVALID_MARKET = "INVALID_MARKET"
    MISSING_ODDS = "MISSING_ODDS"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    LOW_SIMILARITY_MATCH = "LOW_SIMILARITY_MATCH"
    CORRELATED_EVENT = "CORRELATED_EVENT"
    LEAGUE_EXPOSURE_EXCEEDED = "LEAGUE_EXPOSURE_EXCEEDED"
    SPORT_EXPOSURE_EXCEEDED = "SPORT_EXPOSURE_EXCEEDED"
    EXCLUDED_LEAGUE = "EXCLUDED_LEAGUE"
    UNSPECIFIED = "UNSPECIFIED"


@dataclass
class SelectedBetLeg:
    """
    Individual winning candidate leg chosen for inclusion in the final betslip.
    Derived from BetCandidate with accumulator metadata.
    """
    candidate_id: str
    fixture: str
    league: str
    sport: str
    kickoff_time: Optional[datetime]
    market_name: str
    outcome_name: str
    odds: float
    implied_probability_pct: float
    model_probability_pct: Optional[float] = None
    expected_value_pct: Optional[float] = None
    composite_score: Optional[float] = None
    acceptance_reasons: List[str] = field(default_factory=list)
    specifier: Optional[str] = None
    event_id: str = ""
    market_id: str = ""
    outcome_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serializes selected leg to dictionary representation."""
        return {
            "candidate_id": self.candidate_id,
            "fixture": self.fixture,
            "league": self.league,
            "sport": self.sport,
            "kickoff_time": self.kickoff_time.isoformat() if self.kickoff_time else None,
            "market_name": self.market_name,
            "outcome_name": self.outcome_name,
            "odds": self.odds,
            "implied_probability_pct": self.implied_probability_pct,
            "model_probability_pct": self.model_probability_pct,
            "expected_value_pct": self.expected_value_pct,
            "composite_score": self.composite_score,
            "acceptance_reasons": self.acceptance_reasons,
            "specifier": self.specifier,
            "event_id": self.event_id,
            "market_id": self.market_id,
            "outcome_id": self.outcome_id,
        }


@dataclass
class RejectedCandidate:
    """
    Audit record for a candidate that was evaluated and rejected by the engine.
    Provides complete transparency for why a selection was excluded.
    """
    candidate_id: str
    fixture: str
    market_name: str
    odds: float
    rejection_category: RejectionCategory
    rejection_reason: str
    event_id: str = ""
    diagnostic_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes rejected candidate log to dictionary."""
        return {
            "candidate_id": self.candidate_id,
            "fixture": self.fixture,
            "market_name": self.market_name,
            "odds": self.odds,
            "rejection_category": self.rejection_category.value,
            "rejection_reason": self.rejection_reason,
            "event_id": self.event_id,
            "diagnostic_metadata": self.diagnostic_metadata,
        }


@dataclass
class BetConstructionRequest:
    """
    Input contract for the Risk / Bet Construction Engine.
    Strictly separates user configuration preferences from system safety invariants.
    """

    # --- User Configuration Preferences ---
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
    min_selection_probability: float = 75.0
    preferred_markets: List[str] = field(default_factory=list)
    excluded_leagues: List[str] = field(default_factory=list)
    stake_amount: float = 1000.0
    candidates: List[BetCandidate] = field(default_factory=list)

    # --- System Safety Configuration ---
    max_match_correlation: int = 1
    max_league_exposure_pct: float = 0.40
    max_sport_exposure_pct: float = 0.70
    odds_freshness_ttl_sec: int = 300
    min_source_sample_size: int = 5
    require_positive_ev: bool = True
    allow_fallback_reduction: bool = True

    def __post_init__(self) -> None:
        """Lightweight structural invariant validation."""
        if self.min_game_count <= 0:
            raise ValueError(f"min_game_count must be > 0, got {self.min_game_count}.")

        if self.max_game_count < self.min_game_count:
            raise ValueError(
                f"max_game_count ({self.max_game_count}) cannot be less than min_game_count ({self.min_game_count})."
            )

        if not (self.min_game_count <= self.desired_game_count <= self.max_game_count):
            raise ValueError(
                f"desired_game_count ({self.desired_game_count}) must be between "
                f"min_game_count ({self.min_game_count}) and max_game_count ({self.max_game_count})."
            )

        if self.min_combined_odds <= 1.0:
            raise ValueError(f"min_combined_odds must be strictly > 1.0, got {self.min_combined_odds}.")

        if self.max_combined_odds < self.min_combined_odds:
            raise ValueError(
                f"max_combined_odds ({self.max_combined_odds}) cannot be less than "
                f"min_combined_odds ({self.min_combined_odds})."
            )

        if not (0.0 <= self.min_selection_probability <= 100.0):
            raise ValueError(
                f"min_selection_probability must be between 0.0 and 100.0, got {self.min_selection_probability}."
            )

        if self.stake_amount <= 0.0:
            raise ValueError(f"stake_amount must be positive (> 0), got {self.stake_amount}.")

    def to_dict(self) -> Dict[str, Any]:
        """Serializes request to dictionary representation."""
        return {
            "request_id": self.request_id,
            "workflow": self.workflow.value,
            "risk_profile": self.risk_profile.value,
            "target_combined_odds": self.target_combined_odds,
            "min_combined_odds": self.min_combined_odds,
            "max_combined_odds": self.max_combined_odds,
            "desired_game_count": self.desired_game_count,
            "min_game_count": self.min_game_count,
            "max_game_count": self.max_game_count,
            "target_date": self.target_date,
            "target_sports": self.target_sports,
            "min_selection_probability": self.min_selection_probability,
            "preferred_markets": self.preferred_markets,
            "excluded_leagues": self.excluded_leagues,
            "stake_amount": self.stake_amount,
            "candidates_count": len(self.candidates),
            "max_match_correlation": self.max_match_correlation,
            "max_league_exposure_pct": self.max_league_exposure_pct,
            "max_sport_exposure_pct": self.max_sport_exposure_pct,
            "odds_freshness_ttl_sec": self.odds_freshness_ttl_sec,
            "min_source_sample_size": self.min_source_sample_size,
            "require_positive_ev": self.require_positive_ev,
            "allow_fallback_reduction": self.allow_fallback_reduction,
        }


@dataclass
class BetConstructionResult:
    """
    Output envelope returned by the Bet Construction Engine.
    Contains the assembled accumulator betslip, payout metrics, and complete audit trail.
    """

    # --- Execution Status ---
    request_id: str
    success: bool
    status_code: ConstructionStatusCode
    risk_profile_applied: RiskProfile

    # --- Slip Result Metrics ---
    selected_candidates: List[SelectedBetLeg]
    total_combined_odds: float
    estimated_joint_probability: float
    estimated_slip_ev: Optional[float] = None
    recommended_stake: float = 0.0
    sportybet_bonus_pct: float = 0.0
    estimated_total_payout: float = 0.0

    # --- Transparency & Audit Trail ---
    total_candidates_evaluated: int = 0
    accepted_count: int = 0
    rejected_candidates: List[RejectedCandidate] = field(default_factory=list)
    optimization_warnings: List[str] = field(default_factory=list)
    fallback_applied: bool = False
    explanation_summary: str = ""
    debug_metadata: Dict[str, Any] = field(default_factory=dict)
    booking_code: Optional[str] = None
    share_url: Optional[str] = None

    @property
    def leg_count(self) -> int:
        """Number of selected bet legs in the constructed slip."""
        return len(self.selected_candidates)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes result to dictionary representation."""
        return {
            "request_id": self.request_id,
            "success": self.success,
            "status_code": self.status_code.value,
            "risk_profile_applied": self.risk_profile_applied.value,
            "selected_candidates": [leg.to_dict() for leg in self.selected_candidates],
            "total_combined_odds": self.total_combined_odds,
            "estimated_joint_probability": self.estimated_joint_probability,
            "estimated_slip_ev": self.estimated_slip_ev,
            "recommended_stake": self.recommended_stake,
            "sportybet_bonus_pct": self.sportybet_bonus_pct,
            "estimated_total_payout": self.estimated_total_payout,
            "total_candidates_evaluated": self.total_candidates_evaluated,
            "accepted_count": self.accepted_count,
            "rejected_candidates": [rej.to_dict() for rej in self.rejected_candidates],
            "optimization_warnings": self.optimization_warnings,
            "fallback_applied": self.fallback_applied,
            "explanation_summary": self.explanation_summary,
            "debug_metadata": self.debug_metadata,
            "booking_code": self.booking_code,
            "share_url": self.share_url,
            "leg_count": self.leg_count,
        }
