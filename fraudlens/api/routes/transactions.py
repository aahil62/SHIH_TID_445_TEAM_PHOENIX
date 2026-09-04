"""The alert-queue feed — what /feed on the frontend renders."""

from __future__ import annotations

from fastapi import APIRouter, Query

from fraudlens.api.state import state
from fraudlens.core.privacy import mask_identifier

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/recent")
def recent(limit: int = Query(25, ge=1, le=200)) -> dict:
    runtime = state.runtime
    txns = sorted(runtime.transactions, key=lambda t: t.timestamp, reverse=True)[:limit]

    summaries = []
    for txn in txns:
        case = runtime.analyze(txn.txn_id)
        summaries.append({
            "txn_id": case.txn_id,
            "account_id": mask_identifier(txn.account_id),
            "amount": txn.amount,
            "merchant_category": txn.merchant_category,
            "timestamp": txn.timestamp,
            "final_score": case.final_score,
            "decision": case.decision.value,
            "top_reason": case.explanation_reasons[0] if case.explanation_reasons else "",
        })
    return {"transactions": summaries}
