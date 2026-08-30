"""
Unit Tests for Source Reliability Model Module
"""

import unittest
from engine.source_reliability import SourceReliabilityModel


class TestSourceReliability(unittest.TestCase):
    def test_bayesian_shrinkage_small_sample(self):
        # 10 wins out of 10 (100% empirical, N=10) with prior 0.75 and K=25
        # Regressed = (10 / 35) * 1.0 + (25 / 35) * 0.75 = 0.2857 + 0.5357 = 0.8214
        regressed = SourceReliabilityModel.calculate_regressed_reliability(wins=10, total_predictions=10)
        self.assertAlmostEqual(regressed, 0.8214, places=3)

    def test_bayesian_shrinkage_large_sample(self):
        # 800 wins out of 1000 (80% empirical, N=1000) with prior 0.75 and K=25
        # Regressed = (1000 / 1025) * 0.80 + (25 / 1025) * 0.75 = 0.7805 + 0.0183 = 0.7988
        regressed = SourceReliabilityModel.calculate_regressed_reliability(wins=800, total_predictions=1000)
        self.assertAlmostEqual(regressed, 0.7988, places=3)

    def test_recency_decay(self):
        # 0 days inactive -> weight = 1.0
        w_0 = SourceReliabilityModel.calculate_recency_weight(0.0)
        self.assertEqual(w_0, 1.0)

        # 30 days inactive -> weight = exp(-0.023 * 30) = exp(-0.69) = ~0.50
        w_30 = SourceReliabilityModel.calculate_recency_weight(30.0)
        self.assertAlmostEqual(w_30, 0.5016, places=2)

    def test_evaluate_source_credibility_combined(self):
        # Active tipster with 80% accuracy over 50 predictions
        credibility = SourceReliabilityModel.evaluate_source_credibility(
            wins=40, total_predictions=50, days_inactive=2.0
        )
        self.assertGreater(credibility, 0.70)
        self.assertLessEqual(credibility, 1.00)


if __name__ == "__main__":
    unittest.main()
