"""Model-performance panel — surfaces the team's own benchmark and ULB
external-validation numbers through the API.

The benchmark (a train/test split plus a full GBM fit) is real work, not
free — it's computed once, lazily, on first request and cached in
process, rather than re-run on every call or forced onto API startup (a
demo machine that never opens the insights page shouldn't pay for it).

ULB validation is never run live here: it needs a ~140MB third-party file
that may not be present on whatever machine serves this demo, and takes
minutes to fit. Instead fraudlens/data/ulb_validation.json holds one real,
already-computed result (see fraudlens/evaluation/validate_ulb.py) that
this route just reads — unlike the dataset and the benchmark cache, this
JSON file IS committed, since it's a fixed real result we want available
without the source data on hand. Missing file -> null, not an error.
"""

from __future__ import annotations

import json
import os
from typing import Any

from fastapi import APIRouter

from fraudlens.evaluation.benchmark import run_benchmark

router = APIRouter(prefix="/stats", tags=["stats"])

_ULB_RESULTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "ulb_validation.json"
)

_benchmark_cache: dict[str, Any] | None = None


def _get_benchmark() -> dict[str, Any]:
    global _benchmark_cache
    if _benchmark_cache is None:
        _benchmark_cache = run_benchmark()
    return _benchmark_cache


def _load_external_validation() -> dict[str, Any] | None:
    if not os.path.exists(_ULB_RESULTS_PATH):
        return None
    try:
        with open(_ULB_RESULTS_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


@router.get("/performance")
def get_performance() -> dict[str, Any]:
    benchmark = _get_benchmark()
    return {
        "generated_at": benchmark["generated_at"],
        "dataset": benchmark["dataset"],
        "agents": benchmark["agents"],
        "ensemble": benchmark["ensemble"],
        "ml_feature_importances": benchmark["ml_feature_importances"],
        "external_validation": _load_external_validation(),
    }
