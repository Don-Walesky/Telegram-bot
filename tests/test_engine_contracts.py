"""
Unit Tests for Engine Contracts Module
"""

import unittest
from datetime import datetime, timedelta
from engine.contracts import (
    WorkflowType,
    RiskProfile,
    SourceType,
    ConstructionStatusCode,
    RejectionCategory,
    BetCandidate,
    BetConstructionRequest,
    SelectedBetLeg,
    RejectedCandidate,
    BetConstructionResult,
)


class TestEngineContracts(unittest.TestCase):
    def test_bet_candidate_post_init_calculations(self):
        cand = BetCandidate(
            candidate_id="sr:match:1:18:12",
            event_id="sr:match:1",
            sport="Football",
            league="Premier League",
            home_team="Arsenal",
            away_team="Chelsea",
            kickoff_time=datetime.now() + timedelta(hours=3),
            market_id="18",
            market_name="Double Chance",
            outcome_id="12",
            outcome_name="1X",
            decimal_odds=1.25,
        )

        self.assertEqual(cand.bookmaker_implied_prob, 80.0)
        self.assertEqual(cand.model_probability, 0.80)
        self.assertAlmostEqual(cand.expected_value, 0.0, places=3)
        self.assertEqual(cand.fixture_title, "Arsenal vs Chelsea")

    def test_bet_construction_request_defaults(self):
        req = BetConstructionRequest()
        self.assertIsNotNone(req.request_id)
        self.assertEqual(req.workflow, WorkflowType.BET_BUILDER)
        self.assertEqual(req.risk_profile, RiskProfile.BALANCED)
        self.assertEqual(req.desired_game_count, 5)
        self.assertEqual(req.min_game_count, 3)
        self.assertTrue(req.require_positive_ev)

    def test_bet_construction_result_structure(self):
        res = BetConstructionResult(
            request_id="test-req-123",
            success=True,
            status_code=ConstructionStatusCode.OPTIMAL,
            risk_profile_applied=RiskProfile.BALANCED,
            selected_candidates=[],
            total_combined_odds=2.45,
            estimated_joint_probability=42.5,
            estimated_slip_ev=8.4,
            recommended_stake=1000.0,
            sportybet_bonus_pct=5.0,
            estimated_total_payout=2572.5,
            total_candidates_evaluated=10,
            accepted_count=0,
            rejected_candidates=[],
        )

        self.assertTrue(res.success)
        self.assertEqual(res.status_code, ConstructionStatusCode.OPTIMAL)
        self.assertEqual(res.total_combined_odds, 2.45)


if __name__ == "__main__":
    unittest.main()
