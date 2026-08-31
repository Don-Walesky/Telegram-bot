"""
Unit Tests for Expected Value & De-vigging Calculator Module
Verifies EV mathematics, de-vigging, and probability provenance enrichment.
"""

import unittest
from models.bet_candidate import BetCandidate, ProbabilitySource
from engine.ev_calculator import EVCalculator


class TestEVCalculator(unittest.TestCase):
    def test_expected_value_positive(self):
        # 60% probability @ 2.00 odds -> (0.60 * 2.0) - 1.0 = +0.20 (+20%)
        ev = EVCalculator.calculate_expected_value(model_probability=0.60, decimal_odds=2.00)
        self.assertAlmostEqual(ev, 0.20, places=4)

    def test_expected_value_negative(self):
        # 80% probability @ 1.10 odds -> (0.80 * 1.10) - 1.0 = -0.12 (-12%)
        ev = EVCalculator.calculate_expected_value(model_probability=0.80, decimal_odds=1.10)
        self.assertAlmostEqual(ev, -0.12, places=4)

    def test_calculate_implied_probability(self):
        # Odds 1.25 -> 80% implied
        prob = EVCalculator.calculate_implied_probability(1.25)
        self.assertAlmostEqual(prob, 80.0, places=2)

        # Odds 2.00 -> 50% implied
        prob_2 = EVCalculator.calculate_implied_probability(2.00)
        self.assertAlmostEqual(prob_2, 50.0, places=2)

    def test_calculate_overround(self):
        # 1X2 market: 2.00, 3.20, 3.80 -> 0.50 + 0.3125 + 0.26315 = 1.07565 -> Overround ~7.57%
        odds = [2.00, 3.20, 3.80]
        overround = EVCalculator.calculate_overround(odds)
        self.assertAlmostEqual(overround, 0.07565, places=3)

    def test_devig_odds_proportional(self):
        # Two-way market: 1.90, 1.90 -> Fair is 50% (0.50), 50% (0.50)
        odds = [1.90, 1.90]
        fair_probs = EVCalculator.devig_odds_proportional(odds)
        self.assertEqual(len(fair_probs), 2)
        self.assertAlmostEqual(fair_probs[0], 0.50, places=4)
        self.assertAlmostEqual(fair_probs[1], 0.50, places=4)
        self.assertAlmostEqual(sum(fair_probs), 1.00, places=4)

    def test_enrich_candidate_model_probability(self):
        """Candidate with genuine model probability gets model EV and PREDICTIVE_MODEL source."""
        cand = BetCandidate(
            candidate_id="cand_test_model",
            event_id="ev_test_1",
            sport="Football",
            league="EPL",
            home_team="Team A",
            away_team="Team B",
            kickoff_time=None,
            market_id="18",
            market_name="Double Chance",
            outcome_id="12",
            outcome_name="1X",
            decimal_odds=1.25,
            model_probability=0.85,
        )

        enriched = EVCalculator.enrich_candidate(cand)
        self.assertEqual(enriched.bookmaker_implied_prob, 80.0)
        # EV = (0.85 * 1.25) - 1.0 = 1.0625 - 1.0 = +0.0625
        self.assertAlmostEqual(enriched.expected_value, 0.0625, places=4)
        self.assertFalse(enriched.expected_value_is_heuristic)
        self.assertEqual(enriched.probability_source, ProbabilitySource.PREDICTIVE_MODEL)

    def test_enrich_candidate_consensus_probability(self):
        """Candidate with consensus heuristic gets heuristic EV and CONSENSUS_HEURISTIC source."""
        cand = BetCandidate(
            candidate_id="cand_test_consensus",
            event_id="ev_test_2",
            sport="Football",
            league="La Liga",
            home_team="Team C",
            away_team="Team D",
            kickoff_time=None,
            market_id="10",
            market_name="Over 1.5 Goals",
            outcome_id="1",
            outcome_name="Over",
            decimal_odds=1.20,
            consensus_probability=88.0,
        )

        enriched = EVCalculator.enrich_candidate(cand)
        self.assertEqual(enriched.bookmaker_implied_prob, 83.33)
        # EV = (0.88 * 1.20) - 1.0 = 1.056 - 1.0 = +0.056
        self.assertAlmostEqual(enriched.expected_value, 0.0560, places=4)
        self.assertTrue(enriched.expected_value_is_heuristic)
        self.assertEqual(enriched.probability_source, ProbabilitySource.CONSENSUS_HEURISTIC)
        self.assertIsNone(enriched.model_probability)

    def test_enrich_candidate_implied_only(self):
        """Candidate with only odds gets 0.0 EV and BOOKMAKER_IMPLIED source without fabricating model_prob."""
        cand = BetCandidate(
            candidate_id="cand_test_implied",
            event_id="ev_test_3",
            sport="Football",
            league="Serie A",
            home_team="Team E",
            away_team="Team F",
            kickoff_time=None,
            market_id="1",
            market_name="1X2",
            outcome_id="1",
            outcome_name="Home",
            decimal_odds=1.50,
        )

        enriched = EVCalculator.enrich_candidate(cand)
        self.assertEqual(enriched.bookmaker_implied_prob, 66.67)
        self.assertEqual(enriched.expected_value, 0.0)
        self.assertTrue(enriched.expected_value_is_heuristic)
        self.assertEqual(enriched.probability_source, ProbabilitySource.BOOKMAKER_IMPLIED)
        self.assertIsNone(enriched.model_probability)


if __name__ == "__main__":
    unittest.main()
