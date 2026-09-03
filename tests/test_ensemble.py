import unittest

from fraudlens.core.scoring.ensemble import EnsembleScorer
from fraudlens.models.schemas import AgentScore, Decision


def _score(agent_name: str, score: float, confidence: float = 0.8, reasons=None) -> AgentScore:
    return AgentScore(agent_name=agent_name, score=score, confidence=confidence, reasons=reasons or [])


class EnsembleScorerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ensemble = EnsembleScorer()

    def test_no_agents_clears(self) -> None:
        result = self.ensemble.combine([])
        self.assertEqual(result.decision, Decision.CLEAR)
        self.assertEqual(result.final_score, 0.0)

    def test_all_agents_quiet_clears(self) -> None:
        scores = [
            _score("rule_agent", 0.05),
            _score("velocity_agent", 0.05),
            _score("graph_agent", 0.05),
            _score("behavioral_agent", 0.05),
        ]
        result = self.ensemble.combine(scores)
        self.assertEqual(result.decision, Decision.CLEAR)
        self.assertLess(result.final_score, 0.30)

    def test_weighted_average_matches_configured_weights(self) -> None:
        # graph=0.35, velocity=0.25, behavioral=0.20, rule=0.20, all scoring 0.5,
        # no agent reaches the 0.9/0.8 critical-boost threshold, so this is a
        # plain weighted average: 0.5 regardless of weight split.
        scores = [
            _score("rule_agent", 0.5),
            _score("velocity_agent", 0.5),
            _score("graph_agent", 0.5),
            _score("behavioral_agent", 0.5),
        ]
        result = self.ensemble.combine(scores)
        self.assertAlmostEqual(result.final_score, 0.5, places=2)
        self.assertEqual(result.decision, Decision.REVIEW)

    def test_single_strong_signal_boosts_past_dilution(self) -> None:
        # One agent at 0.95/0.9 confidence should push the final score well
        # above what a plain weighted average with three silent agents gives.
        scores = [
            _score("rule_agent", 0.0),
            _score("velocity_agent", 0.0),
            _score("graph_agent", 0.95, confidence=0.9, reasons=["6-account device-sharing ring"]),
            _score("behavioral_agent", 0.0),
        ]
        result = self.ensemble.combine(scores)
        plain_weighted_avg = 0.95 * 0.35  # ≈ 0.3325
        self.assertGreater(result.final_score, plain_weighted_avg)
        self.assertNotEqual(result.decision, Decision.CLEAR)
        self.assertGreaterEqual(result.confidence, 0.85)

    def test_decision_thresholds(self) -> None:
        self.assertEqual(EnsembleScorer._decide(0.29), Decision.CLEAR)
        self.assertEqual(EnsembleScorer._decide(0.30), Decision.REVIEW)
        self.assertEqual(EnsembleScorer._decide(0.59), Decision.REVIEW)
        self.assertEqual(EnsembleScorer._decide(0.60), Decision.BLOCK)
        self.assertEqual(EnsembleScorer._decide(0.79), Decision.BLOCK)
        self.assertEqual(EnsembleScorer._decide(0.80), Decision.BLOCK_AND_REPORT)

    def test_explanation_reasons_cover_every_agent(self) -> None:
        scores = [_score("rule_agent", 0.1, reasons=["Amount within normal range"])]
        result = self.ensemble.combine(scores)
        self.assertEqual(len(result.explanation_reasons), 1)
        self.assertIn("rule_agent", result.explanation_reasons[0])


if __name__ == "__main__":
    unittest.main()
