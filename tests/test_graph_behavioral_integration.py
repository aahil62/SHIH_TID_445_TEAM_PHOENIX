"""End-to-end checks that GraphBuilder/GraphAgent/BehavioralAgent, combined
through the real EnsembleScorer, actually flag a multi-account device-sharing
ring and actually clear a normal transaction. Fixtures here are small and
self-contained — real end-to-end verification against synthetic_generator
data happens once feature/rules-velocity merges into main.
"""

import unittest

from fraudlens.core.graph.builder import GraphBuilder
from fraudlens.core.scoring.behavioral_agent import BehavioralAgent
from fraudlens.core.scoring.ensemble import EnsembleScorer
from fraudlens.core.scoring.graph_agent import GraphAgent
from fraudlens.models.schemas import Decision, Transaction


def _txn(
    txn_id,
    account_id,
    device_id,
    ip_address,
    amount=50.0,
    merchant_id="M1",
    merchant_category="grocery",
    location="NY",
    channel="online",
    hour=10,
) -> Transaction:
    return Transaction(
        txn_id=txn_id,
        account_id=account_id,
        amount=amount,
        merchant_id=merchant_id,
        merchant_category=merchant_category,
        device_id=device_id,
        ip_address=ip_address,
        timestamp=f"2026-09-01T{hour:02d}:00:00+00:00",
        location=location,
        channel=channel,
    )


class RingDetectionIntegrationTests(unittest.TestCase):
    """A 4-account ring sharing one device should be flagged end-to-end."""

    def setUp(self) -> None:
        self.ring_txns = [
            _txn("R1", "RING_A1", "D_SHARED", "IP_R1"),
            _txn("R2", "RING_A2", "D_SHARED", "IP_R2"),
            _txn("R3", "RING_A3", "D_SHARED", "IP_R3"),
            _txn("R4", "RING_A4", "D_SHARED", "IP_R4"),
        ]
        # A well-established, unrelated account with a normal, in-baseline txn.
        self.normal_history = [_txn(f"N{i}", "NORMAL_A1", "D_N1", "IP_N1", amount=40.0 + i)
                                for i in range(6)]
        self.normal_txn = _txn("N_LATEST", "NORMAL_A1", "D_N1", "IP_N1", amount=45.0)

        self.all_txns = self.ring_txns + self.normal_history + [self.normal_txn]

        self.builder = GraphBuilder()
        self.builder.build(self.all_txns)

        self.graph_agent = GraphAgent()
        self.graph_agent.build_index(self.all_txns)

        self.behavioral_agent = BehavioralAgent()
        self.behavioral_agent.build_profiles(self.all_txns)

        self.ensemble = EnsembleScorer()

    def test_graph_builder_flags_shared_device_ring(self) -> None:
        subgraph = self.builder.get_subgraph("R1", depth=2)
        self.assertIsNotNone(subgraph.ring_id)
        self.assertEqual(subgraph.ring_size, 4)
        device_node = next(n for n in subgraph.nodes if n.node_type == "device")
        self.assertTrue(device_node.is_suspicious)

    def test_ring_transaction_escalates_through_ensemble(self) -> None:
        ring_txn = self.ring_txns[0]
        agent_scores = [
            self.graph_agent.score(ring_txn),
            self.behavioral_agent.score(ring_txn),
        ]
        result = self.ensemble.combine(agent_scores)
        self.assertIn(result.decision, (Decision.BLOCK, Decision.BLOCK_AND_REPORT))
        self.assertGreaterEqual(result.final_score, 0.60)

    def test_normal_transaction_stays_clear_through_ensemble(self) -> None:
        agent_scores = [
            self.graph_agent.score(self.normal_txn),
            self.behavioral_agent.score(self.normal_txn),
        ]
        result = self.ensemble.combine(agent_scores)
        self.assertEqual(result.decision, Decision.CLEAR)
        self.assertLess(result.final_score, 0.30)


if __name__ == "__main__":
    unittest.main()
