import unittest

from fraudlens.core.scoring.velocity_agent import VelocityAgent
from fraudlens.models.schemas import Transaction


def _txn(txn_id: str, account_id: str, amount: float, timestamp: str) -> Transaction:
    return Transaction(
        txn_id=txn_id,
        account_id=account_id,
        amount=amount,
        merchant_id="MER-0001",
        merchant_category="groceries",
        device_id="DEV-0001",
        ip_address="10.0.0.1",
        timestamp=timestamp,
    )


class VelocityAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = VelocityAgent()

    def test_agent_name(self) -> None:
        self.assertEqual(self.agent.name, "velocity_agent")

    def test_no_history_returns_low_confidence_unknown(self) -> None:
        txn = _txn("TXN-001", "ACC-1", 50.0, "2026-09-03T12:00:00+00:00")
        result = self.agent.score(txn)

        self.assertEqual(result.score, 0.0)
        self.assertAlmostEqual(result.confidence, 0.5)
        self.assertIn("No transaction history", result.reasons[0])

    def test_clean_transaction_with_history_scores_low(self) -> None:
        history = [
            _txn("TXN-H1", "ACC-1", 40.0, "2026-09-02T09:00:00+00:00"),
            _txn("TXN-H2", "ACC-1", 60.0, "2026-09-02T18:00:00+00:00"),
        ]
        self.agent.set_transactions(history)

        txn = _txn("TXN-002", "ACC-1", 50.0, "2026-09-03T12:00:00+00:00")
        result = self.agent.score(txn)

        self.assertLess(result.score, 0.2)
        self.assertAlmostEqual(result.confidence, 0.85)
        self.assertIn("No velocity anomalies detected", result.reasons)

    def test_high_frequency_1h_window_scores_high(self) -> None:
        base = "2026-09-03T12:0{}:00+00:00"
        history = [
            _txn("TXN-H1", "ACC-2", 30.0, base.format(0)),
            _txn("TXN-H2", "ACC-2", 30.0, base.format(2)),
            _txn("TXN-H3", "ACC-2", 30.0, base.format(4)),
            _txn("TXN-H4", "ACC-2", 30.0, base.format(6)),
        ]
        self.agent.set_transactions(history)

        txn = _txn("TXN-003", "ACC-2", 30.0, "2026-09-03T12:08:00+00:00")
        result = self.agent.score(txn)

        self.assertGreater(result.score, 0.4)
        joined = " ".join(result.reasons)
        self.assertIn("last hour", joined)

    def test_high_frequency_24h_window_scores(self) -> None:
        history = [
            _txn(f"TXN-H{i}", "ACC-3", 20.0, f"2026-09-03T{i:02d}:00:00+00:00")
            for i in range(0, 10)
        ]
        self.agent.set_transactions(history)

        txn = _txn("TXN-004", "ACC-3", 20.0, "2026-09-03T23:00:00+00:00")
        result = self.agent.score(txn)

        joined = " ".join(result.reasons)
        self.assertIn("last 24 hours", joined)

    def test_high_24h_spend_flags(self) -> None:
        history = [
            _txn("TXN-H1", "ACC-4", 500_000.0, "2026-09-03T08:00:00+00:00"),
        ]
        self.agent.set_transactions(history)

        txn = _txn("TXN-005", "ACC-4", 400_000.0, "2026-09-03T18:00:00+00:00")
        result = self.agent.score(txn)

        joined = " ".join(result.reasons)
        self.assertIn("24h spend", joined)
        self.assertGreater(result.score, 0.0)

    def test_card_testing_pattern_flags(self) -> None:
        history = [
            _txn("TXN-H1", "ACC-5", 2.0, "2026-09-03T12:00:00+00:00"),
            _txn("TXN-H2", "ACC-5", 5.0, "2026-09-03T12:03:00+00:00"),
        ]
        self.agent.set_transactions(history)

        txn = _txn("TXN-006", "ACC-5", 1.0, "2026-09-03T12:06:00+00:00")
        result = self.agent.score(txn)

        joined = " ".join(result.reasons)
        self.assertIn("Card-testing pattern", joined)
        self.assertGreater(result.score, 0.3)

    def test_multi_flag_transaction_scores_high(self) -> None:
        history = [
            _txn("TXN-H1", "ACC-6", 150_000.0, "2026-09-03T10:00:00+00:00"),
            _txn("TXN-H2", "ACC-6", 150_000.0, "2026-09-03T11:00:00+00:00"),
            _txn("TXN-H3", "ACC-6", 150_000.0, "2026-09-03T11:30:00+00:00"),
            _txn("TXN-H4", "ACC-6", 150_000.0, "2026-09-03T11:45:00+00:00"),
            _txn("TXN-H5", "ACC-6", 150_000.0, "2026-09-03T11:50:00+00:00"),
        ]
        self.agent.set_transactions(history)

        txn = _txn("TXN-007", "ACC-6", 150_000.0, "2026-09-03T11:55:00+00:00")
        result = self.agent.score(txn)

        self.assertGreater(result.score, 0.6)
        self.assertGreaterEqual(len(result.reasons), 2)

    def test_bad_timestamp_does_not_raise(self) -> None:
        history = [_txn("TXN-H1", "ACC-7", 40.0, "2026-09-02T09:00:00+00:00")]
        self.agent.set_transactions(history)

        txn = _txn("TXN-008", "ACC-7", 40.0, "not-a-timestamp")
        result = self.agent.score(txn)

        self.assertEqual(result.score, 0.0)
        self.assertIn("could not be parsed", result.reasons[0])

    def test_unparseable_history_entries_are_skipped_not_fatal(self) -> None:
        history = [
            _txn("TXN-H1", "ACC-8", 40.0, "garbage-timestamp"),
            _txn("TXN-H2", "ACC-8", 40.0, "2026-09-03T11:00:00+00:00"),
        ]
        self.agent.set_transactions(history)

        txn = _txn("TXN-009", "ACC-8", 40.0, "2026-09-03T11:30:00+00:00")
        result = self.agent.score(txn)

        self.assertIsNotNone(result)

    def test_new_account_with_no_prior_transactions_scores_low(self) -> None:
        self.agent.set_transactions([])

        txn = _txn("TXN-010", "ACC-NEW", 50.0, "2026-09-03T12:00:00+00:00")
        result = self.agent.score(txn)

        self.assertLess(result.score, 0.2)
        self.assertAlmostEqual(result.confidence, 0.85)


if __name__ == "__main__":
    unittest.main()
