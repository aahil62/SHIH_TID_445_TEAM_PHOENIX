"""Analyst account store — persists to JSON like FraudDNAStore, auto-seeded
with a couple of real accounts on first use so the console is usable
immediately, without requiring signup before anyone can log in.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional

from fraudlens.core.auth.security import hash_password, verify_password
from fraudlens.models.schemas import AnalystAccount


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seed_accounts() -> list[AnalystAccount]:
    now = _now_iso()
    return [
        AnalystAccount(
            username="asharma",
            display_name="A. Sharma",
            password_hash=hash_password("fraudlens123"),
            created_at=now,
        ),
        AnalystAccount(
            username="riyer",
            display_name="R. Iyer",
            password_hash=hash_password("fraudlens123"),
            created_at=now,
        ),
    ]


class AnalystStore:
    def __init__(self, path: str = "fraudlens/data/analysts.json") -> None:
        self._path = path
        self._accounts: dict[str, AnalystAccount] = {}
        self._load_or_seed()

    def get(self, username: str) -> Optional[AnalystAccount]:
        return self._accounts.get(username)

    def create(self, username: str, display_name: str, password: str) -> AnalystAccount:
        if username in self._accounts:
            raise ValueError(f"Username {username!r} is already taken")
        account = AnalystAccount(
            username=username,
            display_name=display_name,
            password_hash=hash_password(password),
            created_at=_now_iso(),
        )
        self._accounts[username] = account
        self._persist()
        return account

    def verify(self, username: str, password: str) -> Optional[AnalystAccount]:
        account = self._accounts.get(username)
        if account is None:
            return None
        if not verify_password(password, account.password_hash):
            return None
        return account

    def _load_or_seed(self) -> None:
        if os.path.exists(self._path):
            try:
                with open(self._path, "r") as f:
                    data = json.load(f)
                accounts = {item["username"]: AnalystAccount(**item) for item in data}
                if accounts:
                    self._accounts = accounts
                    return
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        self._accounts = {a.username: a for a in _seed_accounts()}
        self._persist()

    def _persist(self) -> None:
        directory = os.path.dirname(self._path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump([a.model_dump() for a in self._accounts.values()], f, indent=2, default=str)
