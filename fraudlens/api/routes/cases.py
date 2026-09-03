"""Case detail — what /case on the frontend renders."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from fraudlens.api.state import state
from fraudlens.core.privacy import public_case

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("")
def list_cases() -> dict:
    runtime = state.runtime
    return {"cases": [public_case(c) for c in runtime.engine.list_cases()]}


@router.get("/{txn_id}")
def get_case(txn_id: str) -> dict:
    runtime = state.runtime
    try:
        case = runtime.engine.analyze(txn_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Transaction {txn_id} not found")
    return public_case(case)
