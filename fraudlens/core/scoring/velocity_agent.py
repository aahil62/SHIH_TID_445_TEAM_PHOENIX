"""Velocity-based scoring agent for FraudLens.

Looks at how a transaction fits into an account's recent activity: burst
counts within 1h/24h windows, total 24h spend, and card-testing bursts of
small transactions. Needs the account's transaction history loaded via
set_transactions() before score() has anything to reason about — without
it, every transaction reads as low-confidence unknown.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fraudlens.core.cases.account_restriction import AccountRestrictionStore
from fraudlens.models.schemas import AgentScore, Transaction

_ONE_HOUR = timedelta(hours=1)
_TWENTY_FOUR_HOURS = timedelta(hours=24)
_CARD_TESTING_WINDOW = timedelta(minutes=15)

_HOUR_COUNT_MAJOR = 5
_HOUR_COUNT_MEDIUM = 3
_HOUR_COUNT_MINOR = 2

_DAY_COUNT_MAJOR = 10
_DAY_COUNT_MINOR = 6

# Applied instead of the normal thresholds above when the account is under
# an active autonomous restriction (see account_restriction.py) — roughly
# half the normal burst tolerance, so the same transaction pattern that
# was fine yesterday trips the velocity agent today. This is the actual
# mechanism behind "the system changed how it treats this account", not
# just a label.
_RESTRICTED_HOUR_COUNT_MAJOR = 3
_RESTRICTED_HOUR_COUNT_MEDIUM = 2
_RESTRICTED_HOUR_COUNT_MINOR = 1

_RESTRICTED_DAY_COUNT_MAJOR = 5
_RESTRICTED_DAY_COUNT_MINOR = 3

# INR — scaled from the original USD design (~85 INR/USD), see
# rule_agent.py's threshold comment for the same rationale.
_DAY_SPEND_THRESHOLD = 800_000.0

_CARD_TESTING_MIN_COUNT = 3
_CARD_TESTING_MAX_AMOUNT = 800.0

_CONFIDENCE_WITH_HISTORY = 0.85
_CONFIDENCE_WITHOUT_HISTORY = 0.5

_HistoryEntry = tuple[datetime, float, str]


class VelocityAgent:
    """Scores a transaction against its account's recent transaction velocity."""

    name = "velocity_agent"

    def __init__(self, restriction_store: Optional[AccountRestrictionStore] = None) -> None:
        self._history_by_account: dict[str, list[_HistoryEntry]] = {}
        self._has_history = False
        self._restriction_store = restriction_store

    def set_transactions(self, transactions: list[Transaction]) -> None:
        """Load lookback history for velocity checks. Call before score()."""
        history: dict[str, list[_HistoryEntry]] = {}
        for t in transactions:
            ts = _parse_timestamp(t.timestamp)
            if ts is None:
                continue
            history.setdefault(t.account_id, []).append((ts, t.amount, t.txn_id))
        for entries in history.values():
            entries.sort(key=lambda e: e[0])
        self._history_by_account = history
        self._has_history = True

    def score(self, txn: Transaction) -> AgentScore:
        if not self._has_history:
            return AgentScore(
                agent_name=self.name,
                score=0.0,
                confidence=_CONFIDENCE_WITHOUT_HISTORY,
                reasons=["No transaction history available for velocity analysis"],
            )

        now = _parse_timestamp(txn.timestamp)
        if now is None:
            return AgentScore(
                agent_name=self.name,
                score=0.0,
                confidence=_CONFIDENCE_WITHOUT_HISTORY,
                reasons=["Transaction timestamp could not be parsed; velocity checks skipped"],
            )

        entries = [
            (ts, amount)
            for ts, amount, txn_id in self._history_by_account.get(txn.account_id, [])
            if txn_id != txn.txn_id
        ]

        restricted = self._restriction_store is not None and self._restriction_store.is_restricted(
            txn.account_id
        )

        points = 0.0
        reasons: list[str] = []

        points, reasons = self._check_hour_count(now, entries, points, reasons, restricted)
        points, reasons = self._check_day_count(now, entries, points, reasons, restricted)
        points, reasons = self._check_day_spend(now, txn.amount, entries, points, reasons)
        points, reasons = self._check_card_testing(now, txn.amount, entries, points, reasons)

        score = max(0.0, min(points, 1.0))

        if restricted:
            reasons.insert(
                0,
                "Account is under a system-imposed velocity restriction "
                "(auto-applied after a prior high-confidence hold) — burst "
                "thresholds are tightened for this account until an analyst reviews it",
            )
        elif not reasons:
            reasons.append("No velocity anomalies detected")

        return AgentScore(
            agent_name=self.name,
            score=score,
            confidence=_CONFIDENCE_WITH_HISTORY,
            reasons=reasons,
            metadata={"history_size": len(entries)},
        )

    @staticmethod
    def _check_hour_count(
        now: datetime,
        entries: list[tuple[datetime, float]],
        points: float,
        reasons: list[str],
        restricted: bool = False,
    ) -> tuple[float, list[str]]:
        major = _RESTRICTED_HOUR_COUNT_MAJOR if restricted else _HOUR_COUNT_MAJOR
        medium = _RESTRICTED_HOUR_COUNT_MEDIUM if restricted else _HOUR_COUNT_MEDIUM
        minor = _RESTRICTED_HOUR_COUNT_MINOR if restricted else _HOUR_COUNT_MINOR

        count = 1 + sum(1 for ts, _ in entries if now - _ONE_HOUR <= ts <= now)
        if count >= major:
            points += 0.45
            reasons.append(f"{count} transactions in the last hour (severe burst)")
        elif count >= medium:
            points += 0.3
            reasons.append(f"{count} transactions in the last hour")
        elif count >= minor:
            points += 0.15
            reasons.append(f"{count} transactions in the last hour")
        return points, reasons

    @staticmethod
    def _check_day_count(
        now: datetime,
        entries: list[tuple[datetime, float]],
        points: float,
        reasons: list[str],
        restricted: bool = False,
    ) -> tuple[float, list[str]]:
        major = _RESTRICTED_DAY_COUNT_MAJOR if restricted else _DAY_COUNT_MAJOR
        minor = _RESTRICTED_DAY_COUNT_MINOR if restricted else _DAY_COUNT_MINOR

        count = 1 + sum(1 for ts, _ in entries if now - _TWENTY_FOUR_HOURS <= ts <= now)
        if count >= major:
            points += 0.3
            reasons.append(f"{count} transactions in the last 24 hours")
        elif count >= minor:
            points += 0.15
            reasons.append(f"{count} transactions in the last 24 hours")
        return points, reasons

    @staticmethod
    def _check_day_spend(
        now: datetime,
        current_amount: float,
        entries: list[tuple[datetime, float]],
        points: float,
        reasons: list[str],
    ) -> tuple[float, list[str]]:
        total = current_amount + sum(
            amount for ts, amount in entries if now - _TWENTY_FOUR_HOURS <= ts <= now
        )
        if total > _DAY_SPEND_THRESHOLD:
            points += 0.3
            reasons.append(f"Total 24h spend ₹{total:,.2f} exceeds ₹{_DAY_SPEND_THRESHOLD:,.0f}")
        return points, reasons

    @staticmethod
    def _check_card_testing(
        now: datetime,
        current_amount: float,
        entries: list[tuple[datetime, float]],
        points: float,
        reasons: list[str],
    ) -> tuple[float, list[str]]:
        small_in_window = [
            amount
            for ts, amount in entries
            if now - _CARD_TESTING_WINDOW <= ts <= now and amount < _CARD_TESTING_MAX_AMOUNT
        ]
        if current_amount < _CARD_TESTING_MAX_AMOUNT:
            small_in_window.append(current_amount)

        if len(small_in_window) >= _CARD_TESTING_MIN_COUNT:
            points += 0.4
            minutes = int(_CARD_TESTING_WINDOW.total_seconds() // 60)
            reasons.append(
                f"Card-testing pattern: {len(small_in_window)} rapid transactions under "
                f"₹{_CARD_TESTING_MAX_AMOUNT:,.0f} within {minutes} minutes"
            )
        return points, reasons


def _parse_timestamp(timestamp: str) -> datetime | None:
    """Best-effort timestamp parsing. Naive timestamps are assumed UTC so
    comparisons against other transactions never raise. Returns None for
    unparseable timestamps."""
    if not timestamp:
        return None
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
