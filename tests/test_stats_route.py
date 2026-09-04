"""Tests for GET /stats/performance.

Mounts only the stats router on a bare FastAPI app — this route never
touches state.runtime, so there's no reason to pay for the full app's
lifespan (which builds the whole runtime, fits ml_agent, etc.) just to
test it. run_benchmark() itself is mocked throughout: a real run does a
train/test split and a full GBM fit, and this suite shouldn't pay that
cost on every test, or on every CI run.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import fraudlens.api.routes.stats as stats_module
from fraudlens.api.routes.stats import router as stats_router

_FAKE_BENCHMARK = {
    "generated_at": "2026-01-01T00:00:00+00:00",
    "dataset": {"total": 10, "train": 8, "test": 2, "fraud_ratio_total": 0.2},
    "agents": {
        "rule_agent": {
            "precision": 1.0, "recall": 0.5, "f1": 0.667, "auc_pr": 0.9,
            "avg_latency_ms": 0.01, "p95_latency_ms": 0.02, "n_test": 2,
        },
    },
    "ensemble": {
        "precision": 0.98, "recall": 0.87, "f1": 0.92, "auc_pr": 0.95,
        "avg_latency_ms": 0.3, "p95_latency_ms": 0.4, "n_test": 2,
    },
    "ml_feature_importances": {"amount": 0.6, "hour_of_day": 0.4},
}


class StatsRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        stats_module._benchmark_cache = None
        app = FastAPI()
        app.include_router(stats_router)
        self.client = TestClient(app)
        self.addCleanup(self._reset_cache)

    def _reset_cache(self) -> None:
        stats_module._benchmark_cache = None

    @patch("fraudlens.api.routes.stats.run_benchmark", return_value=_FAKE_BENCHMARK)
    def test_performance_returns_benchmark_shape(self, mock_run) -> None:
        with patch.object(stats_module, "_ULB_RESULTS_PATH", "/definitely/does/not/exist.json"):
            resp = self.client.get("/stats/performance")

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["agents"], _FAKE_BENCHMARK["agents"])
        self.assertEqual(data["ensemble"], _FAKE_BENCHMARK["ensemble"])
        self.assertEqual(data["ml_feature_importances"], _FAKE_BENCHMARK["ml_feature_importances"])
        self.assertEqual(data["dataset"], _FAKE_BENCHMARK["dataset"])
        self.assertIsNone(data["external_validation"])
        mock_run.assert_called_once()

    @patch("fraudlens.api.routes.stats.run_benchmark", return_value=_FAKE_BENCHMARK)
    def test_benchmark_is_computed_once_and_cached(self, mock_run) -> None:
        with patch.object(stats_module, "_ULB_RESULTS_PATH", "/definitely/does/not/exist.json"):
            self.client.get("/stats/performance")
            self.client.get("/stats/performance")
            self.client.get("/stats/performance")

        self.assertEqual(mock_run.call_count, 1)

    @patch("fraudlens.api.routes.stats.run_benchmark", return_value=_FAKE_BENCHMARK)
    def test_missing_ulb_file_returns_null_not_error(self, mock_run) -> None:
        with patch.object(stats_module, "_ULB_RESULTS_PATH", "/definitely/does/not/exist.json"):
            resp = self.client.get("/stats/performance")

        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json()["external_validation"])

    @patch("fraudlens.api.routes.stats.run_benchmark", return_value=_FAKE_BENCHMARK)
    def test_present_ulb_file_is_returned_verbatim(self, mock_run) -> None:
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
        expected = {"dataset": "ULB Credit Card Fraud", "auc_pr": 0.95, "total_rows": 284807}
        json.dump(expected, tmp)
        tmp.close()
        self.addCleanup(lambda: os.path.exists(tmp.name) and os.remove(tmp.name))

        with patch.object(stats_module, "_ULB_RESULTS_PATH", tmp.name):
            resp = self.client.get("/stats/performance")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["external_validation"], expected)

    @patch("fraudlens.api.routes.stats.run_benchmark", return_value=_FAKE_BENCHMARK)
    def test_corrupt_ulb_file_returns_null_not_500(self, mock_run) -> None:
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
        tmp.write("{not valid json")
        tmp.close()
        self.addCleanup(lambda: os.path.exists(tmp.name) and os.remove(tmp.name))

        with patch.object(stats_module, "_ULB_RESULTS_PATH", tmp.name):
            resp = self.client.get("/stats/performance")

        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json()["external_validation"])


if __name__ == "__main__":
    unittest.main()
