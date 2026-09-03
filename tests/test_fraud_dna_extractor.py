import unittest

from fraudlens.core.dna.extractor import FraudDNAExtractor
from fraudlens.models.schemas import GraphEvidence, Transaction


def _txn(txn_id, account_id, amount, hour_minute="10:00:00", category="digital_goods") -> Transaction:
    return Transaction(
        txn_id=txn_id,
        account_id=account_id,
        amount=amount,
        merchant_id="M1",
        merchant_category=category,
        device_id="D_SHARED",
        ip_address="1.2.3.4",
        timestamp=f"2026-09-01T{hour_minute}+00:00",
    )


def _evidence(ring_size=3, shared_devices=None, shared_ips=None, graph_density=0.8) -> GraphEvidence:
    return GraphEvidence(
        connected_accounts=["A1", "A2", "A3"][:ring_size],
        shared_devices=shared_devices or ["D_SHARED"],
        shared_ips=shared_ips or ["IP_SHARED"],
        shared_merchants=[],
        ring_size=ring_size,
        ring_id="RING-TEST1234",
        suspicious_cluster=True,
        graph_density=graph_density,
        evidence_summary="test ring",
    )


class FraudDNAExtractorTests(unittest.TestCase):
    def test_raises_for_empty_ring(self) -> None:
        extractor = FraudDNAExtractor()
        with self.assertRaises(ValueError):
            extractor.extract_profile([], _evidence())

    def test_extracts_basic_stats_from_ring_transactions(self) -> None:
        txns = [
            _txn("T1", "A1", 10.0, "10:00:00"),
            _txn("T2", "A2", 20.0, "10:05:00"),
            _txn("T3", "A3", 30.0, "10:10:00"),
        ]
        evidence = _evidence(ring_size=3)
        profile = FraudDNAExtractor().extract_profile(txns, evidence)

        self.assertEqual(profile.ring_id, "RING-TEST1234")
        self.assertEqual(profile.ring_size, 3)
        self.assertEqual(profile.shared_devices, 1)
        self.assertEqual(profile.shared_ips, 1)
        self.assertAlmostEqual(profile.avg_amount, 20.0)
        self.assertEqual(profile.max_amount, 30.0)
        self.assertEqual(profile.merchant_category_count, 1)
        self.assertEqual(profile.graph_density, 0.8)
        self.assertTrue(profile.fraud_type)
        self.assertTrue(profile.modus_operandi)

    def test_velocity_score_in_unit_range(self) -> None:
        txns = [_txn(f"T{i}", f"A{i}", 5.0, f"10:0{i}:00") for i in range(5)]
        profile = FraudDNAExtractor().extract_profile(txns, _evidence())
        self.assertGreaterEqual(profile.velocity_score, 0.0)
        self.assertLessEqual(profile.velocity_score, 1.0)

    def test_burst_of_tiny_amounts_classified_card_testing(self) -> None:
        # Tight window, tiny amounts -> high velocity + low avg amount.
        txns = [_txn(f"T{i}", f"A{i}", 3.0 + i, f"10:0{i}:00") for i in range(6)]
        profile = FraudDNAExtractor().extract_profile(txns, _evidence(graph_density=0.9))
        self.assertEqual(profile.fraud_type, "card_testing_ring")

    def test_ring_id_falls_back_when_evidence_has_none(self) -> None:
        evidence = _evidence()
        evidence.ring_id = None
        txns = [_txn("T1", "A1", 10.0)]
        profile = FraudDNAExtractor().extract_profile(txns, evidence)
        self.assertTrue(profile.ring_id.startswith("RING-UNKNOWN-"))


if __name__ == "__main__":
    unittest.main()
