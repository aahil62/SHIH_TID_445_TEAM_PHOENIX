"""Test-only helper: redirect every persisted runtime file to a throwaway
temp directory instead of the real fraudlens/data/*.json files the live
demo server reads from.

Must be called before `from fraudlens.api.main import app` in any test
module that builds a real app/TestClient — RuntimeConfig's path defaults
are read from these env vars at FraudLensRuntime construction time (see
runtime.py), which happens inside the FastAPI lifespan, triggered the
moment a TestClient enters its context.

Deliberately NOT done via tests/__init__.py: `python -m unittest discover
-s tests` imports test_*.py as bare top-level modules rather than as
`tests.test_*`, so the package's __init__.py never runs before them —
verified empirically, not assumed. A plain function in the fraudlens
package itself sidesteps that import-order quirk entirely.
"""

from __future__ import annotations

import os
import tempfile


def use_isolated_data_dir() -> None:
    if "FRAUDLENS_CASES_PATH" in os.environ:
        return  # already isolated (e.g. called from more than one test module)
    data_dir = tempfile.mkdtemp(prefix="fraudlens-test-data-")
    os.environ["FRAUDLENS_CASES_PATH"] = os.path.join(data_dir, "cases.json")
    os.environ["FRAUDLENS_DNA_STORE_PATH"] = os.path.join(data_dir, "fraud_dna_library.json")
    os.environ["FRAUDLENS_DECISIONS_PATH"] = os.path.join(data_dir, "analyst_decisions.json")
    os.environ["FRAUDLENS_AUDIT_PATH"] = os.path.join(data_dir, "audit_log.json")
    os.environ["FRAUDLENS_ANALYSTS_PATH"] = os.path.join(data_dir, "analysts.json")
    os.environ["FRAUDLENS_ACCOUNT_RESTRICTIONS_PATH"] = os.path.join(data_dir, "account_restrictions.json")
