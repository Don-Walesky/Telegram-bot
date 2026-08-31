"""
Engine Contracts Module (Re-exported from authoritative models package).
Preserves backward compatibility while enforcing single source of truth in models/.
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
