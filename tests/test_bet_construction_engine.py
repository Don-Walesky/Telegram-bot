"""
Unit Tests for Unified BetConstructionEngine Module
"""

import unittest
from datetime import datetime, timedelta
from engine.contracts import (
    BetCandidate,
    BetConstructionRequest,
    ConstructionStatusCode,
    RiskProfile,
    WorkflowType,
)
from engine.bet_construction_engine import BetConstructionEngine


class TestBetConstructionEngine(unittest.TestCase):
    def setUp(self):
        self.future_time = datetime.now() + timedelta(hours=3)
        self.candidates = [
            BetCandidate(
                candidate_id=f"cand_{i}",
                event_id=f"ev_{i}",
                sport="Football",
                league=f"League {i % 4}",
                home_team=f"Home_{i}",
                away_team=f"Away_{i}",
                kickoff_time=self.future_time,
                market_id="18",
                market_name="Double Chance",
                outcome_id="12",
                outcome_name="1X",
                decimal_odds=1.20,
                model_probability=0.85,
            )
            for i in range(12)
        ]

    def test_build_bet_slip_success(self):
        req = BetConstructionRequest(
            workflow=WorkflowType.BET_BUILDER,
            risk_profile=RiskProfile.BALANCED,
            desired_game_count=5,
            min_game_count=3,
            target_combined_odds=2.50,
            candidates=self.candidates,
        )

        result = BetConstructionEngine.build_bet_slip(req)

        self.assertTrue(result.success)
        self.assertEqual(len(result.selected_candidates), 5)
        self.assertGreater(result.total_combined_odds, 2.00)
        self.assertGreater(result.estimated_joint_probability, 30.0)
        self.assertIn("OPTIMIZED BETSLIP & RISK SUMMARY", result.explanation_summary)

    def test_empty_candidates_handling(self):
        req = BetConstructionRequest(candidates=[])
        result = BetConstructionEngine.build_bet_slip(req)

        self.assertFalse(result.success)
        self.assertEqual(result.status_code, ConstructionStatusCode.NO_FIXTURES)
        self.assertEqual(len(result.selected_candidates), 0)

    def test_insufficient_candidates_handling(self):
        req = BetConstructionRequest(
            desired_game_count=5,
            min_game_count=3,
            candidates=self.candidates[:2],  # only 2 candidates
        )

        result = BetConstructionEngine.build_bet_slip(req)

        self.assertFalse(result.success)
        self.assertEqual(result.status_code, ConstructionStatusCode.INSUFFICIENT_CANDIDATES)


if __name__ == "__main__":
    unittest.main()
