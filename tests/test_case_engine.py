import os
import tempfile
import unittest

from fraudlens.core.cases.case_engine import CaseEngine
from fraudlens.models.schemas import AgentScore, Decision, Transaction


class _FakeAgent:
    """Stand-in for a real scoring agent until feature/rules-velocity and
    feature/graph-behavioral land theirs — proves the orchestration works
    end-to-end without waiting on either branch."""

    def __init__(self, name: str, score: float, confidence: float = 0.8, reasons=None) -> None:
        self.name = name
        self._score = score
        self._confidence = confidence
        self._reasons = reasons or []

    def score(self, txn: Transaction) -> AgentScore:
        return AgentScore(
            agent_name=self.name,
            score=self._score,
            confidence=self._confidence,
            reasons=self._reasons,
        )


def _sample_transaction(txn_id: str = "TXN-TEST-001") -> Transaction:
    return Transaction(
        txn_id=txn_id,
        account_id="ACC-0001",
        amount=2500.00,
        merchant_id="MER-0001",
        merchant_category="electronics",
        device_id="DEV-0001",
        ip_address="10.0.0.1",
        timestamp="2026-09-03T12:00:00+00:00",
    )


class CaseEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._tmp.close()
        self.addCleanup(lambda: os.path.exists(self._tmp.name) and os.remove(self._tmp.name))

    def test_end_to_end_scoring_produces_case(self) -> None:
        txn = _sample_transaction()
        agents = [
            _FakeAgent("rule_agent", 0.1),
            _FakeAgent("velocity_agent", 0.15),
            _FakeAgent("graph_agent", 0.95, confidence=0.9, reasons=["Shared device across 3 accounts"]),
            _FakeAgent("behavioral_agent", 0.4),
        ]
        engine = CaseEngine([txn], agents=agents, cases_path=self._tmp.name)

        case = engine.analyze(txn.txn_id)

        self.assertEqual(case.txn_id, txn.txn_id)
        self.assertEqual(case.case_id, f"CASE-{txn.txn_id}")
        self.assertEqual(len(case.agent_scores), 4)
        self.assertGreater(case.final_score, 0.0)
        self.assertNotEqual(case.decision, Decision.CLEAR)
        self.assertTrue(case.recommended_action)
        # graph_evidence / fraud_dna_match are None until Stage B lands
        self.assertIsNone(case.graph_evidence)
        self.assertIsNone(case.fraud_dna_match)

    def test_unknown_transaction_raises(self) -> None:
        engine = CaseEngine([], agents=[], cases_path=self._tmp.name)
        with self.assertRaises(ValueError):
            engine.analyze("TXN-DOES-NOT-EXIST")

    def test_case_persists_and_is_retrievable(self) -> None:
        txn = _sample_transaction("TXN-TEST-002")
        engine = CaseEngine([txn], agents=[_FakeAgent("rule_agent", 0.2)], cases_path=self._tmp.name)

        engine.analyze(txn.txn_id)
        retrieved = engine.get_case_by_txn(txn.txn_id)

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.txn_id, txn.txn_id)
        self.assertIn(retrieved, engine.list_cases())

    def test_cases_reload_from_disk(self) -> None:
        txn = _sample_transaction("TXN-TEST-003")
        first_engine = CaseEngine([txn], agents=[_FakeAgent("rule_agent", 0.5)], cases_path=self._tmp.name)
        first_engine.analyze(txn.txn_id)

        second_engine = CaseEngine([txn], agents=[], cases_path=self._tmp.name)

        self.assertIsNotNone(second_engine.get_case_by_txn(txn.txn_id))

    def test_no_agents_still_produces_a_clear_case(self) -> None:
        txn = _sample_transaction("TXN-TEST-004")
        engine = CaseEngine([txn], agents=[], cases_path=self._tmp.name)

        case = engine.analyze(txn.txn_id)

        self.assertEqual(case.decision, Decision.CLEAR)
        self.assertEqual(case.agent_scores, [])


if __name__ == "__main__":
    unittest.main()
