"""Synthetic transaction generator for FraudLens.

Produces a labeled dataset of normal and fraudulent transactions. Every
transaction carries ground truth (is_fraud_demo_label, fraud_pattern_type)
— this is what the benchmark suite and the ML agent train against later.
Scoring agents never read these two fields at inference time.

Fraud patterns generated:
  - high_amount     : single transaction far above normal thresholds
  - risky_merchant  : transaction at a high-risk merchant category
  - odd_hour        : moderate/high amount transaction between 12am-4am
  - card_testing    : burst of tiny (<$10) transactions on one account
  - high_velocity   : burst of many transactions on one account within 1h
  - fraud_ring      : multiple accounts sharing devices/IPs transacting in
                      a short window — feature/graph-behavioral's ring
                      detector needs clusters like this to exist in the data
"""

from __future__ import annotations

import json
import os
import random
from datetime import datetime, timedelta, timezone

from fraudlens.models.schemas import Transaction

# ── Reference data ───────────────────────────────────────────────────────

_NORMAL_MERCHANT_CATEGORIES = [
    "groceries", "electronics", "restaurants", "gas_station", "pharmacy",
    "clothing", "entertainment", "travel", "utilities", "subscription",
    "home_improvement", "education",
]

# Matches fraudlens.core.scoring.rule_agent's risky-category list so the
# rule agent actually reacts to this data.
_RISKY_MERCHANT_CATEGORIES = [
    "crypto_exchange", "gambling", "gift_cards", "jewelry",
    "luxury_goods", "money_transfer", "digital_goods",
]

_NORMAL_LOCATIONS = ["us", "uk", "ca", "de", "fr", "in", "au", "jp", "br", "mx"]

# Matches fraudlens.core.scoring.rule_agent's risky-location list.
_RISKY_LOCATIONS = [
    "nigeria", "russia", "north_korea", "iran", "offshore",
    "anonymous_proxy", "tor_exit_node", "unknown",
]

_CHANNELS = ["online", "in_store", "mobile_app", "atm"]

_AMOUNT_RANGES: dict[str, tuple[float, float]] = {
    "groceries": (10, 150),
    "electronics": (50, 2000),
    "restaurants": (10, 120),
    "gas_station": (20, 90),
    "pharmacy": (5, 80),
    "clothing": (20, 300),
    "entertainment": (10, 150),
    "travel": (100, 3000),
    "utilities": (30, 250),
    "subscription": (5, 60),
    "home_improvement": (20, 1000),
    "education": (50, 2000),
    "crypto_exchange": (200, 8000),
    "gambling": (50, 3000),
    "gift_cards": (25, 2000),
    "jewelry": (100, 6000),
    "luxury_goods": (200, 9000),
    "money_transfer": (100, 5000),
    "digital_goods": (10, 500),
}

FRAUD_PATTERN_TYPES = (
    "high_amount",
    "risky_merchant",
    "odd_hour",
    "card_testing",
    "high_velocity",
    "fraud_ring",
)


# ── Small helpers ─────────────────────────────────────────────────────────

def _rand_id(rng: random.Random, prefix: str, length: int = 8) -> str:
    return f"{prefix}-{''.join(rng.choices('0123456789ABCDEF', k=length))}"


def _new_txn_id(rng: random.Random) -> str:
    return f"TXN-{rng.getrandbits(64):016X}"


def _rand_ip(rng: random.Random) -> str:
    return f"{rng.randint(1, 223)}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _random_timestamp(rng: random.Random, start: datetime, end: datetime) -> datetime:
    delta_seconds = max(int((end - start).total_seconds()), 0)
    return start + timedelta(seconds=rng.randint(0, delta_seconds))


def _daytime_timestamp(rng: random.Random, day: datetime) -> datetime:
    """Normal customer activity skews toward waking hours, 7am-10pm."""
    return day.replace(
        hour=rng.randint(7, 22), minute=rng.randint(0, 59), second=rng.randint(0, 59)
    )


def _odd_hour_timestamp(rng: random.Random, day: datetime) -> datetime:
    return day.replace(
        hour=rng.randint(0, 3), minute=rng.randint(0, 59), second=rng.randint(0, 59)
    )


# ── Individual transaction builders ───────────────────────────────────────

def make_normal_transaction(
    rng: random.Random,
    account_id: str,
    day: datetime,
    device_id: str | None = None,
    ip_address: str | None = None,
) -> Transaction:
    category = rng.choice(_NORMAL_MERCHANT_CATEGORIES)
    low, high = _AMOUNT_RANGES[category]
    return Transaction(
        txn_id=_new_txn_id(rng),
        account_id=account_id,
        amount=round(rng.uniform(low, high), 2),
        merchant_id=_rand_id(rng, "MER"),
        merchant_category=category,
        device_id=device_id or _rand_id(rng, "DEV"),
        ip_address=ip_address or _rand_ip(rng),
        timestamp=_iso(_daytime_timestamp(rng, day)),
        location=rng.choice(_NORMAL_LOCATIONS),
        channel=rng.choice(_CHANNELS),
        is_fraud_demo_label=False,
        fraud_pattern_type="normal",
    )


def make_high_amount_fraud(rng: random.Random, account_id: str, day: datetime) -> Transaction:
    category = rng.choice(_NORMAL_MERCHANT_CATEGORIES + _RISKY_MERCHANT_CATEGORIES)
    # Half the time land just under the $5000 major-threshold rule (a
    # structuring tell), the rest clearly over it.
    amount = round(
        rng.uniform(4950, 4999.99) if rng.random() < 0.5 else rng.uniform(5001, 15000), 2
    )
    return Transaction(
        txn_id=_new_txn_id(rng),
        account_id=account_id,
        amount=amount,
        merchant_id=_rand_id(rng, "MER"),
        merchant_category=category,
        device_id=_rand_id(rng, "DEV"),
        ip_address=_rand_ip(rng),
        timestamp=_iso(_random_timestamp(rng, day, day + timedelta(hours=23, minutes=59))),
        location=rng.choice(_NORMAL_LOCATIONS + _RISKY_LOCATIONS),
        channel=rng.choice(_CHANNELS),
        is_fraud_demo_label=True,
        fraud_pattern_type="high_amount",
    )


def make_risky_merchant_fraud(rng: random.Random, account_id: str, day: datetime) -> Transaction:
    category = rng.choice(_RISKY_MERCHANT_CATEGORIES)
    low, high = _AMOUNT_RANGES[category]
    return Transaction(
        txn_id=_new_txn_id(rng),
        account_id=account_id,
        amount=round(rng.uniform(low, high), 2),
        merchant_id=_rand_id(rng, "MER"),
        merchant_category=category,
        device_id=_rand_id(rng, "DEV"),
        ip_address=_rand_ip(rng),
        timestamp=_iso(_random_timestamp(rng, day, day + timedelta(hours=23, minutes=59))),
        location=rng.choice(_NORMAL_LOCATIONS + _RISKY_LOCATIONS),
        channel=rng.choice(_CHANNELS),
        is_fraud_demo_label=True,
        fraud_pattern_type="risky_merchant",
    )


def make_odd_hour_fraud(rng: random.Random, account_id: str, day: datetime) -> Transaction:
    category = rng.choice(_NORMAL_MERCHANT_CATEGORIES + _RISKY_MERCHANT_CATEGORIES)
    low, high = _AMOUNT_RANGES[category]
    return Transaction(
        txn_id=_new_txn_id(rng),
        account_id=account_id,
        amount=round(rng.uniform(max(low, 300), max(high, 400)), 2),
        merchant_id=_rand_id(rng, "MER"),
        merchant_category=category,
        device_id=_rand_id(rng, "DEV"),
        ip_address=_rand_ip(rng),
        timestamp=_iso(_odd_hour_timestamp(rng, day)),
        location=rng.choice(_NORMAL_LOCATIONS + _RISKY_LOCATIONS),
        channel="online",
        is_fraud_demo_label=True,
        fraud_pattern_type="odd_hour",
    )


def make_card_testing_burst(rng: random.Random, account_id: str, day: datetime) -> list[Transaction]:
    device_id = _rand_id(rng, "DEV")
    ip_address = _rand_ip(rng)
    count = rng.randint(3, 6)
    start = _random_timestamp(rng, day, day + timedelta(hours=20))

    txns = []
    elapsed = timedelta()
    for _ in range(count):
        elapsed += timedelta(minutes=rng.uniform(0.3, 2.0))
        txns.append(Transaction(
            txn_id=_new_txn_id(rng),
            account_id=account_id,
            amount=round(rng.uniform(0.5, 9.5), 2),
            merchant_id=_rand_id(rng, "MER"),
            merchant_category=rng.choice(_NORMAL_MERCHANT_CATEGORIES + ["digital_goods"]),
            device_id=device_id,
            ip_address=ip_address,
            timestamp=_iso(start + elapsed),
            location=rng.choice(_NORMAL_LOCATIONS),
            channel="online",
            is_fraud_demo_label=True,
            fraud_pattern_type="card_testing",
        ))
    return txns


def make_high_velocity_burst(rng: random.Random, account_id: str, day: datetime) -> list[Transaction]:
    device_id = _rand_id(rng, "DEV")
    ip_address = _rand_ip(rng)
    count = rng.randint(6, 12)
    start = _random_timestamp(rng, day, day + timedelta(hours=20))

    txns = []
    elapsed = timedelta()
    for _ in range(count):
        elapsed += timedelta(minutes=rng.uniform(1, 8))
        category = rng.choice(_NORMAL_MERCHANT_CATEGORIES + _RISKY_MERCHANT_CATEGORIES)
        low, high = _AMOUNT_RANGES[category]
        txns.append(Transaction(
            txn_id=_new_txn_id(rng),
            account_id=account_id,
            amount=round(rng.uniform(low, high), 2),
            merchant_id=_rand_id(rng, "MER"),
            merchant_category=category,
            device_id=device_id,
            ip_address=ip_address,
            timestamp=_iso(start + elapsed),
            location=rng.choice(_NORMAL_LOCATIONS),
            channel=rng.choice(_CHANNELS),
            is_fraud_demo_label=True,
            fraud_pattern_type="high_velocity",
        ))
    return txns


def make_fraud_ring(rng: random.Random, ring_index: int, day: datetime) -> list[Transaction]:
    """Multiple accounts sharing a small pool of devices/IPs, transacting
    in a short window — the graph signal feature/graph-behavioral's ring
    detector looks for."""
    num_accounts = rng.randint(4, 6)
    account_ids = [f"ACC-RING{ring_index:02d}-{i:02d}" for i in range(num_accounts)]
    shared_devices = [_rand_id(rng, "DEV") for _ in range(max(2, num_accounts // 2))]
    shared_ips = [_rand_ip(rng) for _ in range(max(2, num_accounts // 2))]
    start = _random_timestamp(rng, day, day + timedelta(hours=18))

    txns = []
    for account_id in account_ids:
        for _ in range(rng.randint(2, 4)):
            category = rng.choice(_RISKY_MERCHANT_CATEGORIES)
            low, high = _AMOUNT_RANGES[category]
            txns.append(Transaction(
                txn_id=_new_txn_id(rng),
                account_id=account_id,
                amount=round(rng.uniform(low, high), 2),
                merchant_id=_rand_id(rng, "MER"),
                merchant_category=category,
                device_id=rng.choice(shared_devices),
                ip_address=rng.choice(shared_ips),
                timestamp=_iso(start + timedelta(minutes=rng.uniform(0, 240))),
                location=rng.choice(_RISKY_LOCATIONS + _NORMAL_LOCATIONS),
                channel="online",
                is_fraud_demo_label=True,
                fraud_pattern_type="fraud_ring",
            ))
    return txns


# ── Full dataset ───────────────────────────────────────────────────────────

def generate_synthetic_transactions(
    num_normal: int = 700,
    num_high_amount: int = 40,
    num_risky_merchant: int = 40,
    num_odd_hour: int = 30,
    num_card_testing_bursts: int = 15,
    num_high_velocity_bursts: int = 12,
    num_fraud_rings: int = 4,
    seed: int | None = 42,
) -> list[Transaction]:
    """Build a labeled synthetic transaction dataset.

    Ground truth (is_fraud_demo_label, fraud_pattern_type) is set on every
    transaction for benchmarking and ML training — scoring agents never
    read these fields at inference time. `seed` makes the dataset
    reproducible; pass None for non-deterministic generation.
    """
    rng = random.Random(seed)
    window_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(days=30)

    def _random_day() -> datetime:
        return window_start + timedelta(days=rng.randint(0, 29))

    def _random_account() -> str:
        return f"ACC-{rng.randint(1, 300):05d}"

    transactions: list[Transaction] = []

    for _ in range(num_normal):
        transactions.append(make_normal_transaction(rng, _random_account(), _random_day()))

    for _ in range(num_high_amount):
        transactions.append(make_high_amount_fraud(rng, _random_account(), _random_day()))

    for _ in range(num_risky_merchant):
        transactions.append(make_risky_merchant_fraud(rng, _random_account(), _random_day()))

    for _ in range(num_odd_hour):
        transactions.append(make_odd_hour_fraud(rng, _random_account(), _random_day()))

    for _ in range(num_card_testing_bursts):
        transactions.extend(make_card_testing_burst(rng, _random_account(), _random_day()))

    for _ in range(num_high_velocity_bursts):
        transactions.extend(make_high_velocity_burst(rng, _random_account(), _random_day()))

    for ring_index in range(num_fraud_rings):
        transactions.extend(make_fraud_ring(rng, ring_index, _random_day()))

    rng.shuffle(transactions)
    return transactions


def save_transactions(transactions: list[Transaction], path: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w") as f:
        json.dump([t.model_dump() for t in transactions], f, indent=2)


if __name__ == "__main__":
    dataset = generate_synthetic_transactions()
    output_path = os.path.join(os.path.dirname(__file__), "synthetic_transactions.json")
    save_transactions(dataset, output_path)
    fraud_count = sum(1 for t in dataset if t.is_fraud_demo_label)
    print(f"Generated {len(dataset)} transactions ({fraud_count} labeled fraud) -> {output_path}")
