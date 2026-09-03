"""Fraud DNA extractor for FraudLens.

Fingerprints a detected ring — its GraphEvidence plus the ring's own
transactions — into a reusable FraudDNAProfile: the input to
FraudDNAMatcher's similarity search against the known-pattern library.
"""

from __future__ import annotations

import statistics
from datetime import datetime, timezone
from typing import Optional

from fraudlens.models.schemas import FraudDNAProfile, GraphEvidence, Transaction

# Ring transaction rate (txns/hour) at which velocity_score saturates to 1.0.
_VELOCITY_SATURATION_RATE = 5.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_timestamp(timestamp: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        return None


def _velocity_score(timestamps: list[datetime]) -> float:
    if len(timestamps) < 2:
        return 0.0
    span_hours = max((max(timestamps) - min(timestamps)).total_seconds() / 3600.0, 1e-6)
    rate = len(timestamps) / span_hours
    return round(min(rate / _VELOCITY_SATURATION_RATE, 1.0), 4)


def _heuristic_fraud_type(ring_size: int, avg_amount: float, velocity_score: float,
                           graph_density: float) -> str:
    """A best-effort label for a freshly extracted profile — the matcher
    refines this against the known-pattern library, but a query profile
    needs a non-empty fraud_type/modus_operandi of its own regardless of
    whether a confident library match is found."""
    if velocity_score >= 0.7 and avg_amount < 1_500:
        return "card_testing_ring"
    if graph_density >= 0.6 and ring_size >= 6:
        return "device_farm_fraud"
    if avg_amount >= 80_000 and velocity_score >= 0.4:
        return "bust_out_ring"
    if ring_size <= 3 and avg_amount >= 40_000:
        return "account_takeover_cluster"
    return "unclassified_ring"


class FraudDNAExtractor:
    """Fingerprints a detected ring into a reusable FraudDNAProfile."""

    def extract_profile(
        self, ring_transactions: list[Transaction], evidence: GraphEvidence
    ) -> FraudDNAProfile:
        if not ring_transactions:
            raise ValueError("Cannot extract a Fraud DNA profile from an empty ring")

        amounts = [t.amount for t in ring_transactions]
        avg_amount = statistics.mean(amounts)
        max_amount = max(amounts)
        merchant_category_count = len({t.merchant_category for t in ring_transactions})

        timestamps = [
            ts for ts in (_parse_timestamp(t.timestamp) for t in ring_transactions)
            if ts is not None
        ]
        velocity_score = _velocity_score(timestamps)

        fraud_type = _heuristic_fraud_type(
            evidence.ring_size, avg_amount, velocity_score, evidence.graph_density
        )
        modus_operandi = (
            f"{evidence.ring_size} accounts sharing {len(evidence.shared_devices)} device(s) "
            f"and {len(evidence.shared_ips)} IP(s); avg transaction ₹{avg_amount:,.2f}, "
            f"velocity score {velocity_score:.2f}, graph density {evidence.graph_density:.2f}."
        )
        ring_id = evidence.ring_id or f"RING-UNKNOWN-{ring_transactions[0].txn_id}"

        return FraudDNAProfile(
            ring_id=ring_id,
            ring_size=evidence.ring_size,
            shared_devices=len(evidence.shared_devices),
            shared_ips=len(evidence.shared_ips),
            avg_amount=round(avg_amount, 2),
            max_amount=round(max_amount, 2),
            merchant_category_count=merchant_category_count,
            velocity_score=velocity_score,
            graph_density=evidence.graph_density,
            fraud_type=fraud_type,
            modus_operandi=modus_operandi,
            first_detected=_now_iso(),
            description=f"Auto-extracted profile for {ring_id}: {modus_operandi}",
        )
