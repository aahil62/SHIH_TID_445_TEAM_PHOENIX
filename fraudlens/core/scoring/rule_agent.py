"""Rule-based scoring agent for FraudLens.

Deterministic, hand-authored heuristics: amount thresholds, risky merchant
categories, risky locations/hours, channel + amount combinations, and
suspicious amount shapes (round numbers, just-under-threshold). No learned
state, no history — every check operates on the single Transaction passed
to score().
"""

from __future__ import annotations

from datetime import datetime

from fraudlens.models.schemas import AgentScore, Transaction

# Amounts are INR (SH-FIN-01 is an RBI-context Indian fraud problem).
# Thresholds are scaled from the original USD design (~85 INR/USD) and
# rounded to figures that read naturally in Indian retail/banking terms,
# not a precise economic model of what's "risky" at each price point.
_MAJOR_AMOUNT_THRESHOLD = 400_000.0
_MINOR_AMOUNT_THRESHOLD = 150_000.0

_RISKY_MERCHANT_CATEGORIES = frozenset({
    "crypto_exchange",
    "gambling",
    "gift_cards",
    "jewelry",
    "luxury_goods",
    "money_transfer",
    "digital_goods",
})

_RISKY_LOCATIONS = frozenset({
    "unknown",
    "nigeria",
    "russia",
    "north_korea",
    "iran",
    "offshore",
    "anonymous_proxy",
    "tor_exit_node",
})

_RISKY_HOURS = frozenset(range(0, 4))  # midnight-4am, inclusive of 0..3

_ONLINE_HIGH_AMOUNT_THRESHOLD = 75_000.0

# Amounts within this many rupees of a threshold read as "just under the
# limit" — a classic structuring tell.
_STRUCTURING_MARGIN = 4_000.0
_STRUCTURING_THRESHOLDS = (_MINOR_AMOUNT_THRESHOLD, _MAJOR_AMOUNT_THRESHOLD, 800_000.0)

_CONFIDENCE = 0.9


class RuleAgent:
    """Deterministic rule-based fraud scorer."""

    name = "rule_agent"

    def score(self, txn: Transaction) -> AgentScore:
        points = 0.0
        reasons: list[str] = []

        points, reasons = self._check_amount(txn, points, reasons)
        points, reasons = self._check_merchant_category(txn, points, reasons)
        points, reasons = self._check_location(txn, points, reasons)
        points, reasons = self._check_hour(txn, points, reasons)
        points, reasons = self._check_online_high_amount(txn, points, reasons)
        points, reasons = self._check_suspicious_amount_shape(txn, points, reasons)

        score = max(0.0, min(points, 1.0))

        if not reasons:
            reasons.append("No rule violations detected")

        return AgentScore(
            agent_name=self.name,
            score=score,
            confidence=_CONFIDENCE,
            reasons=reasons,
            metadata={"rules_triggered": len(reasons) if score > 0 else 0},
        )

    @staticmethod
    def _check_amount(
        txn: Transaction, points: float, reasons: list[str]
    ) -> tuple[float, list[str]]:
        if txn.amount > _MAJOR_AMOUNT_THRESHOLD:
            points += 0.5
            reasons.append(
                f"Amount ₹{txn.amount:,.2f} exceeds major threshold "
                f"(₹{_MAJOR_AMOUNT_THRESHOLD:,.0f})"
            )
        elif txn.amount > _MINOR_AMOUNT_THRESHOLD:
            points += 0.25
            reasons.append(
                f"Amount ₹{txn.amount:,.2f} exceeds minor threshold "
                f"(₹{_MINOR_AMOUNT_THRESHOLD:,.0f})"
            )
        return points, reasons

    @staticmethod
    def _check_merchant_category(
        txn: Transaction, points: float, reasons: list[str]
    ) -> tuple[float, list[str]]:
        category = (txn.merchant_category or "").strip().lower()
        if category in _RISKY_MERCHANT_CATEGORIES:
            points += 0.3
            reasons.append(f"Risky merchant category: {category}")
        return points, reasons

    @staticmethod
    def _check_location(
        txn: Transaction, points: float, reasons: list[str]
    ) -> tuple[float, list[str]]:
        location = (txn.location or "").strip().lower()
        if location in _RISKY_LOCATIONS:
            points += 0.25
            reasons.append(f"Risky location: {txn.location}")
        return points, reasons

    @staticmethod
    def _check_hour(
        txn: Transaction, points: float, reasons: list[str]
    ) -> tuple[float, list[str]]:
        hour = _parse_hour(txn.timestamp)
        if hour is not None and hour in _RISKY_HOURS:
            points += 0.15
            reasons.append(f"Transaction occurred during high-risk hours ({hour:02d}:00)")
        return points, reasons

    @staticmethod
    def _check_online_high_amount(
        txn: Transaction, points: float, reasons: list[str]
    ) -> tuple[float, list[str]]:
        channel = (txn.channel or "").strip().lower()
        if channel == "online" and txn.amount > _ONLINE_HIGH_AMOUNT_THRESHOLD:
            points += 0.15
            reasons.append(
                f"High-value online transaction (₹{txn.amount:,.2f} via {channel})"
            )
        return points, reasons

    @staticmethod
    def _check_suspicious_amount_shape(
        txn: Transaction, points: float, reasons: list[str]
    ) -> tuple[float, list[str]]:
        amount = txn.amount

        if amount > 0 and amount % 100 == 0:
            points += 0.1
            reasons.append(f"Suspicious round-number amount (₹{amount:,.2f})")

        for threshold in _STRUCTURING_THRESHOLDS:
            if threshold - _STRUCTURING_MARGIN <= amount < threshold:
                points += 0.2
                reasons.append(
                    f"Amount ₹{amount:,.2f} sits just under the ₹{threshold:,.0f} "
                    "threshold (possible structuring)"
                )
                break

        return points, reasons


def _parse_hour(timestamp: str) -> int | None:
    """Best-effort hour-of-day extraction. Returns None for unparseable timestamps."""
    if not timestamp:
        return None
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).hour
    except (ValueError, TypeError):
        return None
