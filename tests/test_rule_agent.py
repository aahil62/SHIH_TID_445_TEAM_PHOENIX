import unittest

from fraudlens.core.scoring.rule_agent import RuleAgent
from fraudlens.models.schemas import Transaction


def _txn(**overrides) -> Transaction:
    defaults = dict(
        txn_id="TXN-RULE-001",
        account_id="ACC-0001",
        amount=45.00,
        merchant_id="MER-0001",
        merchant_category="groceries",
        device_id="DEV-0001",
        ip_address="10.0.0.1",
        timestamp="2026-09-03T14:30:00+00:00",
        location="us",
        channel="in_store",
    )
    defaults.update(overrides)
    return Transaction(**defaults)


class RuleAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = RuleAgent()

    def test_agent_name(self) -> None:
        self.assertEqual(self.agent.name, "rule_agent")

    def test_clean_transaction_scores_low(self) -> None:
        txn = _txn()
        result = self.agent.score(txn)

        self.assertEqual(result.agent_name, "rule_agent")
        self.assertLess(result.score, 0.3)
        self.assertAlmostEqual(result.confidence, 0.9)
        self.assertIn("No rule violations detected", result.reasons)

    def test_multi_flag_transaction_scores_high(self) -> None:
        # Major amount + risky category + risky location + risky hour +
        # online high-amount + round number: should stack to a high score.
        txn = _txn(
            amount=500_000.00,
            merchant_category="crypto_exchange",
            location="nigeria",
            timestamp="2026-09-03T02:15:00+00:00",
            channel="online",
        )
        result = self.agent.score(txn)

        self.assertGreater(result.score, 0.7)
        self.assertGreaterEqual(len(result.reasons), 4)
        joined = " ".join(result.reasons)
        self.assertIn("major threshold", joined)
        self.assertIn("crypto_exchange", joined)
        self.assertIn("nigeria", joined.lower())

    def test_minor_amount_threshold_flag(self) -> None:
        txn = _txn(amount=200_000.00, channel="in_store")
        result = self.agent.score(txn)
        joined = " ".join(result.reasons)
        self.assertIn("minor threshold", joined)

    def test_risky_hour_flag(self) -> None:
        txn = _txn(timestamp="2026-09-03T03:00:00+00:00")
        result = self.agent.score(txn)
        joined = " ".join(result.reasons)
        self.assertIn("high-risk hours", joined)

    def test_online_high_amount_flag(self) -> None:
        txn = _txn(amount=100_000.00, channel="online")
        result = self.agent.score(txn)
        joined = " ".join(result.reasons)
        self.assertIn("High-value online transaction", joined)

    def test_round_number_amount_flag(self) -> None:
        txn = _txn(amount=300.00)
        result = self.agent.score(txn)
        joined = " ".join(result.reasons)
        self.assertIn("round-number", joined)

    def test_just_under_threshold_amount_flag(self) -> None:
        txn = _txn(amount=148_000.00)
        result = self.agent.score(txn)
        joined = " ".join(result.reasons)
        self.assertIn("structuring", joined)

    def test_score_is_clamped_to_one(self) -> None:
        txn = _txn(
            amount=1_000_000.00,
            merchant_category="money_transfer",
            location="offshore",
            timestamp="2026-09-03T01:00:00+00:00",
            channel="online",
        )
        result = self.agent.score(txn)
        self.assertLessEqual(result.score, 1.0)

    def test_bad_timestamp_does_not_raise(self) -> None:
        txn = _txn(timestamp="not-a-real-timestamp")
        result = self.agent.score(txn)
        self.assertIsNotNone(result)
        joined = " ".join(result.reasons)
        self.assertNotIn("high-risk hours", joined)

    def test_empty_timestamp_does_not_raise(self) -> None:
        txn = _txn(timestamp="")
        result = self.agent.score(txn)
        self.assertIsNotNone(result)

    def test_unknown_merchant_category_and_location_are_ignored(self) -> None:
        txn = _txn(merchant_category="electronics", location="us")
        result = self.agent.score(txn)
        joined = " ".join(result.reasons)
        self.assertNotIn("Risky merchant category", joined)
        self.assertNotIn("Risky location", joined)


if __name__ == "__main__":
    unittest.main()
