"""
Models Package: Pure Domain Contracts for the Telegram Betting Bot.
Phase 1: Zero framework/Telegram dependencies, strictly typed data structures.
"""

from models.bet_candidate import BetCandidate, SourceType
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
