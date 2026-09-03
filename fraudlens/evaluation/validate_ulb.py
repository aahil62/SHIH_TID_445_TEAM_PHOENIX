"""Standalone validation against the real, published ULB Credit Card Fraud
dataset (Kaggle mlg-ulb/creditcardfraud; 284,807 real anonymized European
card transactions, 492 confirmed frauds, 0.17% fraud rate).

This is deliberately a SEPARATE model, not fraudlens.core.scoring.ml_agent
run unchanged: ULB's features are PCA components (V1-V28) plus Time and
Amount, anonymized for privacy — there's no merchant/device/IP/account-
history field at all. ml_agent's feature extractor expects real Transaction
fields (merchant_category, channel, hour-of-day, etc.) that simply don't
exist here, so there's no honest way to "plug ULB into ml_agent" without
fabricating fields the original data never had.

What this DOES prove: the same modeling approach — GradientBoostingClassifier
with class-balanced sample weights, same family and imbalance handling as
ml_agent — reaches strong precision/recall/AUC-PR on a real, independently
published, widely-cited fraud benchmark, not just our own synthetic data.
That's legitimate external validation of the methodology; it is not a claim
that ml_agent itself was trained or tested on this file.

Get the data (not committed — ~140MB, third-party licensed):
  curl -o fraudlens/data/external/creditcard_ulb.csv \
    "https://www.openml.org/data/get_csv/1673544/phpKo8OWT"

Run:
  python -m fraudlens.evaluation.validate_ulb
"""

from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Any

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_sample_weight

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "external" / "creditcard_ulb.csv"


def _load(path: Path) -> tuple[list[list[float]], list[int]]:
    X: list[list[float]] = []
    y: list[int] = []
    with path.open() as f:
        reader = csv.reader(f)
        next(reader)  # header
        for row in reader:
            *features, label = row
            X.append([float(v) for v in features])
            y.append(1 if label.strip().strip("'") == "1" else 0)
    return X, y


def run_validation(path: Path = _DEFAULT_PATH, seed: int = 42) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Download it first — see this module's docstring."
        )

    X, y = _load(path)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=seed, stratify=y,
    )

    model = GradientBoostingClassifier(
        n_estimators=150, max_depth=3, learning_rate=0.1, random_state=seed,
    )
    sample_weight = compute_sample_weight("balanced", y_train)

    t0 = time.perf_counter()
    model.fit(X_train, y_train, sample_weight=sample_weight)
    fit_seconds = time.perf_counter() - t0

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    return {
        "dataset": "ULB Credit Card Fraud (Kaggle mlg-ulb/creditcardfraud)",
        "total_rows": len(X),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "fraud_rate": sum(y) / len(y),
        "precision": round(float(precision_score(y_test, y_pred)), 4),
        "recall": round(float(recall_score(y_test, y_pred)), 4),
        "f1": round(float(f1_score(y_test, y_pred)), 4),
        "auc_pr": round(float(average_precision_score(y_test, y_proba)), 4),
        "fit_seconds": round(fit_seconds, 2),
    }


def main() -> None:
    results = run_validation()
    print(f"Dataset: {results['dataset']}")
    print(
        f"  {results['total_rows']} total rows "
        f"({results['train_rows']} train / {results['test_rows']} test), "
        f"fraud rate {results['fraud_rate']:.4%}"
    )
    print(
        f"  precision={results['precision']:.4f}  recall={results['recall']:.4f}  "
        f"f1={results['f1']:.4f}  auc_pr={results['auc_pr']:.4f}  "
        f"(fit: {results['fit_seconds']}s)"
    )


if __name__ == "__main__":
    main()
