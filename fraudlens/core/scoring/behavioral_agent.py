"""Behavioral scoring agent for FraudLens.

Compares a transaction against its own account's baseline — built from
build_profiles(transactions) — rather than global norms: amount vs. the
account's historical average, novel merchant category/location/channel/
device, and unusual hour-of-day via a z-score against the account's own
transaction-hour history.

build_profiles() is typically called once over a whole batch (which may
include the transaction that will later be scored), so each account's
history excludes the transaction currently being scored by txn_id —
otherwise a transaction's own amount/device/category would always count
as "already seen" and dilute its own anomaly signal.
"""

from __future__ import annotations

import statistics
from datetime import datetime
from typing import Any, NamedTuple, Optional

from fraudlens.models.schemas import AgentScore, Transaction

_MIN_HISTORY_FOR_SCORING = 2
_THIN_HISTORY_SCORE = 0.1
_THIN_HISTORY_CONFIDENCE = 0.4

_AMOUNT_RATIO_MAJOR = 5.0
_AMOUNT_RATIO_MINOR = 3.0

_HOUR_Z_MAJOR = 3.0
_HOUR_Z_MINOR = 2.0

_QUIET_SCORE = 0.05
_CONFIDENT_HISTORY_SIZE = 5


class _Entry(NamedTuple):
    txn_id: str
    amount: float
    category: str
    location: str
    channel: str
    device_id: str
    hour: Optional[int]


def _parse_hour(timestamp: str) -> Optional[int]:
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).hour
    except (ValueError, TypeError, AttributeError):
        return None


class BehavioralAgent:
    """Scores transactions against the account's own historical baseline."""

    name = "behavioral_agent"

    def __init__(self) -> None:
        self._entries_by_account: dict[str, list[_Entry]] = {}

    def build_profiles(self, transactions: list[Transaction]) -> None:
        """Build per-account baselines: average amount, seen merchant
        categories/locations/channels/devices, and transaction hours."""
        entries_by_account: dict[str, list[_Entry]] = {}
        for txn in transactions:
            entries_by_account.setdefault(txn.account_id, []).append(
                _Entry(
                    txn_id=txn.txn_id,
                    amount=txn.amount,
                    category=txn.merchant_category,
                    location=txn.location,
                    channel=txn.channel,
                    device_id=txn.device_id,
                    hour=_parse_hour(txn.timestamp),
                )
            )
        self._entries_by_account = entries_by_account

    def score(self, txn: Transaction) -> AgentScore:
        all_entries = self._entries_by_account.get(txn.account_id, [])
        history = [e for e in all_entries if e.txn_id != txn.txn_id]

        if len(history) < _MIN_HISTORY_FOR_SCORING:
            return AgentScore(
                agent_name=self.name,
                score=_THIN_HISTORY_SCORE,
                confidence=_THIN_HISTORY_CONFIDENCE,
                reasons=["Insufficient transaction history for this account"],
                metadata={"txn_count": len(history)},
            )

        reasons: list[str] = []
        signal_scores: list[float] = []
        metadata: dict[str, Any] = {"txn_count": len(history)}

        amounts = [e.amount for e in history]
        avg = statistics.mean(amounts)
        if avg > 0:
            ratio = txn.amount / avg
            metadata["amount_ratio"] = round(ratio, 2)
            if ratio >= _AMOUNT_RATIO_MAJOR:
                signal_scores.append(0.85)
                reasons.append(
                    f"Amount is {ratio:.1f}x the account's average (₹{avg:.2f})"
                )
            elif ratio >= _AMOUNT_RATIO_MINOR:
                signal_scores.append(0.5)
                reasons.append(
                    f"Amount is {ratio:.1f}x the account's average (₹{avg:.2f})"
                )

        categories = {e.category for e in history}
        if txn.merchant_category not in categories:
            signal_scores.append(0.4)
            reasons.append(f"New merchant category for this account: {txn.merchant_category}")

        locations = {e.location for e in history if e.location}
        if txn.location and txn.location not in locations:
            signal_scores.append(0.4)
            reasons.append(f"New location for this account: {txn.location}")

        channels = {e.channel for e in history}
        if txn.channel not in channels:
            signal_scores.append(0.35)
            reasons.append(f"New channel for this account: {txn.channel}")

        devices = {e.device_id for e in history}
        if txn.device_id not in devices:
            signal_scores.append(0.45)
            reasons.append(f"New device for this account: {txn.device_id}")

        hours = [e.hour for e in history if e.hour is not None]
        hour = _parse_hour(txn.timestamp)
        if hour is not None and len(hours) >= _MIN_HISTORY_FOR_SCORING:
            mean = statistics.mean(hours)
            stdev = statistics.pstdev(hours)
            if stdev > 0:
                z = abs(hour - mean) / stdev
                metadata["hour_z_score"] = round(z, 2)
                if z >= _HOUR_Z_MAJOR:
                    signal_scores.append(0.6)
                    reasons.append(
                        f"Unusual transaction hour ({hour}:00), {z:.1f} std devs from account norm"
                    )
                elif z >= _HOUR_Z_MINOR:
                    signal_scores.append(0.35)
                    reasons.append(f"Somewhat unusual transaction hour ({hour}:00)")
            elif hour != mean:
                # No historical variance at all — any deviation is notable.
                signal_scores.append(0.5)
                reasons.append(
                    f"Transaction hour ({hour}:00) differs from account's consistent history"
                )

        score = max(signal_scores) if signal_scores else _QUIET_SCORE
        confidence = 0.8 if len(history) >= _CONFIDENT_HISTORY_SIZE else 0.6

        return AgentScore(
            agent_name=self.name,
            score=round(min(score, 1.0), 4),
            confidence=confidence,
            reasons=reasons,
            metadata=metadata,
        )
