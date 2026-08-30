"""
Unit Tests for Candidate Scoring Model Module
"""

import unittest
from engine.contracts import BetCandidate, BetConstructionRequest
from engine.scoring_model import CandidateScorer


class TestScoringModel(unittest.TestCase):
    def test_normalize_probability(self):
        # Prob 0.50 with min 0.50 -> 0.0
        self.assertEqual(CandidateScorer.normalize_probability(0.50, min_prob=0.50), 0.0)
        # Prob 1.00 -> 1.0
        self.assertEqual(CandidateScorer.normalize_probability(1.00, min_prob=0.50), 1.0)
        # Prob 0.75 -> 0.50
        self.assertAlmostEqual(CandidateScorer.normalize_probability(0.75, min_prob=0.50), 0.50, places=2)

    def test_normalize_expected_value_sigmoid(self):
        # EV = 0.0 -> exactly 0.50
        self.assertAlmostEqual(CandidateScorer.normalize_expected_value(0.0), 0.50, places=2)
        # EV = +0.10 -> > 0.75
        self.assertGreater(CandidateScorer.normalize_expected_value(0.10), 0.75)
        # EV = -0.10 -> < 0.25
        self.assertLess(CandidateScorer.normalize_expected_value(-0.10), 0.25)

    def test_normalize_source_reliability_shrinkage(self):
        # High accuracy with tiny sample size (N=2) vs large sample size (N=100)
        score_small_n = CandidateScorer.normalize_source_reliability(accuracy=0.90, sample_size=2)
        score_large_n = CandidateScorer.normalize_source_reliability(accuracy=0.80, sample_size=100)

        # Large sample size with 80% should outrank tiny sample size with 90%
        self.assertGreater(score_large_n, score_small_n)

    def test_score_candidate_composite(self):
        cand = BetCandidate(
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
            decimal_odds=1.20,
            model_probability=0.88,
            expected_value=0.056,
            source_historical_accuracy=0.82,
            source_sample_size=50,
            data_freshness_seconds=30.0,
        )

        score = CandidateScorer.score_candidate(cand)
        self.assertGreater(score, 0.60)
        self.assertLessEqual(score, 1.00)
        self.assertEqual(cand.composite_score, score)

    def test_rank_candidates(self):
        c_high = BetCandidate(
            candidate_id="c_high",
            event_id="e1",
            sport="Football",
            league="EPL",
            home_team="Team A",
            away_team="Team B",
            kickoff_time=None,
            market_id="18",
            market_name="Double Chance",
            outcome_id="12",
            outcome_name="1X",
            decimal_odds=1.22,
            model_probability=0.90,
            expected_value=0.098,
            source_sample_size=100,
        )
        c_low = BetCandidate(
            candidate_id="c_low",
            event_id="e2",
            sport="Football",
            league="EPL",
            home_team="Team C",
            away_team="Team D",
            kickoff_time=None,
            market_id="1",
            market_name="1X2",
            outcome_id="1",
            outcome_name="1",
            decimal_odds=1.80,
            model_probability=0.55,
            expected_value=-0.01,
            source_sample_size=5,
        )

        req = BetConstructionRequest()
        ranked = CandidateScorer.rank_candidates([c_low, c_high], req)
        self.assertEqual(ranked[0].candidate_id, "c_high")
        self.assertEqual(ranked[1].candidate_id, "c_low")


if __name__ == "__main__":
    unittest.main()
