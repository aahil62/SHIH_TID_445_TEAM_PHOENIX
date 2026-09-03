"""score_fraud_dna() as a scoring signal, and proof that it actually moves
the ensemble's decision now — not just decorates recommended_action after
the decision is already final."""

import os
import tempfile
import unittest

from fraudlens.core.dna.agent import score_fraud_dna
from fraudlens.core.dna.extractor import FraudDNAExtractor
from fraudlens.core.dna.matcher import FraudDNAMatcher
from fraudlens.core.dna.store import FraudDNAStore
from fraudlens.core.scoring.ensemble import EnsembleScorer
from fraudlens.models.schemas import AgentScore, GraphEvidence, Transaction


def _ring_txn(txn_id: str, account_id: str) -> Transaction:
    return Transaction(
        txn_id=txn_id, account_id=account_id, amount=3.0, merchant_id="M1",
        merchant_category="digital_goods", device_id="D_SHARED", ip_address="IP_SHARED",
        timestamp="2026-09-01T10:00:00+00:00",
    )


def _evidence(ring_size: int = 3) -> GraphEvidence:
    return GraphEvidence(
        connected_accounts=[f"RING-A{i}" for i in range(ring_size)],
        shared_devices=["D_SHARED"], shared_ips=["IP_SHARED"], shared_merchants=[],
        ring_size=ring_size, ring_id="RING-TEST", suspicious_cluster=True,
        graph_density=0.8, evidence_summary="test ring",
    )


class ScoreFraudDnaTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp.close()
        os.remove(tmp.name)  # let FraudDNAStore auto-seed it
        self.addCleanup(lambda: os.path.exists(tmp.name) and os.remove(tmp.name))
        self.extractor = FraudDNAExtractor()
        self.matcher = FraudDNAMatcher(FraudDNAStore(path=tmp.name))

    def test_no_evidence_abstains(self) -> None:
        score, match = score_fraud_dna(None, [], self.extractor, self.matcher)
        self.assertEqual(score.agent_name, "fraud_dna_agent")
        self.assertEqual(score.confidence, 0.0)
        self.assertEqual(score.score, 0.0)
        self.assertIsNone(match)

    def test_evidence_but_no_ring_transactions_abstains(self) -> None:
        score, match = score_fraud_dna(_evidence(), [], self.extractor, self.matcher)
        self.assertEqual(score.confidence, 0.0)
        self.assertIsNone(match)

    def test_strong_match_scores_and_matches(self) -> None:
        ring_txns = [_ring_txn(f"T{i}", f"RING-A{i}") for i in range(3)]
        # Tiny, tight-window transactions closely resemble SEED-CARD-TESTING.
        score, match = score_fraud_dna(_evidence(3), ring_txns, self.extractor, self.matcher)
        self.assertGreater(score.score, 0.0)
        self.assertGreater(score.confidence, 0.0)
        self.assertIsNotNone(match)
        self.assertEqual(score.score, match.similarity_score)
        self.assertEqual(score.confidence, match.similarity_score)


class DnaEnsembleIntegrationTests(unittest.TestCase):
    """The actual claim: a strong DNA match measurably raises the ensemble
    score above what the same base agents alone would produce — not just
    appended text after an already-final decision."""

    def test_dna_match_raises_score_above_base_agents_alone(self) -> None:
        ensemble = EnsembleScorer()
        base_scores = [
            AgentScore(agent_name="rule_agent", score=0.35, confidence=0.9, reasons=["mild flag"]),
            AgentScore(agent_name="velocity_agent", score=0.30, confidence=0.7, reasons=["mild flag"]),
            AgentScore(agent_name="behavioral_agent", score=0.35, confidence=0.6, reasons=["mild flag"]),
            AgentScore(agent_name="graph_agent", score=0.40, confidence=0.7, reasons=["mild flag"]),
            AgentScore(agent_name="ml_agent", score=0.35, confidence=0.85, reasons=["mild flag"]),
        ]
        without_dna = ensemble.combine(base_scores)

        strong_dna = AgentScore(
            agent_name="fraud_dna_agent", score=0.92, confidence=0.92,
            reasons=["92% match to known 'bust_out_ring' pattern"],
        )
        with_dna = ensemble.combine(base_scores + [strong_dna])

        self.assertGreater(with_dna.final_score, without_dna.final_score)

    def test_dna_abstain_does_not_drag_down_a_borderline_case(self) -> None:
        """The failure mode this whole design avoids: an abstaining agent's
        implicit 0.0 must NOT count as a confident 'clear' vote."""
        ensemble = EnsembleScorer()
        base_scores = [
            AgentScore(agent_name="rule_agent", score=0.5, confidence=0.9),
            AgentScore(agent_name="graph_agent", score=0.5, confidence=0.9),
        ]
        without_dna_field = ensemble.combine(base_scores)

        abstained_dna = AgentScore(
            agent_name="fraud_dna_agent", score=0.0, confidence=0.0,
            reasons=["No ring detected — Fraud DNA not applicable"],
        )
        with_abstained_dna = ensemble.combine(base_scores + [abstained_dna])

        self.assertEqual(without_dna_field.final_score, with_abstained_dna.final_score)


if __name__ == "__main__":
    unittest.main()
