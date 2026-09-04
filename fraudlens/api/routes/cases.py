"""Case detail — what /case on the frontend renders."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from fraudlens.api.state import state
from fraudlens.core.privacy import public_case, public_fraud_graph

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


@router.get("/{txn_id}/graph")
def get_case_graph(txn_id: str) -> dict:
    """The real fraud-ring node/edge graph for a case, masked. `graph` is
    null when the transaction exists but has no detected ring — same
    convention as `graph_evidence` being null on the case itself."""
    runtime = state.runtime
    try:
        runtime.engine.analyze(txn_id)  # ensures the transaction is valid, same 404 as /cases/{txn_id}
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Transaction {txn_id} not found")

    result = runtime.engine.get_fraud_graph(txn_id)
    if result is None:
        return {"graph": None}
    graph, flagged_node_id = result
    return {"graph": public_fraud_graph(graph, flagged_node_id)}
