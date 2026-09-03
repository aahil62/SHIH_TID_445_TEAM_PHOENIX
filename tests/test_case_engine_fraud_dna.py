"""CaseEngine's Stage B wiring: _build_graph_evidence and _run_dna_analysis
now delegate to GraphBuilder and the Fraud DNA package instead of the
Stage A stubs. Uses temp-file-backed cases_path/dna_store so tests never
touch the real fraudlens/data/ files.
"""

import os
import tempfile
import unittest

from fraudlens.core.cases.case_engine import CaseEngine
from fraudlens.core.dna.store import FraudDNAStore
from fraudlens.core.scoring.graph_agent import GraphAgent
from fraudlens.models.schemas import Decision, Transaction


def _txn(txn_id, account_id, device_id, ip_address, amount, minute, merchant_id="M_CT") -> Transaction:
    return Transaction(
        txn_id=txn_id,
        account_id=account_id,
        amount=amount,
        merchant_id=merchant_id,
        merchant_category="digital_goods",
        device_id=device_id,
        ip_address=ip_address,
        timestamp=f"2026-09-01T10:{minute:02d}:00+00:00",
    )


def _card_testing_ring_txns() -> list[Transaction]:
    """3 accounts, one shared device/IP/merchant, tiny amounts in a tight
    window — deliberately close to the seeded card-testing pattern."""
    txns = []
    amounts = [2.0, 3.5, 5.0, 6.5, 8.0, 9.0]
    accounts = ["RING-A1", "RING-A2", "RING-A3"]
    i = 0
    for minute, account_id in enumerate(accounts * 2):
        txns.append(
            _txn(f"R{i}", account_id, "D_CT", "IP_CT", amounts[i % len(amounts)], minute)
        )
        i += 1
    return txns


def _normal_txn() -> Transaction:
    return Transaction(
        txn_id="N1",
        account_id="NORMAL-A1",
        amount=42.0,
        merchant_id="M_NORMAL",
        merchant_category="groceries",
        device_id="D_NORMAL",
        ip_address="9.9.9.9",
        timestamp="2026-09-01T12:00:00+00:00",
    )


class CaseEngineFraudDNATests(unittest.TestCase):
    def setUp(self) -> None:
        self._cases_tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._cases_tmp.close()
        self._dna_tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._dna_tmp.close()
        os.remove(self._dna_tmp.name)  # let FraudDNAStore auto-seed it
        self.addCleanup(lambda: os.path.exists(self._cases_tmp.name) and os.remove(self._cases_tmp.name))
        self.addCleanup(lambda: os.path.exists(self._dna_tmp.name) and os.remove(self._dna_tmp.name))

    def _engine(self, transactions: list[Transaction]) -> CaseEngine:
        graph_agent = GraphAgent()
        graph_agent.build_index(transactions)
        return CaseEngine(
            transactions,
            agents=[graph_agent],
            cases_path=self._cases_tmp.name,
            dna_store=FraudDNAStore(path=self._dna_tmp.name),
        )

    def test_ring_transaction_gets_graph_evidence_and_dna_match(self) -> None:
        ring_txns = _card_testing_ring_txns()
        engine = self._engine(ring_txns)

        case = engine.analyze(ring_txns[0].txn_id)

        self.assertIsNotNone(case.graph_evidence)
        self.assertTrue(case.graph_evidence.suspicious_cluster)
        self.assertEqual(case.graph_evidence.ring_size, 3)
        self.assertIn("D_CT", case.graph_evidence.shared_devices)
        self.assertNotEqual(case.decision, Decision.CLEAR)

        self.assertIsNotNone(case.fraud_dna_match)
        self.assertEqual(case.fraud_dna_match.matched_ring_id, "SEED-CARD-TESTING")
        self.assertGreater(case.fraud_dna_match.similarity_score, 0.5)
        self.assertTrue(case.fraud_dna_match.recommendation)
        self.assertIn("Fraud DNA Alert", case.recommended_action)

    def test_normal_transaction_gets_no_graph_evidence_or_dna_match(self) -> None:
        txn = _normal_txn()
        engine = self._engine([txn])

        case = engine.analyze(txn.txn_id)

        self.assertIsNone(case.graph_evidence)
        self.assertIsNone(case.fraud_dna_match)
        self.assertEqual(case.decision, Decision.CLEAR)


if __name__ == "__main__":
    unittest.main()
