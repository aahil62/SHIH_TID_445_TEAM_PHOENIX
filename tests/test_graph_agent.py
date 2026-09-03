import unittest

from fraudlens.core.scoring.base import ScoringAgent
from fraudlens.core.scoring.graph_agent import GraphAgent
from fraudlens.models.schemas import Transaction


def _txn(txn_id, account_id, device_id, ip_address, amount=50.0) -> Transaction:
    return Transaction(
        txn_id=txn_id,
        account_id=account_id,
        amount=amount,
        merchant_id="M1",
        merchant_category="grocery",
        device_id=device_id,
        ip_address=ip_address,
        timestamp="2026-09-01T10:00:00+00:00",
    )


class GraphAgentTests(unittest.TestCase):
    def test_satisfies_scoring_agent_protocol(self) -> None:
        agent = GraphAgent()
        self.assertIsInstance(agent, ScoringAgent)
        self.assertEqual(agent.name, "graph_agent")

    def test_normal_isolated_transaction_scores_low(self) -> None:
        txns = [
            _txn("T1", "A1", "D1", "IP1"),
            _txn("T2", "A2", "D2", "IP2"),
            _txn("T3", "A3", "D3", "IP3"),
        ]
        agent = GraphAgent()
        agent.build_index(txns)
        result = agent.score(txns[0])
        self.assertLess(result.score, 0.3)
        self.assertEqual(result.reasons, [])

    def test_multi_account_ring_via_shared_device_is_flagged(self) -> None:
        # 4 accounts share one device -> major ring signal + major device-share signal.
        txns = [
            _txn("T1", "A1", "D_RING", "IP1"),
            _txn("T2", "A2", "D_RING", "IP2"),
            _txn("T3", "A3", "D_RING", "IP3"),
            _txn("T4", "A4", "D_RING", "IP4"),
        ]
        agent = GraphAgent()
        agent.build_index(txns)
        result = agent.score(txns[0])
        self.assertGreaterEqual(result.score, 0.85)
        self.assertTrue(any("shared" in r.lower() for r in result.reasons))
        self.assertTrue(any("ring" in r.lower() for r in result.reasons))
        self.assertEqual(result.metadata["estimated_ring_size"], 4)

    def test_confidence_scales_with_ring_size(self) -> None:
        small_ring_txns = [
            _txn("T1", "A1", "D_SMALL", "IP1"),
            _txn("T2", "A2", "D_SMALL", "IP2"),
        ]
        big_ring_txns = [
            _txn("T1", "A1", "D_BIG", "IP1"),
            _txn("T2", "A2", "D_BIG", "IP2"),
            _txn("T3", "A3", "D_BIG", "IP3"),
            _txn("T4", "A4", "D_BIG", "IP4"),
            _txn("T5", "A5", "D_BIG", "IP5"),
        ]
        small_agent = GraphAgent()
        small_agent.build_index(small_ring_txns)
        small_result = small_agent.score(small_ring_txns[0])

        big_agent = GraphAgent()
        big_agent.build_index(big_ring_txns)
        big_result = big_agent.score(big_ring_txns[0])

        self.assertGreater(big_result.confidence, small_result.confidence)

    def test_minor_device_sharing_scores_lower_than_major(self) -> None:
        minor_txns = [
            _txn("T1", "A1", "D_MINOR", "IP1"),
            _txn("T2", "A2", "D_MINOR", "IP2"),
        ]
        major_txns = [
            _txn("T1", "A1", "D_MAJOR", "IP1"),
            _txn("T2", "A2", "D_MAJOR", "IP2"),
            _txn("T3", "A3", "D_MAJOR", "IP3"),
            _txn("T4", "A4", "D_MAJOR", "IP4"),
        ]
        minor_agent = GraphAgent()
        minor_agent.build_index(minor_txns)
        minor_result = minor_agent.score(minor_txns[0])

        major_agent = GraphAgent()
        major_agent.build_index(major_txns)
        major_result = major_agent.score(major_txns[0])

        self.assertLess(minor_result.score, major_result.score)

    def test_account_using_many_devices_is_flagged(self) -> None:
        txns = [
            _txn("T1", "A1", "D1", "IP1"),
            _txn("T2", "A1", "D2", "IP1"),
            _txn("T3", "A1", "D3", "IP1"),
            _txn("T4", "A1", "D4", "IP1"),
        ]
        agent = GraphAgent()
        agent.build_index(txns)
        result = agent.score(txns[-1])
        self.assertTrue(any("distinct devices" in r for r in result.reasons))

    def test_score_without_build_index_does_not_raise(self) -> None:
        agent = GraphAgent()
        result = agent.score(_txn("T1", "A1", "D1", "IP1"))
        self.assertEqual(result.score, 0.05)


if __name__ == "__main__":
    unittest.main()
