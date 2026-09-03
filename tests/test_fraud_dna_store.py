import os
import tempfile
import unittest

from fraudlens.core.dna.store import FraudDNAStore
from fraudlens.models.schemas import FraudDNAProfile


def _profile(ring_id="RING-CUSTOM") -> FraudDNAProfile:
    return FraudDNAProfile(
        ring_id=ring_id,
        ring_size=4,
        shared_devices=1,
        shared_ips=1,
        avg_amount=100.0,
        max_amount=200.0,
        merchant_category_count=2,
        velocity_score=0.5,
        graph_density=0.5,
        fraud_type="unclassified_ring",
        modus_operandi="test",
        first_detected="2026-09-01T00:00:00+00:00",
    )


class FraudDNAStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._tmp.close()
        os.remove(self._tmp.name)  # store should auto-seed when the file doesn't exist
        self.addCleanup(lambda: os.path.exists(self._tmp.name) and os.remove(self._tmp.name))

    def test_auto_seeds_when_file_missing(self) -> None:
        store = FraudDNAStore(path=self._tmp.name)
        profiles = store.all()
        self.assertGreaterEqual(len(profiles), 4)
        self.assertTrue(os.path.exists(self._tmp.name))

    def test_add_and_get(self) -> None:
        store = FraudDNAStore(path=self._tmp.name)
        store.add(_profile())
        self.assertEqual(store.get("RING-CUSTOM").ring_id, "RING-CUSTOM")

    def test_unknown_ring_id_returns_none(self) -> None:
        store = FraudDNAStore(path=self._tmp.name)
        self.assertIsNone(store.get("RING-DOES-NOT-EXIST"))

    def test_reload_from_disk_roundtrips_added_profile(self) -> None:
        first = FraudDNAStore(path=self._tmp.name)
        first.add(_profile())

        second = FraudDNAStore(path=self._tmp.name)
        reloaded = second.get("RING-CUSTOM")
        self.assertIsNotNone(reloaded)
        self.assertEqual(reloaded.avg_amount, 100.0)
        # Seed profiles persist alongside the newly added one.
        self.assertGreaterEqual(len(second.all()), 5)


if __name__ == "__main__":
    unittest.main()
