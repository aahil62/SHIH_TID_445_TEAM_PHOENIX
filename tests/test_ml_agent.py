import unittest

from fraudlens.core.scoring.ml_agent import MLAgent
from fraudlens.data.synthetic_generator import generate_synthetic_transactions
from fraudlens.models.schemas import Transaction


def _txn(**overrides) -> Transaction:
    defaults = dict(
        txn_id="TXN-ML-001",
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


class MLAgentTests(unittest.TestCase):
    def test_agent_name(self) -> None:
        self.assertEqual(MLAgent().name, "ml_agent")

    def test_unfitted_agent_returns_placeholder_without_raising(self) -> None:
        agent = MLAgent()
        result = agent.score(_txn())

        self.assertEqual(result.score, 0.0)
        self.assertLess(result.confidence, 0.5)
        self.assertIn("not been trained", result.reasons[0])

    def test_fit_on_empty_list_raises(self) -> None:
        agent = MLAgent()
        with self.assertRaises(ValueError):
            agent.fit([])

    def test_fit_then_score_produces_valid_agent_score(self) -> None:
        agent = MLAgent()
        training_data = generate_synthetic_transactions(
            num_normal=60, num_high_amount=15, num_risky_merchant=15,
            num_odd_hour=10, num_card_testing_bursts=0,
            num_high_velocity_bursts=0, num_fraud_rings=0, seed=1,
        )
        agent.fit(training_data)

        result = agent.score(_txn())

        self.assertEqual(result.agent_name, "ml_agent")
        self.assertGreaterEqual(result.score, 0.0)
        self.assertLessEqual(result.score, 1.0)
        self.assertAlmostEqual(result.confidence, 0.85)
        self.assertTrue(result.reasons)

    def test_fraud_leaning_transactions_score_higher_than_normal_on_average(self) -> None:
        training_data = generate_synthetic_transactions(
            num_normal=150, num_high_amount=40, num_risky_merchant=40,
            num_odd_hour=30, num_card_testing_bursts=0,
            num_high_velocity_bursts=0, num_fraud_rings=0, seed=2,
        )
        agent = MLAgent()
        agent.fit(training_data)

        fraud_txns = [t for t in training_data if t.is_fraud_demo_label][:30]
        normal_txns = [t for t in training_data if not t.is_fraud_demo_label][:30]

        avg_fraud_score = sum(agent.score(t).score for t in fraud_txns) / len(fraud_txns)
        avg_normal_score = sum(agent.score(t).score for t in normal_txns) / len(normal_txns)

        self.assertGreater(avg_fraud_score, avg_normal_score)

    def test_feature_importances_populated_after_fit(self) -> None:
        agent = MLAgent()
        training_data = generate_synthetic_transactions(
            num_normal=40, num_high_amount=10, num_risky_merchant=10,
            num_odd_hour=5, num_card_testing_bursts=0,
            num_high_velocity_bursts=0, num_fraud_rings=0, seed=3,
        )
        agent.fit(training_data)

        self.assertTrue(agent.feature_importances)
        self.assertAlmostEqual(sum(agent.feature_importances.values()), 1.0, places=3)

    def test_bad_timestamp_does_not_raise(self) -> None:
        agent = MLAgent()
        training_data = generate_synthetic_transactions(
            num_normal=30, num_high_amount=5, num_risky_merchant=5,
            num_odd_hour=5, num_card_testing_bursts=0,
            num_high_velocity_bursts=0, num_fraud_rings=0, seed=4,
        )
        agent.fit(training_data)

        result = agent.score(_txn(timestamp="not-a-real-timestamp"))
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.score, 0.0)
        self.assertLessEqual(result.score, 1.0)

    def test_missing_location_does_not_raise(self) -> None:
        agent = MLAgent()
        training_data = generate_synthetic_transactions(
            num_normal=30, num_high_amount=5, num_risky_merchant=5,
            num_odd_hour=5, num_card_testing_bursts=0,
            num_high_velocity_bursts=0, num_fraud_rings=0, seed=5,
        )
        agent.fit(training_data)

        result = agent.score(_txn(location=""))
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
