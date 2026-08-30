"""
Unit Tests for Correlation Manager Module
"""

import unittest
from engine.contracts import BetCandidate
from engine.correlation_manager import CorrelationManager


class TestCorrelationManager(unittest.TestCase):
    def test_are_conflicting_same_event_id(self):
        c1 = BetCandidate(
            candidate_id="c1",
            event_id="match_100",
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
        )
        c2 = BetCandidate(
            candidate_id="c2",
            event_id="match_100",
            sport="Football",
            league="EPL",
            home_team="Arsenal",
            away_team="Chelsea",
            kickoff_time=None,
            market_id="10",
            market_name="Over 1.5",
            outcome_id="1",
            outcome_name="Over 1.5",
            decimal_odds=1.15,
        )

        self.assertTrue(CorrelationManager.are_conflicting(c1, c2))

    def test_deduplicate_intra_match_candidates(self):
        c1_high = BetCandidate(
            candidate_id="c1",
            event_id="match_100",
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
            composite_score=0.90,
        )
        c2_low = BetCandidate(
            candidate_id="c2",
            event_id="match_100",
            sport="Football",
            league="EPL",
            home_team="Arsenal",
            away_team="Chelsea",
            kickoff_time=None,
            market_id="10",
            market_name="Over 1.5",
            outcome_id="1",
            outcome_name="Over 1.5",
            decimal_odds=1.15,
            composite_score=0.75,
        )
        c3_diff = BetCandidate(
            candidate_id="c3",
            event_id="match_200",
            sport="Football",
            league="La Liga",
            home_team="Real Madrid",
            away_team="Sevilla",
            kickoff_time=None,
            market_id="18",
            market_name="Double Chance",
            outcome_id="12",
            outcome_name="1X",
            decimal_odds=1.18,
            composite_score=0.85,
        )

        candidates = [c1_high, c2_low, c3_diff]
        deduped = CorrelationManager.deduplicate_intra_match_candidates(candidates)

        self.assertEqual(len(deduped), 2)
        self.assertEqual(deduped[0].candidate_id, "c1")
        self.assertEqual(deduped[1].candidate_id, "c3")

    def test_calculate_exposure_penalty(self):
        # 4 selections all from the same league (100% vs 40% threshold)
        legs = [
            BetCandidate(
                candidate_id=f"c_{i}",
                event_id=f"e_{i}",
                sport="Football",
                league="Premier League",
                home_team=f"Team {i}A",
                away_team=f"Team {i}B",
                kickoff_time=None,
                market_id="18",
                market_name="DC",
                outcome_id="1",
                outcome_name="1X",
                decimal_odds=1.20,
            )
            for i in range(4)
        ]

        penalty = CorrelationManager.calculate_exposure_penalty(legs, max_league_pct=0.40)
        self.assertGreater(penalty, 0.0)

    def test_validate_slip_independence(self):
        c1 = BetCandidate(
            candidate_id="c1",
            event_id="e1",
            sport="Football",
            league="EPL",
            home_team="Arsenal",
            away_team="Chelsea",
            kickoff_time=None,
            market_id="18",
            market_name="DC",
            outcome_id="1",
            outcome_name="1X",
            decimal_odds=1.20,
        )
        c2 = BetCandidate(
            candidate_id="c2",
            event_id="e2",
            sport="Football",
            league="La Liga",
            home_team="Real Madrid",
            away_team="Barcelona",
            kickoff_time=None,
            market_id="18",
            market_name="DC",
            outcome_id="1",
            outcome_name="1X",
            decimal_odds=1.20,
        )

        is_valid, reason = CorrelationManager.validate_slip_independence([c1, c2])
        self.assertTrue(is_valid)


if __name__ == "__main__":
    unittest.main()
