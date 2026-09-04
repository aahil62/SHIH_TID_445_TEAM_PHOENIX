"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import Header, HTTPException

from fraudlens.api.state import state
from fraudlens.core.auth.security import decode_access_token
from fraudlens.models.schemas import AnalystProfile


def get_current_analyst(authorization: str | None = Header(default=None)) -> AnalystProfile:
    """Requires a valid `Authorization: Bearer <token>` header — raises 401
    otherwise. Used to attach a real, authenticated analyst identity to any
    write action (submitting a decision) instead of trusting client-supplied
    free text."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated — missing bearer token.")
    token = authorization.removeprefix("Bearer ").strip()
    username = decode_access_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session — please log in again.")
    account = state.runtime.analyst_store.get(username)
    if account is None:
        raise HTTPException(status_code=401, detail="Analyst account no longer exists.")
    return AnalystProfile(username=account.username, display_name=account.display_name)
