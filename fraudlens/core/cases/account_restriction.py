"""Autonomous account-level velocity restriction — the second half of
"bounded autonomous action" alongside auto-hold (see autonomous_action.py).

Auto-holding a single case is a label on one transaction. This module is a
real, measurable consequence that follows an account forward in time:
when a case clears every corroborating-signal threshold and gets held,
its account is placed under a temporary velocity restriction —
VelocityAgent checks this store on every future score() call for that
account and applies materially tighter burst thresholds while it's
active. Nothing here claims to block real money; it changes how the
system's own agents treat the account going forward, which is a genuine
cross-agent effect (the graph/DNA agents' finding on one transaction
changes the velocity agent's behavior on the next), not just a wider
flag.

Always reversible: releasing a restriction requires a human action
(currently: the moment an analyst records any decision on the
case that triggered it — see DecisionWorkflow.submit_decision), logged as
its own audit event, exactly like the auto-hold reversal pattern.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional

from fraudlens.models.schemas import AccountRestriction


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AccountRestrictionStore:
    def __init__(self, path: str = "fraudlens/data/account_restrictions.json") -> None:
        self._path = path
        self._restrictions: dict[str, AccountRestriction] = {}
        self._load()

    def is_restricted(self, account_id: str) -> bool:
        r = self._restrictions.get(account_id)
        return r is not None and r.is_active

    def get(self, account_id: str) -> Optional[AccountRestriction]:
        return self._restrictions.get(account_id)

    def restrict(self, account_id: str, reason_txn_id: str, reason_case_id: str) -> AccountRestriction:
        """Idempotent — an already-restricted account stays under its
        original restriction rather than being re-stamped on every
        re-analysis of the same or another case for the same account."""
        existing = self._restrictions.get(account_id)
        if existing is not None and existing.is_active:
            return existing
        restriction = AccountRestriction(
            account_id=account_id,
            reason_txn_id=reason_txn_id,
            reason_case_id=reason_case_id,
            applied_at=_now_iso(),
        )
        self._restrictions[account_id] = restriction
        self._persist()
        return restriction

    def release(self, account_id: str, released_by: str) -> Optional[AccountRestriction]:
        existing = self._restrictions.get(account_id)
        if existing is None or not existing.is_active:
            return None
        released = existing.model_copy(update={"released_at": _now_iso(), "released_by": released_by})
        self._restrictions[account_id] = released
        self._persist()
        return released

    def all(self) -> list[AccountRestriction]:
        return list(self._restrictions.values())

    def _load(self) -> None:
        self._restrictions = {}
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r") as f:
                data = json.load(f)
            for item in data:
                r = AccountRestriction(**item)
                self._restrictions[r.account_id] = r
        except (json.JSONDecodeError, KeyError, TypeError):
            self._restrictions = {}

    def _persist(self) -> None:
        directory = os.path.dirname(self._path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump([r.model_dump() for r in self._restrictions.values()], f, indent=2, default=str)
