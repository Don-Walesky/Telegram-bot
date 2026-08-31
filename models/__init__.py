"""
Models Package: Pure Domain Contracts for the Telegram Betting Bot.
Phase 1/7B: Zero framework/Telegram dependencies, strictly typed data structures.
"""

from models.bet_candidate import BetCandidate, ProbabilitySource, SourceType
from models.engine_contracts import (
    BetConstructionRequest,
    BetConstructionResult,
    ConstructionStatusCode,
    RejectionCategory,
    RejectedCandidate,
    RiskProfile,
    SelectedBetLeg,
    WorkflowType,
)

__all__ = [
    "BetCandidate",
    "ProbabilitySource",
    "SourceType",
    "BetConstructionRequest",
    "BetConstructionResult",
    "ConstructionStatusCode",
    "RejectionCategory",
    "RejectedCandidate",
    "RiskProfile",
    "SelectedBetLeg",
    "WorkflowType",
]
