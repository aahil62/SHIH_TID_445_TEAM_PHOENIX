"""Analyst signup/login — real JWT-based auth, not a demo stub. Seeded
accounts (asharma / riyer, password "fraudlens123") exist so the console
is usable immediately; signup lets a new analyst create their own account.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from fraudlens.api.deps import get_current_analyst
from fraudlens.api.state import state
from fraudlens.core.auth.security import create_access_token
from fraudlens.models.schemas import AnalystProfile, LoginRequest, SignupRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
def signup(payload: SignupRequest) -> TokenResponse:
    store = state.runtime.analyst_store
    username = payload.username.strip().lower()
    if not username or not payload.password:
        raise HTTPException(status_code=400, detail="Username and password are required.")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    try:
        account = store.create(username, payload.display_name.strip() or username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    token = create_access_token(account.username)
    profile = AnalystProfile(username=account.username, display_name=account.display_name)
    return TokenResponse(access_token=token, analyst=profile)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    store = state.runtime.analyst_store
    account = store.verify(payload.username.strip().lower(), payload.password)
    if account is None:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token = create_access_token(account.username)
    profile = AnalystProfile(username=account.username, display_name=account.display_name)
    return TokenResponse(access_token=token, analyst=profile)


@router.get("/me", response_model=AnalystProfile)
def me(current: AnalystProfile = Depends(get_current_analyst)) -> AnalystProfile:
    return current
