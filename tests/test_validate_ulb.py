"""Skips entirely if the ~140MB ULB dataset isn't downloaded locally — see
fraudlens/evaluation/validate_ulb.py's docstring. Never required for the
main suite; this is opt-in external validation, not a build gate."""

import unittest

from fraudlens.evaluation.validate_ulb import _DEFAULT_PATH, run_validation


@unittest.skipUnless(_DEFAULT_PATH.exists(), f"{_DEFAULT_PATH} not downloaded")
class ValidateUlbTests(unittest.TestCase):
    def test_runs_and_produces_plausible_metrics(self) -> None:
        results = run_validation()

        self.assertEqual(results["total_rows"], 284807)
        self.assertAlmostEqual(results["fraud_rate"], 0.001727, places=5)
        for key in ("precision", "recall", "f1", "auc_pr"):
            self.assertGreaterEqual(results[key], 0.0)
            self.assertLessEqual(results[key], 1.0)
        # Real, published-benchmark performance — not our synthetic
        # ensemble's numbers, and shouldn't be expected to match them.
        self.assertGreater(results["auc_pr"], 0.5)


if __name__ == "__main__":
    unittest.main()
