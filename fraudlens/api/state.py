"""Shared application state, set once at startup (see main.py's lifespan).

Kept separate from main.py so route modules can import `state` without a
circular import back to the app factory.
"""

from __future__ import annotations

from fraudlens.runtime import FraudLensRuntime


class AppState:
    runtime: FraudLensRuntime | None = None


state = AppState()
