"""
Unit Tests for Risk Profiles & Invariants Manager Module
"""

import unittest
from engine.contracts import BetCandidate, RiskProfile
from engine.risk_profiles import RiskProfileManager


class TestRiskProfiles(unittest.TestCase):
    def test_conservative_profile_validation(self):
        valid_cand = BetCandidate(
            candidate_id="c1",
            event_id="e1",
            sport="Football",
            league="EPL",
            home_team="Arsenal",
            away_team="Chelsea",
            kickoff_time=None,
            market_id="18",
            market_name="Double Chance",
            outcome_id="12",
            outcome_name="1X",
            decimal_odds=1.18,
            model_probability=0.88,
            expected_value=0.0384,
        )

        is_valid, reason = RiskProfileManager.validate_candidate(valid_cand, RiskProfile.CONSERVATIVE)
        self.assertTrue(is_valid)
        self.assertEqual(reason, "")

    def test_conservative_profile_rejects_low_probability(self):
        low_p_cand = BetCandidate(
            candidate_id="c2",
            event_id="e2",
            sport="Football",
            league="EPL",
            home_team="Team A",
            away_team="Team B",
            kickoff_time=None,
            market_id="18",
            market_name="Double Chance",
            outcome_id="12",
            outcome_name="1X",
            decimal_odds=1.20,
            model_probability=0.80,  # Below 85% conservative threshold
            expected_value=-0.04,
        )

        is_valid, reason = RiskProfileManager.validate_candidate(low_p_cand, RiskProfile.CONSERVATIVE)
        self.assertFalse(is_valid)
        self.assertIn("below CONSERVATIVE minimum", reason)

    def test_fractional_kelly_stake_calculation(self):
        # 50% probability @ 2.40 odds on 10,000 bankroll
        # Full Kelly = (1.4 * 0.5 - 0.5) / 1.4 = 0.2 / 1.4 = 0.1428 (14.28%)
        # Balanced Profile uses Quarter Kelly (0.25) -> ~3.57% of 10,000 = ~357.14
        stake = RiskProfileManager.calculate_kelly_stake(
            estimated_joint_probability=50.0,
            total_odds=2.40,
            bankroll=10000.0,
            profile=RiskProfile.BALANCED,
        )
        self.assertGreater(stake, 200.0)
        self.assertLess(stake, 600.0)

    def test_negative_edge_kelly_stake_minimum(self):
        # 30% probability @ 2.00 odds -> Negative EV
        stake = RiskProfileManager.calculate_kelly_stake(
            estimated_joint_probability=30.0,
            total_odds=2.00,
            bankroll=10000.0,
            profile=RiskProfile.BALANCED,
        )
        # Returns token minimum (100.0)
        self.assertEqual(stake, 100.0)


if __name__ == "__main__":
    unittest.main()
