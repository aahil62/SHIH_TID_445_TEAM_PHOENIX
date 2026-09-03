import unittest
from collections import defaultdict
from datetime import datetime

from fraudlens.data.synthetic_generator import (
    FRAUD_PATTERN_TYPES,
    generate_synthetic_transactions,
    make_fraud_ring,
)
import random


class SyntheticGeneratorTests(unittest.TestCase):
    def test_generates_expected_total_count(self) -> None:
        txns = generate_synthetic_transactions(
            num_normal=10,
            num_high_amount=2,
            num_risky_merchant=2,
            num_odd_hour=2,
            num_card_testing_bursts=0,
            num_high_velocity_bursts=0,
            num_fraud_rings=0,
            seed=1,
        )
        self.assertEqual(len(txns), 16)

    def test_every_transaction_is_labeled(self) -> None:
        txns = generate_synthetic_transactions(
            num_normal=20, num_high_amount=5, num_risky_merchant=5,
            num_odd_hour=5, num_card_testing_bursts=2,
            num_high_velocity_bursts=2, num_fraud_rings=1, seed=2,
        )
        for t in txns:
            self.assertIsInstance(t.is_fraud_demo_label, bool)
            self.assertTrue(t.fraud_pattern_type)
            if t.is_fraud_demo_label:
                self.assertIn(t.fraud_pattern_type, FRAUD_PATTERN_TYPES)
            else:
                self.assertEqual(t.fraud_pattern_type, "normal")

    def test_contains_a_mix_of_normal_and_fraud(self) -> None:
        txns = generate_synthetic_transactions(seed=3)
        fraud = [t for t in txns if t.is_fraud_demo_label]
        normal = [t for t in txns if not t.is_fraud_demo_label]
        self.assertGreater(len(fraud), 0)
        self.assertGreater(len(normal), 0)

    def test_timestamps_are_parseable_iso(self) -> None:
        txns = generate_synthetic_transactions(
            num_normal=5, num_high_amount=1, num_risky_merchant=1,
            num_odd_hour=1, num_card_testing_bursts=1,
            num_high_velocity_bursts=1, num_fraud_rings=1, seed=4,
        )
        for t in txns:
            datetime.fromisoformat(t.timestamp)

    def test_amounts_are_positive(self) -> None:
        txns = generate_synthetic_transactions(seed=5)
        for t in txns:
            self.assertGreater(t.amount, 0)

    def test_same_seed_is_reproducible(self) -> None:
        first = generate_synthetic_transactions(seed=99)
        second = generate_synthetic_transactions(seed=99)
        self.assertEqual([t.txn_id for t in first], [t.txn_id for t in second])
        self.assertEqual([t.amount for t in first], [t.amount for t in second])

    def test_fraud_ring_shares_devices_and_ips_across_accounts(self) -> None:
        rng = random.Random(7)
        day = datetime(2026, 8, 15)
        ring_txns = make_fraud_ring(rng, ring_index=0, day=day)

        accounts = {t.account_id for t in ring_txns}
        devices = {t.device_id for t in ring_txns}
        ips = {t.ip_address for t in ring_txns}

        self.assertGreaterEqual(len(accounts), 4)
        # The whole point of a ring: fewer distinct devices/IPs than accounts,
        # because accounts share them.
        self.assertLess(len(devices), len(accounts))
        self.assertLess(len(ips), len(accounts))
        for t in ring_txns:
            self.assertTrue(t.is_fraud_demo_label)
            self.assertEqual(t.fraud_pattern_type, "fraud_ring")

        # At least one device/IP is actually reused by more than one account.
        device_to_accounts: dict[str, set[str]] = defaultdict(set)
        for t in ring_txns:
            device_to_accounts[t.device_id].add(t.account_id)
        self.assertTrue(any(len(accts) > 1 for accts in device_to_accounts.values()))

    def test_card_testing_burst_all_under_800_rupees(self) -> None:
        txns = generate_synthetic_transactions(
            num_normal=0, num_high_amount=0, num_risky_merchant=0,
            num_odd_hour=0, num_card_testing_bursts=3,
            num_high_velocity_bursts=0, num_fraud_rings=0, seed=8,
        )
        self.assertTrue(txns)
        for t in txns:
            self.assertEqual(t.fraud_pattern_type, "card_testing")
            self.assertLess(t.amount, 800.0)

    def test_zero_counts_produce_empty_dataset(self) -> None:
        txns = generate_synthetic_transactions(
            num_normal=0, num_high_amount=0, num_risky_merchant=0,
            num_odd_hour=0, num_card_testing_bursts=0,
            num_high_velocity_bursts=0, num_fraud_rings=0, seed=9,
        )
        self.assertEqual(txns, [])


if __name__ == "__main__":
    unittest.main()
