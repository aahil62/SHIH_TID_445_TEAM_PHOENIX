from __future__ import annotations

from fastapi import APIRouter, HTTPException

from fraudlens.api.state import state

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{txn_id}")
def get_report(txn_id: str) -> dict:
    runtime = state.runtime
    case = runtime.engine.get_case_by_txn(txn_id)
    if case is None:
        try:
            case = runtime.analyze(txn_id)
        except ValueError:
            raise HTTPException(status_code=404, detail=f"Transaction {txn_id} not found")

    decision = runtime.decision_workflow.get_decision(case.case_id)
    report = runtime.report_generator.generate(case, analyst_decision=decision)
    return report.model_dump()
