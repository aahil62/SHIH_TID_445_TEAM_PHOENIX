import unittest

from fraudlens.core.dna.matcher import FraudDNAMatcher
from fraudlens.models.schemas import FraudDNAProfile


def _profile(**overrides) -> FraudDNAProfile:
    base = dict(
        ring_id="RING-QUERY",
        ring_size=3,
        shared_devices=1,
        shared_ips=1,
        avg_amount=5.0,
        max_amount=9.0,
        merchant_category_count=2,
        velocity_score=0.9,
        graph_density=0.85,
        fraud_type="unclassified_ring",
        modus_operandi="",
        first_detected="2026-09-01T00:00:00+00:00",
    )
    base.update(overrides)
    return FraudDNAProfile(**base)


class _FakeStore:
    def __init__(self, profiles: list[FraudDNAProfile]) -> None:
        self._profiles = profiles

    def all(self) -> list[FraudDNAProfile]:
        return self._profiles


_CARD_TESTING_SEED = _profile(
    ring_id="SEED-CARD-TESTING",
    fraud_type="card_testing_ring",
    modus_operandi="Many tiny transactions to validate stolen cards.",
)

_BUST_OUT_SEED = _profile(
    ring_id="SEED-BUST-OUT",
    ring_size=7,
    avg_amount=2400.0,
    max_amount=8900.0,
    merchant_category_count=4,
    velocity_score=0.55,
    graph_density=0.45,
    fraud_type="bust_out_ring",
    modus_operandi="Synthetic identities run up balances then default.",
)


class FraudDNAMatcherTests(unittest.TestCase):
    def test_close_profile_matches_with_high_similarity(self) -> None:
        matcher = FraudDNAMatcher(_FakeStore([_CARD_TESTING_SEED, _BUST_OUT_SEED]))
        query = _profile(ring_id="RING-QUERY-1")  # deliberately close to the card-testing seed
        match = matcher.match(query)

        self.assertIsNotNone(match)
        self.assertEqual(match.matched_ring_id, "SEED-CARD-TESTING")
        self.assertEqual(match.fraud_type, "card_testing_ring")
        self.assertGreater(match.similarity_score, 0.8)
        self.assertTrue(match.recommendation)

    def test_dissimilar_profile_below_threshold_returns_none(self) -> None:
        matcher = FraudDNAMatcher(_FakeStore([_CARD_TESTING_SEED]), threshold=0.55)
        # Large ring, huge amounts, low velocity/density -> far from the card-testing seed.
        query = _profile(
            ring_id="RING-QUERY-2",
            ring_size=10,
            avg_amount=50000.0,
            max_amount=90000.0,
            merchant_category_count=1,
            velocity_score=0.0,
            graph_density=0.05,
        )
        match = matcher.match(query)
        self.assertIsNone(match)

    def test_empty_library_returns_none(self) -> None:
        matcher = FraudDNAMatcher(_FakeStore([]))
        self.assertIsNone(matcher.match(_profile()))

    def test_matcher_skips_self_match_by_ring_id(self) -> None:
        seed = _profile(ring_id="RING-QUERY")  # same ring_id as the default query profile
        matcher = FraudDNAMatcher(_FakeStore([seed]))
        match = matcher.match(_profile(ring_id="RING-QUERY"))
        self.assertIsNone(match)


if __name__ == "__main__":
    unittest.main()
