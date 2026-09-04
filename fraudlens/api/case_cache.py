"""Shared, process-wide cache of every transaction's analyzed FraudCase.

Used by every route that needs case data for more than one transaction at a
time (console.py's dashboard/reports/audit/network views, transactions.py's
recent-activity feed) — recomputing the full six-agent pipeline per
transaction on every request would mean re-running ~1,000 analyses per page
load. Safe to share: CaseEngine mutates FraudCase objects in place on
decision submission (see decisions.py), and this cache holds references to
those same objects, so a submitted decision is visible here without any
explicit invalidation.
"""

from __future__ import annotations

import threading

from fraudlens.models.schemas import FraudCase
from fraudlens.runtime import FraudLensRuntime

_cache_lock = threading.Lock()
_cache_runtime_id: int | None = None
_all_cases_cache: list[FraudCase] | None = None


def all_cases(runtime: FraudLensRuntime) -> list[FraudCase]:
    """Every transaction in the fixed dataset, analyzed once. Cached at
    module level since the dataset and models are deterministic for the
    life of a given runtime. Keyed on the runtime's identity (not just "is
    it None") so a fresh runtime — e.g. a new test class's own TestClient
    rebuilding the app's lifespan — invalidates the cache instead of
    silently reusing another runtime's cases.

    Lock-guarded: FastAPI runs sync routes in a thread pool, and the
    frontend's console pages fire dashboard/network/reports/audit requests
    in parallel — without this lock, two threads could both see a stale
    cache and call runtime.analyze() concurrently, mutating CaseEngine's
    internal cases dict from two threads at once ("dictionary changed size
    during iteration", a real crash hit and reproduced during live
    testing, not a hypothetical)."""
    global _cache_runtime_id, _all_cases_cache
    with _cache_lock:
        if _cache_runtime_id != id(runtime):
            _all_cases_cache = [runtime.analyze(t.txn_id) for t in runtime.transactions]
            _cache_runtime_id = id(runtime)
        return _all_cases_cache
