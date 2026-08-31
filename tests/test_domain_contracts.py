"""
Unit Tests for Phase 1 Domain Contracts (models/bet_candidate.py, models/engine_contracts.py).
Verifies structural validation, invariant enforcement, serialization, and enum integrity.
"""

from datetime import datetime
import unittest

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


class TestBetCandidateContract(unittest.TestCase):
    """Test suite for BetCandidate domain model."""

    def test_valid_bet_candidate_minimal(self) -> None:
        """Test minimal valid BetCandidate instantiation."""
        candidate = BetCandidate(
            candidate_id="cand-001",
            event_id="sr:match:101",
            sport="Football",
            league="Premier League",
            home_team="Arsenal",
            away_team="Chelsea",
            kickoff_time=datetime(2026, 9, 1, 15, 0),
            market_id="1",
            market_name="1X2",
            outcome_id="1",
            outcome_name="Home",
            decimal_odds=1.25,
        )
        self.assertEqual(candidate.candidate_id, "cand-001")
        self.assertEqual(candidate.decimal_odds, 1.25)
        # Auto-calculated implied prob = (1.0 / 1.25) * 100 = 80.0
        self.assertEqual(candidate.bookmaker_implied_prob, 80.0)
        self.assertIsNone(candidate.model_probability)
        self.assertIsNone(candidate.model_confidence)
        self.assertIsNone(candidate.expected_value)
        self.assertEqual(candidate.fixture_title, "Arsenal vs Chelsea")
        self.assertTrue(candidate.is_eligible)

    def test_valid_bet_candidate_full(self) -> None:
        """Test BetCandidate with explicit optional/future fields."""
        candidate = BetCandidate(
            candidate_id="cand-002",
            event_id="sr:match:102",
            sport="Basketball",
            league="NBA",
            home_team="Lakers",
            away_team="Warriors",
            kickoff_time=None,
            market_id="200",
            market_name="Over/Under",
            outcome_id="over_220",
            outcome_name="Over 220.5",
            decimal_odds=1.85,
            specifier="total=220.5",
            bookmaker_implied_prob=54.05,
            model_probability=0.62,
            model_confidence=0.90,
            expected_value=0.147,
            source_type=SourceType.TIPSTER,
            source_name="VIP Banker Channel",
            source_historical_accuracy=0.78,
            source_sample_size=120,
            data_freshness_seconds=45.0,
            is_eligible=True,
            composite_score=0.88,
            flags=["HIGH_VALUE"],
        )
        self.assertEqual(candidate.source_type, SourceType.TIPSTER)
        self.assertEqual(candidate.model_probability, 0.62)
        self.assertEqual(candidate.expected_value, 0.147)
        self.assertEqual(candidate.flags, ["HIGH_VALUE"])

    def test_effective_probability_hierarchy(self) -> None:
        """Test effective_probability prioritizes model > consensus > implied."""
        # 1. Implied only (odds 1.25 -> 80.0%)
        cand_implied = BetCandidate(
            candidate_id="c1",
            event_id="e1",
            sport="Football",
            league="EPL",
            home_team="A",
            away_team="B",
            kickoff_time=None,
            market_id="1",
            market_name="1X2",
            outcome_id="1",
            outcome_name="Home",
            decimal_odds=1.25,
        )
        self.assertEqual(cand_implied.effective_probability, 80.0)

        # 2. Consensus heuristic present (88.0%)
        cand_consensus = BetCandidate(
            candidate_id="c2",
            event_id="e2",
            sport="Football",
            league="EPL",
            home_team="A",
            away_team="B",
            kickoff_time=None,
            market_id="1",
            market_name="1X2",
            outcome_id="1",
            outcome_name="Home",
            decimal_odds=1.25,
            consensus_probability=88.0,
            probability_source=ProbabilitySource.CONSENSUS_HEURISTIC,
        )
        self.assertEqual(cand_consensus.effective_probability, 88.0)

        # 3. Model probability present (0.91 -> 91.0%)
        cand_model = BetCandidate(
            candidate_id="c3",
            event_id="e3",
            sport="Football",
            league="EPL",
            home_team="A",
            away_team="B",
            kickoff_time=None,
            market_id="1",
            market_name="1X2",
            outcome_id="1",
            outcome_name="Home",
            decimal_odds=1.25,
            consensus_probability=88.0,
            model_probability=0.91,
            probability_source=ProbabilitySource.PREDICTIVE_MODEL,
        )
        self.assertEqual(cand_model.effective_probability, 91.0)

    def test_missing_model_probability_remains_none(self) -> None:
        """
        Priority 1 Test:
        When only decimal odds or consensus probabilities are provided,
        model_probability must remain None (never fabricated as 1/odds).
        """
        cand = BetCandidate(
            candidate_id="c_none",
            event_id="e_none",
            sport="Football",
            league="EPL",
            home_team="A",
            away_team="B",
            kickoff_time=None,
            market_id="1",
            market_name="1X2",
            outcome_id="1",
            outcome_name="Home",
            decimal_odds=1.25,
        )
        self.assertIsNone(cand.model_probability)
        self.assertEqual(cand.bookmaker_implied_prob, 80.0)
        self.assertEqual(cand.probability_source, ProbabilitySource.BOOKMAKER_IMPLIED)

    def test_heuristic_probability_explicitly_identified(self) -> None:
        """
        Priority 1 Test:
        Consensus heuristic probability is explicitly tracked under CONSENSUS_HEURISTIC source.
        """
        cand = BetCandidate(
            candidate_id="c_heur",
            event_id="e_heur",
            sport="Football",
            league="EPL",
            home_team="A",
            away_team="B",
            kickoff_time=None,
            market_id="18",
            market_name="Double Chance",
            outcome_id="12",
            outcome_name="1X",
            decimal_odds=1.20,
            consensus_probability=85.0,
            probability_source=ProbabilitySource.CONSENSUS_HEURISTIC,
        )
        self.assertIsNone(cand.model_probability)
        self.assertEqual(cand.consensus_probability, 85.0)
        self.assertEqual(cand.probability_source, ProbabilitySource.CONSENSUS_HEURISTIC)
        self.assertEqual(cand.effective_probability, 85.0)

    def test_invalid_odds_raises_value_error(self) -> None:
        """Test non-positive decimal odds raises ValueError."""
        with self.assertRaises(ValueError):
            BetCandidate(
                candidate_id="cand-err",
                event_id="sr:match:0",
                sport="Football",
                league="EPL",
                home_team="A",
                away_team="B",
                kickoff_time=None,
                market_id="1",
                market_name="1X2",
                outcome_id="1",
                outcome_name="Home",
                decimal_odds=0.0,
            )

        with self.assertRaises(ValueError):
            BetCandidate(
                candidate_id="cand-err2",
                event_id="sr:match:0",
                sport="Football",
                league="EPL",
                home_team="A",
                away_team="B",
                kickoff_time=None,
                market_id="1",
                market_name="1X2",
                outcome_id="1",
                outcome_name="Home",
                decimal_odds=-1.50,
            )

    def test_invalid_probability_raises_value_error(self) -> None:
        """Test out-of-bounds probabilities raise ValueError."""
        with self.assertRaises(ValueError):
            BetCandidate(
                candidate_id="cand-err3",
                event_id="sr:match:0",
                sport="Football",
                league="EPL",
                home_team="A",
                away_team="B",
                kickoff_time=None,
                market_id="1",
                market_name="1X2",
                outcome_id="1",
                outcome_name="Home",
                decimal_odds=1.50,
                bookmaker_implied_prob=150.0,
            )

        with self.assertRaises(ValueError):
            BetCandidate(
                candidate_id="cand-err4",
                event_id="sr:match:0",
                sport="Football",
                league="EPL",
                home_team="A",
                away_team="B",
                kickoff_time=None,
                market_id="1",
                market_name="1X2",
                outcome_id="1",
                outcome_name="Home",
                decimal_odds=1.50,
                model_probability=1.20,
            )

    def test_to_dict_serialization(self) -> None:
        """Test candidate serialization to dictionary."""
        candidate = BetCandidate(
            candidate_id="cand-dict",
            event_id="sr:match:999",
            sport="Tennis",
            league="ATP",
            home_team="Alcaraz",
            away_team="Sinner",
            kickoff_time=datetime(2026, 9, 2, 14, 0),
            market_id="10",
            market_name="Match Winner",
            outcome_id="1",
            outcome_name="Alcaraz",
            decimal_odds=1.40,
        )
        d = candidate.to_dict()
        self.assertEqual(d["candidate_id"], "cand-dict")
        self.assertEqual(d["decimal_odds"], 1.40)
        self.assertEqual(d["source_type"], "SPORTYBET")
        self.assertIn("2026-09-02", d["kickoff_time"])


class TestBetConstructionRequestContract(unittest.TestCase):
    """Test suite for BetConstructionRequest domain model."""

    def test_valid_default_request(self) -> None:
        """Test default request construction."""
        req = BetConstructionRequest()
        self.assertEqual(req.workflow, WorkflowType.BET_BUILDER)
        self.assertEqual(req.risk_profile, RiskProfile.BALANCED)
        self.assertEqual(req.desired_game_count, 5)
        self.assertEqual(req.min_game_count, 3)
        self.assertEqual(req.max_game_count, 25)
        self.assertEqual(req.stake_amount, 1000.0)

    def test_invalid_game_counts(self) -> None:
        """Test game count bounds validation."""
        # min_game_count <= 0
        with self.assertRaises(ValueError):
            BetConstructionRequest(min_game_count=0)

        # max_game_count < min_game_count
        with self.assertRaises(ValueError):
            BetConstructionRequest(min_game_count=5, max_game_count=3)

        # desired_game_count outside [min, max]
        with self.assertRaises(ValueError):
            BetConstructionRequest(min_game_count=3, max_game_count=7, desired_game_count=10)

    def test_invalid_odds_bounds(self) -> None:
        """Test odds bounds validation."""
        with self.assertRaises(ValueError):
            BetConstructionRequest(min_combined_odds=0.5)

        with self.assertRaises(ValueError):
            BetConstructionRequest(min_combined_odds=5.0, max_combined_odds=3.0)

    def test_invalid_stake_amount(self) -> None:
        """Test non-positive stake amount."""
        with self.assertRaises(ValueError):
            BetConstructionRequest(stake_amount=0.0)

    def test_request_to_dict(self) -> None:
        """Test request serialization."""
        req = BetConstructionRequest(
            workflow=WorkflowType.SCAN_CHANNELS,
            risk_profile=RiskProfile.CONSERVATIVE,
            desired_game_count=4,
            min_game_count=3,
            max_game_count=10,
            stake_amount=2500.0,
        )
        d = req.to_dict()
        self.assertEqual(d["workflow"], "SCAN_CHANNELS")
        self.assertEqual(d["risk_profile"], "CONSERVATIVE")
        self.assertEqual(d["desired_game_count"], 4)
        self.assertEqual(d["stake_amount"], 2500.0)


class TestBetConstructionResultContract(unittest.TestCase):
    """Test suite for BetConstructionResult domain model."""

    def test_successful_result(self) -> None:
        """Test successful BetConstructionResult construction."""
        leg = SelectedBetLeg(
            candidate_id="cand-1",
            fixture="Arsenal vs Chelsea",
            league="EPL",
            sport="Football",
            kickoff_time=datetime(2026, 9, 1, 15, 0),
            market_name="1X2",
            outcome_name="Home",
            odds=1.35,
            implied_probability_pct=74.07,
            acceptance_reasons=["HIGH_PROBABILITY"],
        )
        result = BetConstructionResult(
            request_id="req-123",
            success=True,
            status_code=ConstructionStatusCode.OPTIMAL,
            risk_profile_applied=RiskProfile.BALANCED,
            selected_candidates=[leg],
            total_combined_odds=1.35,
            estimated_joint_probability=74.07,
            recommended_stake=500.0,
            sportybet_bonus_pct=0.0,
            estimated_total_payout=675.0,
            total_candidates_evaluated=10,
            accepted_count=1,
            booking_code="BC-TEST-99",
        )
        self.assertTrue(result.success)
        self.assertEqual(result.leg_count, 1)
        self.assertEqual(result.booking_code, "BC-TEST-99")
        d = result.to_dict()
        self.assertEqual(d["status_code"], "OPTIMAL")
        self.assertEqual(len(d["selected_candidates"]), 1)

    def test_failed_result_with_rejections(self) -> None:
        """Test failed BetConstructionResult with rejected candidates."""
        rejected = RejectedCandidate(
            candidate_id="cand-bad",
            fixture="Real Madrid vs Barcelona",
            market_name="1X2",
            odds=1.02,
            rejection_category=RejectionCategory.ODDS_TOO_LOW,
            rejection_reason="Odds 1.02 below profile minimum 1.05",
        )
        result = BetConstructionResult(
            request_id="req-fail",
            success=False,
            status_code=ConstructionStatusCode.INSUFFICIENT_CANDIDATES,
            risk_profile_applied=RiskProfile.CONSERVATIVE,
            selected_candidates=[],
            total_combined_odds=1.0,
            estimated_joint_probability=0.0,
            rejected_candidates=[rejected],
            total_candidates_evaluated=1,
            accepted_count=0,
            explanation_summary="Could not find sufficient candidates meeting risk profile.",
        )
        self.assertFalse(result.success)
        self.assertEqual(result.leg_count, 0)
        self.assertEqual(len(result.rejected_candidates), 1)
        self.assertEqual(result.rejected_candidates[0].rejection_category, RejectionCategory.ODDS_TOO_LOW)


class TestEnumsIntegrity(unittest.TestCase):
    """Test suite for domain enums completeness."""

    def test_source_type_values(self) -> None:
        """Verify SourceType enum values."""
        self.assertEqual(SourceType.LIVESCORE.value, "LIVESCORE")
        self.assertEqual(SourceType.SPORTYBET.value, "SPORTYBET")
        self.assertEqual(SourceType.TIPSTER.value, "TIPSTER")
        self.assertEqual(SourceType.CONSENSUS.value, "CONSENSUS")
        self.assertEqual(SourceType.EXTERNAL_CODE.value, "EXTERNAL_CODE")

    def test_probability_source_values(self) -> None:
        """Verify ProbabilitySource enum values."""
        self.assertEqual(ProbabilitySource.BOOKMAKER_IMPLIED.value, "BOOKMAKER_IMPLIED")
        self.assertEqual(ProbabilitySource.CONSENSUS_HEURISTIC.value, "CONSENSUS_HEURISTIC")
        self.assertEqual(ProbabilitySource.PREDICTIVE_MODEL.value, "PREDICTIVE_MODEL")
        self.assertEqual(ProbabilitySource.UNKNOWN.value, "UNKNOWN")

    def test_risk_profile_values(self) -> None:
        """Verify RiskProfile enum values."""
        self.assertEqual(RiskProfile.CONSERVATIVE.value, "CONSERVATIVE")
        self.assertEqual(RiskProfile.BALANCED.value, "BALANCED")
        self.assertEqual(RiskProfile.AGGRESSIVE.value, "AGGRESSIVE")
        self.assertEqual(RiskProfile.VERY_AGGRESSIVE.value, "VERY_AGGRESSIVE")
        self.assertEqual(RiskProfile.CUSTOM.value, "CUSTOM")

    def test_workflow_type_values(self) -> None:
        """Verify WorkflowType enum values."""
        self.assertEqual(WorkflowType.BET_BUILDER.value, "BET_BUILDER")
        self.assertEqual(WorkflowType.SCAN_CHANNELS.value, "SCAN_CHANNELS")

    def test_construction_status_code_values(self) -> None:
        """Verify ConstructionStatusCode enum values."""
        self.assertEqual(ConstructionStatusCode.OPTIMAL.value, "OPTIMAL")
        self.assertEqual(ConstructionStatusCode.SUB_OPTIMAL.value, "SUB_OPTIMAL")
        self.assertEqual(ConstructionStatusCode.FAILED.value, "FAILED")

    def test_rejection_category_values(self) -> None:
        """Verify RejectionCategory enum values."""
        self.assertEqual(RejectionCategory.ODDS_TOO_LOW.value, "ODDS_TOO_LOW")
        self.assertEqual(RejectionCategory.ODDS_TOO_HIGH.value, "ODDS_TOO_HIGH")
        self.assertEqual(RejectionCategory.PROBABILITY_BELOW_THRESHOLD.value, "PROBABILITY_BELOW_THRESHOLD")
        self.assertEqual(RejectionCategory.CORRELATED_EVENT.value, "CORRELATED_EVENT")


if __name__ == "__main__":
    unittest.main()
