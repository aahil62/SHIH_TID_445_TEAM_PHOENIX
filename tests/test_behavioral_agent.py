import unittest

from fraudlens.core.scoring.base import ScoringAgent
from fraudlens.core.scoring.behavioral_agent import BehavioralAgent
from fraudlens.models.schemas import Transaction


def _txn(
    txn_id,
    account_id="A1",
    amount=50.0,
    merchant_category="grocery",
    device_id="D1",
    location="NY",
    channel="online",
    hour=10,
) -> Transaction:
    return Transaction(
        txn_id=txn_id,
        account_id=account_id,
        amount=amount,
        merchant_id="M1",
        merchant_category=merchant_category,
        device_id=device_id,
        ip_address="1.2.3.4",
        timestamp=f"2026-09-01T{hour:02d}:00:00+00:00",
        location=location,
        channel=channel,
    )


def _history(n=8, hour=10) -> list[Transaction]:
    return [_txn(f"H{i}", amount=50.0, hour=hour) for i in range(n)]


class BehavioralAgentTests(unittest.TestCase):
    def test_satisfies_scoring_agent_protocol(self) -> None:
        agent = BehavioralAgent()
        self.assertIsInstance(agent, ScoringAgent)
        self.assertEqual(agent.name, "behavioral_agent")

    def test_thin_history_gets_fixed_low_score(self) -> None:
        txns = [_txn("T1")]
        agent = BehavioralAgent()
        agent.build_profiles(txns)
        result = agent.score(txns[0])
        self.assertEqual(result.score, 0.1)
        self.assertEqual(result.confidence, 0.4)

    def test_unknown_account_gets_fixed_low_score(self) -> None:
        agent = BehavioralAgent()
        agent.build_profiles([_txn("H1", account_id="OTHER")])
        result = agent.score(_txn("T1", account_id="A1"))
        self.assertEqual(result.score, 0.1)
        self.assertEqual(result.confidence, 0.4)

    def test_normal_transaction_within_baseline_scores_low(self) -> None:
        history = _history(n=8, hour=10)
        normal_txn = _txn("T_NEW", amount=55.0, hour=10)
        all_txns = history + [normal_txn]
        agent = BehavioralAgent()
        agent.build_profiles(all_txns)
        result = agent.score(normal_txn)
        self.assertLess(result.score, 0.3)
        self.assertEqual(result.reasons, [])

    def test_amount_far_above_average_is_flagged_major(self) -> None:
        history = _history(n=8, hour=10)
        spike_txn = _txn("T_SPIKE", amount=50.0 * 6, hour=10)  # 6x average
        all_txns = history + [spike_txn]
        agent = BehavioralAgent()
        agent.build_profiles(all_txns)
        result = agent.score(spike_txn)
        self.assertGreaterEqual(result.score, 0.85)
        self.assertTrue(any("average" in r for r in result.reasons))

    def test_new_device_is_flagged(self) -> None:
        history = _history(n=5, hour=10)
        new_device_txn = _txn("T_NEWDEV", device_id="D_NEVER_SEEN", hour=10)
        all_txns = history + [new_device_txn]
        agent = BehavioralAgent()
        agent.build_profiles(all_txns)
        result = agent.score(new_device_txn)
        self.assertTrue(any("device" in r.lower() for r in result.reasons))

    def test_unusual_hour_flagged_via_zscore(self) -> None:
        # Consistent history at hour 10 with slight jitter, then a 3am transaction.
        history = [
            _txn("H1", hour=9),
            _txn("H2", hour=10),
            _txn("H3", hour=10),
            _txn("H4", hour=11),
            _txn("H5", hour=10),
        ]
        odd_hour_txn = _txn("T_ODD", hour=3)
        all_txns = history + [odd_hour_txn]
        agent = BehavioralAgent()
        agent.build_profiles(all_txns)
        result = agent.score(odd_hour_txn)
        self.assertTrue(any("hour" in r.lower() for r in result.reasons))

    def test_confidence_increases_with_history_size(self) -> None:
        thin_history = _history(n=2, hour=10)
        thin_txn = _txn("T1", hour=10)
        thin_agent = BehavioralAgent()
        thin_agent.build_profiles(thin_history + [thin_txn])
        thin_result = thin_agent.score(thin_txn)

        rich_history = _history(n=6, hour=10)
        rich_txn = _txn("T1", hour=10)
        rich_agent = BehavioralAgent()
        rich_agent.build_profiles(rich_history + [rich_txn])
        rich_result = rich_agent.score(rich_txn)

        self.assertGreater(rich_result.confidence, thin_result.confidence)


if __name__ == "__main__":
    unittest.main()
