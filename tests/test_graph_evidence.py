import unittest

from fraudlens.core.graph.builder import GraphBuilder
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


class GetGraphEvidenceTests(unittest.TestCase):
    def test_returns_none_for_isolated_account(self) -> None:
        builder = GraphBuilder()
        builder.build([
            _txn("T1", "A1", "D1", "IP1"),
            _txn("T2", "A2", "D2", "IP2"),
        ])
        self.assertIsNone(builder.get_graph_evidence("T1"))

    def test_populates_evidence_for_a_ring(self) -> None:
        txns = [
            _txn("T1", "A1", "D_SHARED", "IP_SHARED", merchant_id="M_SHARED"),
            _txn("T2", "A2", "D_SHARED", "IP_SHARED", merchant_id="M_SHARED"),
            _txn("T3", "A3", "D_SHARED", "IP_SHARED", merchant_id="M_SHARED"),
        ]
        builder = GraphBuilder()
        builder.build(txns)
        evidence = builder.get_graph_evidence("T1")

        self.assertIsNotNone(evidence)
        self.assertTrue(evidence.suspicious_cluster)
        self.assertEqual(evidence.ring_size, 3)
        self.assertIsNotNone(evidence.ring_id)
        self.assertEqual(evidence.connected_accounts, ["A1", "A2", "A3"])
        self.assertEqual(evidence.shared_devices, ["D_SHARED"])
        self.assertEqual(evidence.shared_ips, ["IP_SHARED"])
        self.assertEqual(evidence.shared_merchants, ["M_SHARED"])
        self.assertGreater(evidence.graph_density, 0.0)
        self.assertTrue(evidence.evidence_summary)

    def test_merchant_used_by_single_account_is_not_shared(self) -> None:
        txns = [
            _txn("T1", "A1", "D_SHARED", "IP_SHARED", merchant_id="M1"),
            _txn("T2", "A2", "D_SHARED", "IP_SHARED", merchant_id="M2"),
        ]
        builder = GraphBuilder()
        builder.build(txns)
        evidence = builder.get_graph_evidence("T1")
        self.assertEqual(evidence.shared_merchants, [])

    def test_raises_for_unknown_txn(self) -> None:
        builder = GraphBuilder()
        builder.build([_txn("T1", "A1", "D1", "IP1")])
        with self.assertRaises(ValueError):
            builder.get_graph_evidence("UNKNOWN")


if __name__ == "__main__":
    unittest.main()
