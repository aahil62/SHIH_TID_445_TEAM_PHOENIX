import unittest

from fraudlens.data.synthetic_generator import generate_synthetic_transactions
from fraudlens.evaluation.benchmark import run_benchmark

_EXPECTED_AGENTS = {"rule_agent", "velocity_agent", "behavioral_agent", "graph_agent", "ml_agent"}
_METRIC_KEYS = {"precision", "recall", "f1", "auc_pr", "avg_latency_ms", "p95_latency_ms", "n_test"}


def _small_dataset(seed: int = 1):
    return generate_synthetic_transactions(
        num_normal=80,
        num_high_amount=15,
        num_risky_merchant=15,
        num_odd_hour=10,
        num_card_testing_bursts=3,
        num_high_velocity_bursts=3,
        num_fraud_rings=1,
        seed=seed,
    )


class BenchmarkTests(unittest.TestCase):
    def test_returns_all_expected_agents_and_ensemble(self) -> None:
        results = run_benchmark(transactions=_small_dataset(), test_size=0.25, seed=1)

        self.assertEqual(set(results["agents"].keys()), _EXPECTED_AGENTS)
        self.assertIn("ensemble", results)

    def test_every_agent_result_has_expected_metric_keys(self) -> None:
        results = run_benchmark(transactions=_small_dataset(), test_size=0.25, seed=1)

        for name, metrics in results["agents"].items():
            self.assertEqual(set(metrics.keys()), _METRIC_KEYS, msg=name)
        self.assertEqual(set(results["ensemble"].keys()), _METRIC_KEYS)

    def test_metrics_are_within_valid_ranges(self) -> None:
        results = run_benchmark(transactions=_small_dataset(), test_size=0.25, seed=1)

        for metrics in list(results["agents"].values()) + [results["ensemble"]]:
            for key in ("precision", "recall", "f1", "auc_pr"):
                self.assertGreaterEqual(metrics[key], 0.0, msg=key)
                self.assertLessEqual(metrics[key], 1.0, msg=key)
            self.assertGreaterEqual(metrics["avg_latency_ms"], 0.0)
            self.assertGreaterEqual(metrics["p95_latency_ms"], metrics["avg_latency_ms"] - 1e-6)

    def test_dataset_split_sizes_match_config(self) -> None:
        dataset = _small_dataset()
        results = run_benchmark(transactions=dataset, test_size=0.25, seed=1)

        self.assertEqual(results["dataset"]["total"], len(dataset))
        self.assertEqual(
            results["dataset"]["train"] + results["dataset"]["test"], len(dataset)
        )
        self.assertEqual(results["dataset"]["test"], results["agents"]["rule_agent"]["n_test"])

    def test_same_seed_is_reproducible(self) -> None:
        dataset = _small_dataset()
        first = run_benchmark(transactions=dataset, test_size=0.25, seed=7)
        second = run_benchmark(transactions=dataset, test_size=0.25, seed=7)

        # Latency is a wall-clock measurement and legitimately varies run to
        # run; only the deterministic classification metrics should match.
        for key in ("precision", "recall", "f1", "auc_pr", "n_test"):
            self.assertEqual(
                first["agents"]["ml_agent"][key], second["agents"]["ml_agent"][key], msg=key
            )
        self.assertEqual(first["dataset"], second["dataset"])

    def test_too_small_dataset_raises(self) -> None:
        with self.assertRaises(ValueError):
            run_benchmark(transactions=_small_dataset()[:5])

    def test_includes_ml_feature_importances(self) -> None:
        results = run_benchmark(transactions=_small_dataset(), test_size=0.25, seed=1)

        importances = results["ml_feature_importances"]
        self.assertTrue(importances)
        for value in importances.values():
            self.assertGreaterEqual(value, 0.0)
        self.assertAlmostEqual(sum(importances.values()), 1.0, places=4)

    def test_pattern_counts_cover_generated_labels(self) -> None:
        dataset = _small_dataset()
        results = run_benchmark(transactions=dataset, test_size=0.25, seed=1)

        self.assertEqual(sum(results["dataset"]["pattern_counts"].values()), len(dataset))
        self.assertIn("normal", results["dataset"]["pattern_counts"])
        self.assertIn("fraud_ring", results["dataset"]["pattern_counts"])


if __name__ == "__main__":
    unittest.main()
