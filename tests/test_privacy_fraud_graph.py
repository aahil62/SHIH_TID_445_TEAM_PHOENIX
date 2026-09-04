"""public_fraud_graph() — the masking layer between GraphBuilder's real
node/edge output and the API. The one thing this must never do is leak a
raw account/device/IP identifier, including via node_id (which embeds the
raw value internally, unlike the already-masked label)."""

import unittest

from fraudlens.core.graph.builder import GraphBuilder
from fraudlens.core.privacy import public_fraud_graph
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


class PublicFraudGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.txns = [
            _txn("T1", "ACC-00110", "DEV-4471", "203.0.113.9"),
            _txn("T2", "ACC-00220", "DEV-4471", "203.0.113.9"),
            _txn("T3", "ACC-00330", "DEV-4471", "203.0.113.9"),
        ]
        self.builder = GraphBuilder()
        self.builder.build(self.txns)
        self.graph = self.builder.get_ring_graph("T1")
        self.flagged = self.builder.flagged_account_node_id("T1")

    def test_node_labels_are_masked(self) -> None:
        result = public_fraud_graph(self.graph, self.flagged)
        for node in result["nodes"]:
            if node["node_type"] == "account":
                self.assertIn("••", node["label"])
                self.assertNotIn("ACC-00110", node["label"])
                self.assertNotIn("ACC-00220", node["label"])
                self.assertNotIn("ACC-00330", node["label"])
            if node["node_type"] == "device":
                self.assertIn("••", node["label"])
                self.assertNotIn("DEV-4471", node["label"])
            if node["node_type"] == "ip":
                self.assertIn("••", node["label"])
                self.assertNotIn("203.0.113.9", node["label"])

    def test_no_raw_identifier_anywhere_in_node_ids(self) -> None:
        result = public_fraud_graph(self.graph, self.flagged)
        raw_values = ["ACC-00110", "ACC-00220", "ACC-00330", "DEV-4471", "203.0.113.9"]
        for node in result["nodes"]:
            for raw in raw_values:
                self.assertNotIn(raw, node["id"])
        for edge in result["edges"]:
            for raw in raw_values:
                self.assertNotIn(raw, edge["source"])
                self.assertNotIn(raw, edge["target"])

    def test_edges_still_reference_valid_node_ids(self) -> None:
        result = public_fraud_graph(self.graph, self.flagged)
        node_ids = {n["id"] for n in result["nodes"]}
        for edge in result["edges"]:
            self.assertIn(edge["source"], node_ids)
            self.assertIn(edge["target"], node_ids)

    def test_flagged_node_id_matches_a_real_node(self) -> None:
        result = public_fraud_graph(self.graph, self.flagged)
        node_ids = {n["id"] for n in result["nodes"]}
        self.assertIn(result["flagged_node_id"], node_ids)

    def test_flagged_node_id_none_when_not_provided(self) -> None:
        result = public_fraud_graph(self.graph, None)
        self.assertIsNone(result["flagged_node_id"])

    def test_edge_weights_and_types_pass_through_real(self) -> None:
        result = public_fraud_graph(self.graph, self.flagged)
        device_edges = [e for e in result["edges"] if e["edge_type"] == "uses_device"]
        self.assertEqual(len(device_edges), 3)
        for e in device_edges:
            self.assertEqual(e["weight"], 1.0)

    def test_is_suspicious_passes_through_real(self) -> None:
        result = public_fraud_graph(self.graph, self.flagged)
        device_node = next(n for n in result["nodes"] if n["node_type"] == "device")
        self.assertTrue(device_node["is_suspicious"])

    def test_ring_id_and_size_pass_through_real(self) -> None:
        result = public_fraud_graph(self.graph, self.flagged)
        self.assertEqual(result["ring_size"], 3)
        self.assertEqual(result["ring_id"], self.graph.ring_id)


if __name__ == "__main__":
    unittest.main()
