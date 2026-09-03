"""Benchmark suite for FraudLens scoring agents.

Runs every scoring agent — and the ensemble combining them — against a
held-out test split of the synthetic dataset, reporting precision,
recall, F1, AUC-PR, and per-transaction latency. Feeds the team's Results
slide and the UI's model-performance panel, so these are real measured
numbers, not placeholders.

Train/test methodology:
  - ml_agent is fit ONLY on the train split's features and labels — the
    standard supervised-learning split, no leakage.
  - velocity_agent, behavioral_agent, and graph_agent are given the full
    dataset as context (set_transactions / build_profiles / build_index).
    This isn't label leakage: none of those calls touch
    is_fraud_demo_label, only transactional metadata (account, device,
    ip, timestamp, amount). It mirrors production reality, where a
    velocity check or ring detector has access to an account's full
    transaction history, not a train/test partition of it.
  - rule_agent is stateless and needs no setup.

All agents and the ensemble are then scored transaction-by-transaction
on the test split only — those are the numbers reported.
"""

from __future__ import annotations

import json
import os
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sklearn.metrics import average_precision_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split

from fraudlens.core.scoring.behavioral_agent import BehavioralAgent
from fraudlens.core.scoring.ensemble import EnsembleScorer
from fraudlens.core.scoring.graph_agent import GraphAgent
from fraudlens.core.scoring.ml_agent import MLAgent
from fraudlens.core.scoring.rule_agent import RuleAgent
from fraudlens.core.scoring.velocity_agent import VelocityAgent
from fraudlens.data.synthetic_generator import generate_synthetic_transactions
from fraudlens.models.schemas import Transaction

_DEFAULT_TEST_SIZE = 0.2
_DEFAULT_SEED = 42
_DEFAULT_THRESHOLD = 0.5
_DEFAULT_OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "benchmark_results.json"
)


def _compute_metrics(y_true: list[int], y_scores: list[float], threshold: float) -> dict[str, float]:
    y_pred = [1 if s >= threshold else 0 for s in y_scores]
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", zero_division=0
    )
    auc_pr = average_precision_score(y_true, y_scores) if len(set(y_true)) > 1 else 0.0
    return {
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "auc_pr": round(float(auc_pr), 4),
    }


def _latency_stats(latencies_ms: list[float]) -> dict[str, float]:
    if not latencies_ms:
        return {"avg_latency_ms": 0.0, "p95_latency_ms": 0.0}
    ordered = sorted(latencies_ms)
    p95_index = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
    return {
        "avg_latency_ms": round(sum(latencies_ms) / len(latencies_ms), 4),
        "p95_latency_ms": round(ordered[p95_index], 4),
    }


def _measure_agent(agent: Any, transactions: list[Transaction]) -> tuple[list[float], list[float]]:
    scores: list[float] = []
    latencies_ms: list[float] = []
    for txn in transactions:
        start = time.perf_counter()
        result = agent.score(txn)
        latencies_ms.append((time.perf_counter() - start) * 1000)
        scores.append(result.score)
    return scores, latencies_ms


def _measure_ensemble(
    agents: list[Any], ensemble: EnsembleScorer, transactions: list[Transaction]
) -> tuple[list[float], list[float]]:
    scores: list[float] = []
    latencies_ms: list[float] = []
    for txn in transactions:
        start = time.perf_counter()
        agent_scores = [agent.score(txn) for agent in agents]
        result = ensemble.combine(agent_scores)
        latencies_ms.append((time.perf_counter() - start) * 1000)
        scores.append(result.final_score)
    return scores, latencies_ms


def run_benchmark(
    transactions: list[Transaction] | None = None,
    test_size: float = _DEFAULT_TEST_SIZE,
    threshold: float = _DEFAULT_THRESHOLD,
    seed: int = _DEFAULT_SEED,
) -> dict[str, Any]:
    """Generate (or accept) a labeled dataset, split it, train/prime every
    agent, and measure precision/recall/F1/AUC-PR/latency for each agent
    and for the ensemble, all on the held-out test split."""
    dataset = transactions if transactions is not None else generate_synthetic_transactions(seed=seed)
    if len(dataset) < 10:
        raise ValueError("Need at least 10 transactions to run a meaningful benchmark")

    labels = [int(t.is_fraud_demo_label) for t in dataset]
    train, test = train_test_split(
        dataset, test_size=test_size, random_state=seed, stratify=labels
    )
    y_test = [int(t.is_fraud_demo_label) for t in test]

    velocity_agent = VelocityAgent()
    velocity_agent.set_transactions(dataset)

    behavioral_agent = BehavioralAgent()
    behavioral_agent.build_profiles(dataset)

    graph_agent = GraphAgent()
    graph_agent.build_index(dataset)

    ml_agent = MLAgent(random_state=seed)
    ml_agent.fit(train)

    agents: dict[str, Any] = {
        "rule_agent": RuleAgent(),
        "velocity_agent": velocity_agent,
        "behavioral_agent": behavioral_agent,
        "graph_agent": graph_agent,
        "ml_agent": ml_agent,
    }

    agent_results: dict[str, dict[str, float]] = {}
    for name, agent in agents.items():
        scores, latencies_ms = _measure_agent(agent, test)
        metrics = _compute_metrics(y_test, scores, threshold)
        metrics.update(_latency_stats(latencies_ms))
        metrics["n_test"] = len(test)
        agent_results[name] = metrics

    ensemble_scores, ensemble_latencies = _measure_ensemble(
        list(agents.values()), EnsembleScorer(), test
    )
    ensemble_metrics = _compute_metrics(y_test, ensemble_scores, threshold)
    ensemble_metrics.update(_latency_stats(ensemble_latencies))
    ensemble_metrics["n_test"] = len(test)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {"seed": seed, "test_size": test_size, "threshold": threshold},
        "dataset": {
            "total": len(dataset),
            "train": len(train),
            "test": len(test),
            "fraud_ratio_total": round(sum(labels) / len(labels), 4),
            "fraud_ratio_test": round(sum(y_test) / len(y_test), 4) if y_test else 0.0,
            "pattern_counts": dict(Counter(t.fraud_pattern_type for t in dataset)),
        },
        "agents": agent_results,
        "ensemble": ensemble_metrics,
    }


def save_results(results: dict[str, Any], path: str = _DEFAULT_OUTPUT_PATH) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    benchmark_results = run_benchmark()
    save_results(benchmark_results)

    print(f"Dataset: {benchmark_results['dataset']['total']} transactions "
          f"({benchmark_results['dataset']['train']} train / "
          f"{benchmark_results['dataset']['test']} test)")
    print(f"{'agent':<18}{'precision':>10}{'recall':>10}{'f1':>10}{'auc_pr':>10}{'avg_ms':>10}")
    for name, metrics in benchmark_results["agents"].items():
        print(
            f"{name:<18}{metrics['precision']:>10.4f}{metrics['recall']:>10.4f}"
            f"{metrics['f1']:>10.4f}{metrics['auc_pr']:>10.4f}{metrics['avg_latency_ms']:>10.4f}"
        )
    ens = benchmark_results["ensemble"]
    print(
        f"{'ensemble':<18}{ens['precision']:>10.4f}{ens['recall']:>10.4f}"
        f"{ens['f1']:>10.4f}{ens['auc_pr']:>10.4f}{ens['avg_latency_ms']:>10.4f}"
    )
    print(f"\nSaved to {_DEFAULT_OUTPUT_PATH}")
