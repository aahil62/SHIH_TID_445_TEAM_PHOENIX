"""Trained ML scoring agent for FraudLens.

A gradient-boosted classifier trained on the synthetic generator's
is_fraud_demo_label ground truth. Deliberately single-transaction and
stateless like rule_agent (no set_transactions()/build_profiles() call
needed) — the temporal/network signals already live in velocity_agent,
behavioral_agent, and graph_agent, so this agent's job is to learn
nonlinear combinations of a transaction's own static features rather than
duplicate their history-based work.

fit() must be called with labeled training data before score() produces a
real prediction; an unfitted agent returns a low-confidence placeholder
instead of raising, matching every other agent's promise to never raise
for a well-formed Transaction.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.utils.class_weight import compute_sample_weight

from fraudlens.models.schemas import AgentScore, Transaction

# Mirrors fraudlens.core.scoring.rule_agent's risky-category/location sets.
# Duplicated rather than imported so this agent's feature set stays
# self-contained and doesn't couple to rule_agent's internals.
_RISKY_MERCHANT_CATEGORIES = frozenset({
    "crypto_exchange", "gambling", "gift_cards", "jewelry",
    "luxury_goods", "money_transfer", "digital_goods",
})

_RISKY_LOCATIONS = frozenset({
    "unknown", "nigeria", "russia", "north_korea", "iran",
    "offshore", "anonymous_proxy", "tor_exit_node",
})

_NIGHT_HOURS = frozenset(range(0, 4))

_THRESHOLD_MARGIN = 50.0
_STRUCTURING_THRESHOLDS = (2000.0, 5000.0, 10000.0)

_FEATURE_NAMES = (
    "amount",
    "log_amount",
    "hour_of_day",
    "is_night_hours",
    "is_risky_merchant",
    "is_risky_location",
    "is_online_channel",
    "is_round_number",
    "is_near_threshold",
)

_UNTRAINED_SCORE = 0.0
_UNTRAINED_CONFIDENCE = 0.3
_TRAINED_CONFIDENCE = 0.85


def _parse_hour(timestamp: str) -> int | None:
    if not timestamp:
        return None
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).hour
    except (ValueError, TypeError):
        return None


def _is_near_threshold(amount: float) -> bool:
    return any(t - _THRESHOLD_MARGIN <= amount < t for t in _STRUCTURING_THRESHOLDS)


def _extract_features(txn: Transaction) -> list[float]:
    hour = _parse_hour(txn.timestamp)
    category = (txn.merchant_category or "").strip().lower()
    location = (txn.location or "").strip().lower()
    channel = (txn.channel or "").strip().lower()
    amount = max(txn.amount, 0.0)

    return [
        amount,
        math.log1p(amount),
        float(hour) if hour is not None else -1.0,
        1.0 if hour is not None and hour in _NIGHT_HOURS else 0.0,
        1.0 if category in _RISKY_MERCHANT_CATEGORIES else 0.0,
        1.0 if location in _RISKY_LOCATIONS else 0.0,
        1.0 if channel == "online" else 0.0,
        1.0 if amount > 0 and amount % 100 == 0 else 0.0,
        1.0 if _is_near_threshold(amount) else 0.0,
    ]


class MLAgent:
    """Gradient-boosted fraud classifier trained on synthetic ground truth."""

    name = "ml_agent"

    def __init__(self, random_state: int = 42) -> None:
        self._model = GradientBoostingClassifier(
            n_estimators=150,
            max_depth=3,
            learning_rate=0.1,
            random_state=random_state,
        )
        self._is_fitted = False
        self._feature_importances: dict[str, float] = {}

    def fit(self, transactions: list[Transaction]) -> None:
        """Train on labeled transactions (is_fraud_demo_label as ground truth)."""
        if not transactions:
            raise ValueError("Cannot fit MLAgent on an empty transaction list")

        X = [_extract_features(t) for t in transactions]
        y = [int(t.is_fraud_demo_label) for t in transactions]

        # The dataset is fraud-minority; weight samples so the classifier
        # doesn't just learn to always predict "normal".
        sample_weight = compute_sample_weight("balanced", y)
        self._model.fit(X, y, sample_weight=sample_weight)
        self._is_fitted = True
        self._feature_importances = dict(
            zip(_FEATURE_NAMES, (float(v) for v in self._model.feature_importances_))
        )

    def score(self, txn: Transaction) -> AgentScore:
        if not self._is_fitted:
            return AgentScore(
                agent_name=self.name,
                score=_UNTRAINED_SCORE,
                confidence=_UNTRAINED_CONFIDENCE,
                reasons=["ML model has not been trained yet"],
            )

        features = _extract_features(txn)
        proba = float(self._model.predict_proba([features])[0][1])

        return AgentScore(
            agent_name=self.name,
            score=round(proba, 4),
            confidence=_TRAINED_CONFIDENCE,
            reasons=[self._explain(proba)],
            metadata={"model": "gradient_boosting", "fraud_probability": round(proba, 4)},
        )

    def _explain(self, proba: float) -> str:
        if proba < 0.3:
            return f"Model predicts low fraud probability ({proba:.0%})"
        top_features = sorted(
            self._feature_importances.items(), key=lambda kv: kv[1], reverse=True
        )[:3]
        top_names = ", ".join(name for name, _ in top_features)
        return f"Model predicts {proba:.0%} fraud probability (top signals: {top_names})"

    @property
    def feature_importances(self) -> dict[str, float]:
        return dict(self._feature_importances)
