import unittest

from fraudlens.core.graph.builder import GraphBuilder
from fraudlens.models.schemas import Transaction


def _txn(txn_id, account_id, device_id, ip_address, merchant_id="M1", amount=50.0) -> Transaction:
    return Transaction(
        txn_id=txn_id,
        account_id=account_id,
        amount=amount,
        merchant_id=merchant_id,
        merchant_category="grocery",
        device_id=device_id,
        ip_address=ip_address,
        timestamp="2026-09-01T10:00:00+00:00",
    )


class GraphBuilderBuildTests(unittest.TestCase):
    def test_creates_nodes_for_every_entity(self) -> None:
        txns = [_txn("T1", "A1", "D1", "IP1", merchant_id="M1")]
        graph = GraphBuilder().build(txns)
        node_types = {n.node_type for n in graph.nodes}
        self.assertEqual(node_types, {"account", "device", "ip", "merchant"})
        self.assertEqual(len(graph.nodes), 4)

    def test_creates_expected_edge_types(self) -> None:
        txns = [_txn("T1", "A1", "D1", "IP1", merchant_id="M1")]
        graph = GraphBuilder().build(txns)
        edge_types = {e.edge_type for e in graph.edges}
        self.assertEqual(edge_types, {"uses_device", "uses_ip", "transacts_with"})

    def test_repeated_pair_increments_edge_weight_not_duplicate(self) -> None:
        txns = [_txn("T1", "A1", "D1", "IP1"), _txn("T2", "A1", "D1", "IP1")]
        graph = GraphBuilder().build(txns)
        device_edges = [e for e in graph.edges if e.edge_type == "uses_device"]
        self.assertEqual(len(device_edges), 1)
        self.assertEqual(device_edges[0].weight, 2.0)

    def test_device_shared_by_multiple_accounts_is_flagged_suspicious(self) -> None:
        txns = [
            _txn("T1", "A1", "D_SHARED", "IP1"),
            _txn("T2", "A2", "D_SHARED", "IP2"),
        ]
        graph = GraphBuilder().build(txns)
        device_node = next(n for n in graph.nodes if n.node_type == "device")
        self.assertTrue(device_node.is_suspicious)

    def test_device_used_by_single_account_is_not_suspicious(self) -> None:
        txns = [_txn("T1", "A1", "D1", "IP1"), _txn("T2", "A1", "D1", "IP1")]
        graph = GraphBuilder().build(txns)
        device_node = next(n for n in graph.nodes if n.node_type == "device")
        self.assertFalse(device_node.is_suspicious)

    def test_ip_shared_by_multiple_accounts_is_flagged_suspicious(self) -> None:
        txns = [
            _txn("T1", "A1", "D1", "IP_SHARED"),
            _txn("T2", "A2", "D2", "IP_SHARED"),
        ]
        graph = GraphBuilder().build(txns)
        ip_node = next(n for n in graph.nodes if n.node_type == "ip")
        self.assertTrue(ip_node.is_suspicious)


class GraphBuilderSubgraphTests(unittest.TestCase):
    def test_raises_if_build_not_called(self) -> None:
        with self.assertRaises(ValueError):
            GraphBuilder().get_subgraph("T1")

    def test_raises_for_unknown_txn_id(self) -> None:
        builder = GraphBuilder()
        builder.build([_txn("T1", "A1", "D1", "IP1")])
        with self.assertRaises(ValueError):
            builder.get_subgraph("UNKNOWN")

    def test_ring_detected_for_shared_device_ring(self) -> None:
        # A1, A2, A3 all share device D_RING -> a 3-account ring.
        txns = [
            _txn("T1", "A1", "D_RING", "IP1"),
            _txn("T2", "A2", "D_RING", "IP2"),
            _txn("T3", "A3", "D_RING", "IP3"),
        ]
        builder = GraphBuilder()
        builder.build(txns)
        sub = builder.get_subgraph("T1", depth=2)
        self.assertIsNotNone(sub.ring_id)
        self.assertEqual(sub.ring_size, 3)

    def test_no_ring_for_isolated_account(self) -> None:
        txns = [
            _txn("T1", "A1", "D1", "IP1"),
            _txn("T2", "A2", "D2", "IP2"),
        ]
        builder = GraphBuilder()
        builder.build(txns)
        sub = builder.get_subgraph("T1", depth=2)
        self.assertIsNone(sub.ring_id)
        self.assertEqual(sub.ring_size, 0)

    def test_subgraph_contains_only_nodes_within_depth(self) -> None:
        # A1 -uses_device-> D1 <-uses_device- A2 -uses_device-> D2 <-uses_device- A3
        # A1 to A2 is 2 hops (via D1); A1 to A3 is 4 hops.
        txns = [
            _txn("T1", "A1", "D1", "IPX1", merchant_id="M1"),
            _txn("T2", "A2", "D1", "IPX2", merchant_id="M2"),
            _txn("T3", "A2", "D2", "IPX3", merchant_id="M2"),
            _txn("T4", "A3", "D2", "IPX4", merchant_id="M3"),
        ]
        builder = GraphBuilder()
        builder.build(txns)

        sub_depth1 = builder.get_subgraph("T1", depth=1)
        labels_depth1 = {n.label for n in sub_depth1.nodes}
        self.assertIn("A1", labels_depth1)
        self.assertIn("D1", labels_depth1)
        self.assertNotIn("A2", labels_depth1)

        sub_depth2 = builder.get_subgraph("T1", depth=2)
        labels_depth2 = {n.label for n in sub_depth2.nodes}
        self.assertIn("A2", labels_depth2)
        self.assertNotIn("A3", labels_depth2)


if __name__ == "__main__":
    unittest.main()
