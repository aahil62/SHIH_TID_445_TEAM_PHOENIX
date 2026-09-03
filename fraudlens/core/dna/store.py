"""Fraud DNA library store for FraudLens.

Persists the known-pattern library as JSON (mirrors CaseEngine's
cases.json persistence) and auto-seeds it with a small set of known
fraud-ring typologies on first use, so FraudDNAMatcher has something to
match against before any ring has ever been confirmed and added.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional

from fraudlens.models.schemas import FraudDNAProfile


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seed_profiles() -> list[FraudDNAProfile]:
    now = _now_iso()
    return [
        FraudDNAProfile(
            ring_id="SEED-CARD-TESTING",
            ring_size=3,
            shared_devices=1,
            shared_ips=1,
            avg_amount=4.75,
            max_amount=9.50,
            merchant_category_count=2,
            velocity_score=0.95,
            graph_density=0.85,
            fraud_type="card_testing_ring",
            modus_operandi=(
                "Many sub-$10 transactions run in quick succession across a shared "
                "device/IP to validate stolen card numbers before a larger purchase."
            ),
            first_detected=now,
            description="Seed pattern: card-testing ring.",
        ),
        FraudDNAProfile(
            ring_id="SEED-BUST-OUT",
            ring_size=7,
            shared_devices=3,
            shared_ips=2,
            avg_amount=2400.0,
            max_amount=8900.0,
            merchant_category_count=4,
            velocity_score=0.55,
            graph_density=0.45,
            fraud_type="bust_out_ring",
            modus_operandi=(
                "Synthetic identities share devices, build credit history, then run "
                "up balances rapidly across several accounts before defaulting."
            ),
            first_detected=now,
            description="Seed pattern: bust-out fraud ring.",
        ),
        FraudDNAProfile(
            ring_id="SEED-MONEY-MULE",
            ring_size=5,
            shared_devices=2,
            shared_ips=3,
            avg_amount=1200.0,
            max_amount=3000.0,
            merchant_category_count=2,
            velocity_score=0.25,
            graph_density=0.35,
            fraud_type="money_mule_network",
            modus_operandi=(
                "Recruited mules move stolen funds through personal accounts via "
                "money-transfer/crypto merchants from a shared pool of devices/IPs."
            ),
            first_detected=now,
            description="Seed pattern: money mule network.",
        ),
        FraudDNAProfile(
            ring_id="SEED-ACCOUNT-TAKEOVER",
            ring_size=2,
            shared_devices=1,
            shared_ips=1,
            avg_amount=650.0,
            max_amount=1800.0,
            merchant_category_count=3,
            velocity_score=0.40,
            graph_density=0.60,
            fraud_type="account_takeover_cluster",
            modus_operandi=(
                "An attacker accesses a small number of compromised accounts from "
                "the same device/IP and cashes out via high-value purchases."
            ),
            first_detected=now,
            description="Seed pattern: account takeover cluster.",
        ),
        FraudDNAProfile(
            ring_id="SEED-DEVICE-FARM",
            ring_size=10,
            shared_devices=4,
            shared_ips=4,
            avg_amount=180.0,
            max_amount=900.0,
            merchant_category_count=5,
            velocity_score=0.60,
            graph_density=0.75,
            fraud_type="device_farm_fraud",
            modus_operandi=(
                "A small pool of devices/IPs is rotated across many synthetic "
                "accounts to defeat per-device and per-IP risk checks."
            ),
            first_detected=now,
            description="Seed pattern: device-farm fraud.",
        ),
    ]


class FraudDNAStore:
    """Persists the Fraud DNA library, auto-seeded on first use."""

    def __init__(self, path: str = "fraudlens/data/fraud_dna_library.json") -> None:
        self._path = path
        self._profiles: dict[str, FraudDNAProfile] = {}
        self._load_or_seed()

    def all(self) -> list[FraudDNAProfile]:
        return list(self._profiles.values())

    def get(self, ring_id: str) -> Optional[FraudDNAProfile]:
        return self._profiles.get(ring_id)

    def add(self, profile: FraudDNAProfile) -> None:
        self._profiles[profile.ring_id] = profile
        self._persist()

    def _load_or_seed(self) -> None:
        if os.path.exists(self._path):
            try:
                with open(self._path, "r") as f:
                    data = json.load(f)
                profiles = {item["ring_id"]: FraudDNAProfile(**item) for item in data}
                if profiles:
                    self._profiles = profiles
                    return
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        self._profiles = {p.ring_id: p for p in _seed_profiles()}
        self._persist()

    def _persist(self) -> None:
        directory = os.path.dirname(self._path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump([p.model_dump() for p in self._profiles.values()], f, indent=2, default=str)
