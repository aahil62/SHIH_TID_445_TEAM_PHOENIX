"""GraphBuilder._detect_ring() switched from a BFS/union-find connected-
components walk to Louvain community detection (fraudlens/core/graph/
community.py). This file has two jobs:

1. Re-run the simple ring shapes the old BFS/union-find fixtures already
   covered (a single tightly-shared device/IP ring) and confirm they
   still get flagged the same way — same ring_size, a real ring_id, all
   accounts present. A single dense cluster has no way to sub-partition
   for higher modularity, so Louvain and connected-components must agree
   here regardless of algorithm.

2. Add the case connected-components structurally cannot get right: two
   internally-dense clusters joined by one weak single-shared-IP bridge.
   Connected-components treats "connected" as binary, so that one weak
   link would merge both clusters into a single over-counted 6-account
   ring. Louvain weighs connection *strength* (accounts sharing a device
   AND an IP pull harder than accounts sharing only one weak IP), so it
   resolves this into two separate, correctly-sized 3-account rings.
"""

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


class SimpleRingShapesStillFlagTests(unittest.TestCase):
    """Same fixtures as test_graph_builder.py / test_graph_evidence.py —
    confirms the Louvain swap didn't change behavior on the easy cases."""

    def test_three_accounts_sharing_one_device_still_a_ring_of_three(self) -> None:
        txns = [
            _txn("T1", "A1", "D_RING", "IP1"),
            _txn("T2", "A2", "D_RING", "IP2"),
            _txn("T3", "A3", "D_RING", "IP3"),
        ]
        builder = GraphBuilder()
        builder.build(txns)
        subgraph = builder.get_subgraph("T1", depth=2)

        self.assertIsNotNone(subgraph.ring_id)
        self.assertEqual(subgraph.ring_size, 3)

    def test_isolated_accounts_still_report_no_ring(self) -> None:
        txns = [
            _txn("T1", "A1", "D1", "IP1"),
            _txn("T2", "A2", "D2", "IP2"),
        ]
        builder = GraphBuilder()
        builder.build(txns)
        subgraph = builder.get_subgraph("T1", depth=2)

        self.assertIsNone(subgraph.ring_id)
        self.assertEqual(subgraph.ring_size, 0)

    def test_card_testing_style_ring_still_flagged_via_evidence(self) -> None:
        # Same shape as the card-testing fixture in test_case_engine_fraud_dna.py:
        # one shared device/IP/merchant across 3 accounts.
        txns = [
            _txn("T1", "RING-A1", "D_CT", "IP_CT", merchant_id="M_CT"),
            _txn("T2", "RING-A2", "D_CT", "IP_CT", merchant_id="M_CT"),
            _txn("T3", "RING-A3", "D_CT", "IP_CT", merchant_id="M_CT"),
        ]
        builder = GraphBuilder()
        builder.build(txns)
        evidence = builder.get_graph_evidence("T1")

        self.assertIsNotNone(evidence)
        self.assertTrue(evidence.suspicious_cluster)
        self.assertEqual(evidence.ring_size, 3)
        self.assertEqual(sorted(evidence.connected_accounts), ["RING-A1", "RING-A2", "RING-A3"])


class WeaklyBridgedClustersTests(unittest.TestCase):
    """The case plain connected-components gets wrong: two dense 3-account
    clusters joined by a single weak shared-IP link."""

    def setUp(self) -> None:
        txns = []
        # Cluster 1: C1/C2/C3 share both a device and an IP — a strong tie.
        for account_id in ("C1", "C2", "C3"):
            txns.append(_txn(f"CLUSTER1-{account_id}", account_id, "D1", "IP1", "M1"))
        # Cluster 2: C4/C5/C6 share both a device and an IP — a strong tie.
        for account_id in ("C4", "C5", "C6"):
            txns.append(_txn(f"CLUSTER2-{account_id}", account_id, "D2", "IP2", "M2"))
        # Weak bridge: C3 and C4 share only a single IP, no device.
        txns.append(_txn("BRIDGE-C3", "C3", "D_BRIDGE_C3", "IP_BRIDGE", "M3"))
        txns.append(_txn("BRIDGE-C4", "C4", "D_BRIDGE_C4", "IP_BRIDGE", "M3"))

        self.builder = GraphBuilder()
        self.builder.build(txns)

    def test_bridged_clusters_resolve_to_two_separate_rings_not_one(self) -> None:
        evidence_c1 = self.builder.get_graph_evidence("CLUSTER1-C1", depth=8)
        evidence_c4 = self.builder.get_graph_evidence("CLUSTER2-C4", depth=8)

        self.assertIsNotNone(evidence_c1)
        self.assertIsNotNone(evidence_c4)

        # Each account's own ring is its 3-account cluster, not the
        # 6-account union a connected-components walk would have reported.
        self.assertEqual(evidence_c1.ring_size, 3)
        self.assertEqual(evidence_c4.ring_size, 3)
        self.assertNotEqual(evidence_c1.ring_id, evidence_c4.ring_id)

    def test_bridge_account_belongs_to_its_own_dense_cluster(self) -> None:
        # C3 sits on the bridge but is still most tightly tied to cluster 1.
        evidence = self.builder.get_graph_evidence("CLUSTER1-C3", depth=8)
        self.assertEqual(evidence.ring_size, 3)


if __name__ == "__main__":
    unittest.main()
