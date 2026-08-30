"""
Unit Tests for Hard Constraint Filter Module
"""

import unittest
from datetime import datetime, timedelta
from engine.contracts import (
    BetCandidate,
    BetConstructionRequest,
    RejectionCategory,
    RiskProfile,
)
from engine.constraint_filter import HardConstraintFilter


class TestConstraintFilter(unittest.TestCase):
    def setUp(self):
        self.future_time = datetime.now() + timedelta(hours=4)
        self.valid_candidate = BetCandidate(
            candidate_id="cand_1",
            event_id="ev_1",
            sport="Football",
            league="Premier League",
            home_team="Liverpool",
            away_team="Bournemouth",
            kickoff_time=self.future_time,
            market_id="18",
            market_name="Double Chance",
            outcome_id="12",
            outcome_name="1X",
            decimal_odds=1.20,
            model_probability=0.85,
        )

    def test_valid_candidate_passes(self):
        req = BetConstructionRequest(risk_profile=RiskProfile.BALANCED, min_selection_probability=75.0)
        eligible, rejected = HardConstraintFilter.evaluate_candidates([self.valid_candidate], req)

        self.assertEqual(len(eligible), 1)
        self.assertEqual(len(rejected), 0)
        self.assertTrue(eligible[0].is_eligible)

    def test_past_match_rejection(self):
        past_cand = BetCandidate(
            candidate_id="cand_past",
            event_id="ev_past",
            sport="Football",
            league="La Liga",
            home_team="Real Madrid",
            away_team="Sevilla",
            kickoff_time=datetime.now() - timedelta(minutes=30),
            market_id="18",
            market_name="Double Chance",
            outcome_id="12",
            outcome_name="1X",
            decimal_odds=1.25,
        )

        req = BetConstructionRequest()
        eligible, rejected = HardConstraintFilter.evaluate_candidates([past_cand], req)

        self.assertEqual(len(eligible), 0)
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0].rejection_category, RejectionCategory.MATCH_ALREADY_STARTED)

    def test_odds_bounds_rejection(self):
        high_odds_cand = BetCandidate(
            candidate_id="cand_high",
            event_id="ev_2",
            sport="Football",
            league="Serie A",
            home_team="Monza",
            away_team="Milan",
            kickoff_time=self.future_time,
            market_id="1",
            market_name="1X2",
            outcome_id="1",
            outcome_name="Home Win",
            decimal_odds=3.50,
            model_probability=0.80,
        )

        req = BetConstructionRequest(risk_profile=RiskProfile.CONSERVATIVE)
        eligible, rejected = HardConstraintFilter.evaluate_candidates([high_odds_cand], req)

        self.assertEqual(len(eligible), 0)
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0].rejection_category, RejectionCategory.ODDS_TOO_HIGH)

    def test_low_probability_rejection(self):
        low_prob_cand = BetCandidate(
            candidate_id="cand_low",
            event_id="ev_3",
            sport="Football",
            league="Bundesliga",
            home_team="Bochum",
            away_team="Leipzig",
            kickoff_time=self.future_time,
            market_id="1",
            market_name="1X2",
            outcome_id="2",
            outcome_name="Away Win",
            decimal_odds=1.50,
            model_probability=0.60,
        )

        req = BetConstructionRequest(min_selection_probability=75.0)
        eligible, rejected = HardConstraintFilter.evaluate_candidates([low_prob_cand], req)

        self.assertEqual(len(eligible), 0)
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0].rejection_category, RejectionCategory.PROBABILITY_BELOW_THRESHOLD)

    def test_stale_data_rejection(self):
        stale_cand = BetCandidate(
            candidate_id="cand_stale",
            event_id="ev_4",
            sport="Basketball",
            league="NBA",
            home_team="Celtics",
            away_team="Lakers",
            kickoff_time=self.future_time,
            market_id="22",
            market_name="Handicap",
            outcome_id="1",
            outcome_name="+5.5",
            decimal_odds=1.25,
            model_probability=0.82,
            data_freshness_seconds=450.0,
        )

        req = BetConstructionRequest(odds_freshness_ttl_sec=300)
        eligible, rejected = HardConstraintFilter.evaluate_candidates([stale_cand], req)

        self.assertEqual(len(eligible), 0)
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0].rejection_category, RejectionCategory.STALE_DATA)


if __name__ == "__main__":
    unittest.main()
