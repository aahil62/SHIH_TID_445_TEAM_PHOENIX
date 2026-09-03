"""GraphBuilder.get_ring_graph() and flagged_account_node_id() — the real
node/edge structure backing the /cases/{txn_id}/graph endpoint, scoped to
the detected ring the same way get_graph_evidence() already is."""

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


class GetRingGraphTests(unittest.TestCase):
    def test_returns_none_for_isolated_account(self) -> None:
        builder = GraphBuilder()
        builder.build([
            _txn("T1", "A1", "D1", "IP1"),
            _txn("T2", "A2", "D2", "IP2"),
        ])
        self.assertIsNone(builder.get_ring_graph("T1"))

    def test_raises_for_unknown_txn(self) -> None:
        builder = GraphBuilder()
        builder.build([_txn("T1", "A1", "D1", "IP1")])
        with self.assertRaises(ValueError):
            builder.get_ring_graph("UNKNOWN")

    def test_ring_graph_contains_real_nodes_and_edges(self) -> None:
        txns = [
            _txn("T1", "A1", "D_SHARED", "IP_SHARED", merchant_id="M_SHARED"),
            _txn("T2", "A2", "D_SHARED", "IP_SHARED", merchant_id="M_SHARED"),
            _txn("T3", "A3", "D_SHARED", "IP_SHARED", merchant_id="M_SHARED"),
        ]
        builder = GraphBuilder()
        builder.build(txns)
        graph = builder.get_ring_graph("T1")

        self.assertIsNotNone(graph)
        self.assertEqual(graph.ring_size, 3)
        self.assertIsNotNone(graph.ring_id)

        account_labels = sorted(n.label for n in graph.nodes if n.node_type == "account")
        self.assertEqual(account_labels, ["A1", "A2", "A3"])

        device_node = next(n for n in graph.nodes if n.node_type == "device")
        self.assertEqual(device_node.label, "D_SHARED")
        self.assertTrue(device_node.is_suspicious)

        # Real edges: each account really does connect to the shared device.
        device_edges = [e for e in graph.edges if e.edge_type == "uses_device"]
        self.assertEqual(len(device_edges), 3)
        edge_sources = {e.source for e in device_edges}
        self.assertEqual(len(edge_sources), 3)  # one edge per account, not fabricated/duplicated

    def test_ring_graph_excludes_weakly_bridged_neighbor_cluster(self) -> None:
        # Same fixture as test_ring_detection_louvain.py's weak-bridge case:
        # the graph for C1 must not include C4/C5/C6's cluster.
        txns = []
        for account_id in ("C1", "C2", "C3"):
            txns.append(_txn(f"CLUSTER1-{account_id}", account_id, "D1", "IP1", "M1"))
        for account_id in ("C4", "C5", "C6"):
            txns.append(_txn(f"CLUSTER2-{account_id}", account_id, "D2", "IP2", "M2"))
        txns.append(_txn("BRIDGE-C3", "C3", "D_BRIDGE_C3", "IP_BRIDGE", "M3"))
        txns.append(_txn("BRIDGE-C4", "C4", "D_BRIDGE_C4", "IP_BRIDGE", "M3"))

        builder = GraphBuilder()
        builder.build(txns)
        graph = builder.get_ring_graph("CLUSTER1-C1", depth=8)

        account_labels = sorted(n.label for n in graph.nodes if n.node_type == "account")
        self.assertEqual(account_labels, ["C1", "C2", "C3"])
        self.assertNotIn("C4", account_labels)


class FlaggedAccountNodeIdTests(unittest.TestCase):
    def test_returns_none_for_unbuilt_graph(self) -> None:
        builder = GraphBuilder()
        self.assertIsNone(builder.flagged_account_node_id("T1"))

    def test_returns_none_for_unknown_txn(self) -> None:
        builder = GraphBuilder()
        builder.build([_txn("T1", "A1", "D1", "IP1")])
        self.assertIsNone(builder.flagged_account_node_id("UNKNOWN"))

    def test_returns_the_account_node_id_for_the_transaction(self) -> None:
        builder = GraphBuilder()
        builder.build([_txn("T1", "A1", "D1", "IP1")])
        self.assertEqual(builder.flagged_account_node_id("T1"), "account:A1")

    def test_flagged_node_id_is_present_in_its_own_ring_graph(self) -> None:
        txns = [
            _txn("T1", "A1", "D_SHARED", "IP1"),
            _txn("T2", "A2", "D_SHARED", "IP2"),
        ]
        builder = GraphBuilder()
        builder.build(txns)
        graph = builder.get_ring_graph("T1")
        flagged = builder.flagged_account_node_id("T1")
        self.assertIn(flagged, {n.node_id for n in graph.nodes})


if __name__ == "__main__":
    unittest.main()
