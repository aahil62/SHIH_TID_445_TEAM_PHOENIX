"""Fraud DNA matcher for FraudLens.

Similarity search over the known-pattern library: normalizes each
profile's numeric features onto comparable [0, 1] scales (raw rupee
amounts would otherwise dominate a plain distance metric) and returns the
closest library profile, or None if nothing clears the confidence
threshold.
"""

from __future__ import annotations

import math
from typing import Optional, Protocol

from fraudlens.models.schemas import FraudDNAMatch, FraudDNAProfile

_DEFAULT_SIMILARITY_THRESHOLD = 0.55

# Log-scale references so avg/max amounts read as increasingly similar the
# further apart they get, rather than a linear scale where a ₹4,000 gap
# near zero counts the same as a ₹4,000 gap near ₹8,00,000. Scaled to the
# same INR magnitude as the seed profiles in store.py and the thresholds
# in rule_agent.py/velocity_agent.py — these three must move together, or
# a ring's amounts and the library's amounts stop being comparable.
_AMOUNT_LOG_SCALE = math.log1p(400_000.0)
_MAX_AMOUNT_LOG_SCALE = math.log1p(800_000.0)
_RING_SIZE_SCALE = 10.0
_CATEGORY_COUNT_SCALE = 5.0


class ProfileLibrary(Protocol):
    def all(self) -> list[FraudDNAProfile]: ...


def _feature_vector(profile: FraudDNAProfile) -> list[float]:
    return [
        min(profile.ring_size / _RING_SIZE_SCALE, 1.0),
        min(math.log1p(max(profile.avg_amount, 0.0)) / _AMOUNT_LOG_SCALE, 1.0),
        min(math.log1p(max(profile.max_amount, 0.0)) / _MAX_AMOUNT_LOG_SCALE, 1.0),
        min(profile.merchant_category_count / _CATEGORY_COUNT_SCALE, 1.0),
        max(0.0, min(profile.velocity_score, 1.0)),
        max(0.0, min(profile.graph_density, 1.0)),
    ]


def _similarity(a: FraudDNAProfile, b: FraudDNAProfile) -> float:
    va, vb = _feature_vector(a), _feature_vector(b)
    distance = math.sqrt(sum((x - y) ** 2 for x, y in zip(va, vb)))
    max_distance = math.sqrt(len(va))
    return max(0.0, 1.0 - distance / max_distance)


def _recommendation(fraud_type: str, similarity: float) -> str:
    label = fraud_type.replace("_", " ")
    if similarity >= 0.85:
        return (
            f"Very high confidence match to a known {label} pattern — escalate to "
            "fraud operations and cross-reference all connected accounts."
        )
    if similarity >= 0.70:
        return (
            f"Strong match to a known {label} pattern — recommend priority analyst "
            "review with the linked ring in scope."
        )
    return f"Possible match to a known {label} pattern — flag for analyst review."


class FraudDNAMatcher:
    """Finds the closest known fraud pattern for a freshly extracted ring profile."""

    def __init__(self, store: ProfileLibrary, threshold: float = _DEFAULT_SIMILARITY_THRESHOLD) -> None:
        self._store = store
        self._threshold = threshold

    def match(self, profile: FraudDNAProfile) -> Optional[FraudDNAMatch]:
        best: Optional[FraudDNAProfile] = None
        best_similarity = -1.0
        for candidate in self._store.all():
            if candidate.ring_id == profile.ring_id:
                continue
            similarity = _similarity(profile, candidate)
            if similarity > best_similarity:
                best_similarity, best = similarity, candidate

        if best is None or best_similarity < self._threshold:
            return None

        return FraudDNAMatch(
            matched_ring_id=best.ring_id,
            similarity_score=round(best_similarity, 4),
            fraud_type=best.fraud_type,
            modus_operandi=best.modus_operandi,
            recommendation=_recommendation(best.fraud_type, best_similarity),
            matched_profile=best,
            description=(
                f"{best_similarity:.0%} similarity match to known '{best.fraud_type}' "
                f"pattern ({best.ring_id})."
            ),
        )
