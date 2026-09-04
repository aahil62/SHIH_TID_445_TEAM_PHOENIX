"""The alert-queue feed — what /feed on the frontend renders."""

from __future__ import annotations

from fastapi import APIRouter, Query

from fraudlens.api.case_cache import all_cases
from fraudlens.api.state import state
from fraudlens.core.privacy import mask_identifier

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/recent")
def recent(limit: int = Query(25, ge=1, le=200)) -> dict:
    runtime = state.runtime
    # Read from the shared, already-analyzed cache instead of calling
    # runtime.analyze() per transaction here — that used to mean re-running
    # the full six-agent pipeline for every transaction on every request
    # (measured ~1.6s for limit=25), even though every other console route
    # already analyzes the same fixed dataset once and reuses it.
    cases_by_txn = {c.txn_id: c for c in all_cases(runtime)}
    txns = sorted(runtime.transactions, key=lambda t: t.timestamp, reverse=True)[:limit]

    summaries = []
    for txn in txns:
        case = cases_by_txn[txn.txn_id]
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
