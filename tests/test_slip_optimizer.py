"""
Unit Tests for Combinatorial Slip Optimizer Module
"""

import unittest
from engine.contracts import (
    BetCandidate,
    BetConstructionRequest,
    ConstructionStatusCode,
)
from engine.slip_optimizer import SlipOptimizer


class TestSlipOptimizer(unittest.TestCase):
    def setUp(self):
        self.candidates = [
            BetCandidate(
                candidate_id=f"c_{i}",
                event_id=f"ev_{i}",
                sport="Football",
                league=f"League {i % 3}",
                home_team=f"HomeTeam_{i}",
                away_team=f"AwayTeam_{i}",
                kickoff_time=None,
                market_id="18",
                market_name="Double Chance",
                outcome_id="12",
                outcome_name="1X",
                decimal_odds=1.25,
                composite_score=0.90 - (i * 0.05),
                model_probability=0.85,
            )
            for i in range(10)
        ]

    def test_optimize_slip_selects_desired_count(self):
        req = BetConstructionRequest(
            desired_game_count=5,
            min_game_count=3,
            target_combined_odds=3.00,
        )

        selected, status, warnings = SlipOptimizer.optimize_slip(self.candidates, req)

        self.assertEqual(len(selected), 5)
        self.assertIn(status, [ConstructionStatusCode.OPTIMAL, ConstructionStatusCode.SUB_OPTIMAL])
        # 1.25^5 = ~3.05
        total_odds = 1.0
        for leg in selected:
            total_odds *= leg.decimal_odds
        self.assertAlmostEqual(total_odds, 3.05, places=1)

    def test_shortfall_handling_minimum_viable_slip(self):
        # Pool with only 2 candidates when 5 requested and min is 3
        pool = self.candidates[:2]
        req = BetConstructionRequest(desired_game_count=5, min_game_count=3)

        selected, status, warnings = SlipOptimizer.optimize_slip(pool, req)

        self.assertEqual(status, ConstructionStatusCode.INSUFFICIENT_CANDIDATES)
        self.assertIn("minimum viable slip requires 3", warnings[0])

    def test_no_bad_bets_rule(self):
        # 4 high-quality candidates available
        pool = self.candidates[:4]
        req = BetConstructionRequest(desired_game_count=6, min_game_count=3)

        selected, status, warnings = SlipOptimizer.optimize_slip(pool, req)

        # Returns 4 rather than inventing 2 weak candidates
        self.assertEqual(len(selected), 4)
        self.assertTrue(any("Did not add lower-confidence matches" in w for w in warnings))

    def test_target_odds_never_forces_poor_quality_legs(self):
        """
        Regression Test (Priority 4):
        Requested target is 10.00x, but available safe candidates only produce ~4.50x.
        The optimizer must return the 4.50x safe subset with explanation rather than adding unsafe legs.
        """
        safe_candidates = [
            BetCandidate(
                candidate_id=f"safe_{i}",
                event_id=f"ev_safe_{i}",
                sport="Football",
                league=f"League {i}",
                home_team=f"Home_{i}",
                away_team=f"Away_{i}",
                kickoff_time=None,
                market_id="18",
                market_name="Double Chance",
                outcome_id="12",
                outcome_name="1X",
                decimal_odds=1.35,  # 1.35^5 = ~4.48x
                composite_score=0.85,
                consensus_probability=82.0,
            )
            for i in range(5)
        ]

        req = BetConstructionRequest(
            desired_game_count=5,
            min_game_count=3,
            target_combined_odds=10.00,  # High target
            min_combined_odds=1.50,
            max_combined_odds=20.00,
        )

        selected, status, warnings = SlipOptimizer.optimize_slip(safe_candidates, req)

        # Selected exactly the 5 safe legs
        self.assertEqual(len(selected), 5)
        total_odds = 1.0
        for leg in selected:
            total_odds *= leg.decimal_odds

        self.assertAlmostEqual(total_odds, 4.48, places=1)
        self.assertEqual(status, ConstructionStatusCode.SUB_OPTIMAL)
        self.assertTrue(any("differed from requested target" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()

