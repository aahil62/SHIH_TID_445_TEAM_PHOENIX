"""CaseEngine.get_fraud_graph() — the real node/edge graph + flagged node
id behind GET /cases/{txn_id}/graph."""

import os
import tempfile
import unittest

from fraudlens.core.cases.case_engine import CaseEngine
from fraudlens.models.schemas import Transaction


def _txn(txn_id, account_id, device_id, ip_address, merchant_id="M1") -> Transaction:
    return Transaction(
        txn_id=txn_id,
        account_id=account_id,
        amount=50.0,
        merchant_id=merchant_id,
        merchant_category="grocery",
        device_id=device_id,
        ip_address=ip_address,
        timestamp="2026-09-01T10:00:00+00:00",
    )


class CaseEngineFraudGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._tmp.close()
        self.addCleanup(lambda: os.path.exists(self._tmp.name) and os.remove(self._tmp.name))

    def test_returns_none_for_no_ring(self) -> None:
        txns = [
            _txn("T1", "A1", "D1", "IP1"),
            _txn("T2", "A2", "D2", "IP2"),
        ]
        engine = CaseEngine(txns, cases_path=self._tmp.name)
        self.assertIsNone(engine.get_fraud_graph("T1"))

    def test_returns_none_for_unknown_txn(self) -> None:
        engine = CaseEngine([], cases_path=self._tmp.name)
        self.assertIsNone(engine.get_fraud_graph("TXN-DOES-NOT-EXIST"))

    def test_returns_real_graph_and_flagged_node_for_a_ring(self) -> None:
        txns = [
            _txn("T1", "A1", "D_SHARED", "IP_SHARED"),
            _txn("T2", "A2", "D_SHARED", "IP_SHARED"),
            _txn("T3", "A3", "D_SHARED", "IP_SHARED"),
        ]
        engine = CaseEngine(txns, cases_path=self._tmp.name)
        result = engine.get_fraud_graph("T1")

        self.assertIsNotNone(result)
        graph, flagged_node_id = result
        self.assertEqual(graph.ring_size, 3)
        self.assertEqual(flagged_node_id, "account:A1")
        self.assertIn(flagged_node_id, {n.node_id for n in graph.nodes})

        account_labels = sorted(n.label for n in graph.nodes if n.node_type == "account")
        self.assertEqual(account_labels, ["A1", "A2", "A3"])


if __name__ == "__main__":
    unittest.main()
