from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from fraudlens.api.state import state
from fraudlens.core.cases.decision_workflow import DecisionWorkflowError

router = APIRouter(prefix="/decisions", tags=["decisions"])


class DecisionRequest(BaseModel):
    txn_id: str
    decision: str
    analyst: Optional[str] = None
    notes: Optional[str] = None


@router.post("")
def submit_decision(payload: DecisionRequest) -> dict:
    runtime = state.runtime
    case = runtime.engine.get_case_by_txn(payload.txn_id)
    if case is None:
        try:
            case = runtime.analyze(payload.txn_id)
        except ValueError:
            raise HTTPException(status_code=404, detail=f"Transaction {payload.txn_id} not found")

    try:
        record = runtime.decision_workflow.submit_decision(
            case, payload.decision, analyst=payload.analyst, notes=payload.notes,
        )
    except DecisionWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # An analyst confirming block/block_and_report on a ring-linked case is
    # validated fraud — grow the Fraud DNA library from it. Unconfirmed
    # engine-only detections never feed the library; only analyst-reviewed
    # ones do, so it doesn't fill up with unreviewed false positives.
    if payload.decision in ("block", "block_and_report"):
        runtime.engine.confirm_fraud_dna(payload.txn_id)

    return record.model_dump()


@router.get("/{txn_id}/audit")
def get_audit(txn_id: str) -> dict:
    runtime = state.runtime
    case = runtime.engine.get_case_by_txn(txn_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"No case yet for {txn_id} — call GET /cases/{{txn_id}} first")
    events = runtime.decision_workflow.get_audit_trail(case.case_id)
    return {"events": [e.model_dump() for e in events]}
