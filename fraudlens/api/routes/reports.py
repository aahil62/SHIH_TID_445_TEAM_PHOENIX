from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from fraudlens.api.state import state

router = APIRouter(prefix="/reports", tags=["reports"])


def _get_or_analyze(txn_id: str):
    runtime = state.runtime
    case = runtime.engine.get_case_by_txn(txn_id)
    if case is None:
        try:
            case = runtime.engine.analyze(txn_id)
        except ValueError:
            raise HTTPException(status_code=404, detail=f"Transaction {txn_id} not found")
    return runtime, case


@router.get("/{txn_id}")
def get_report(txn_id: str) -> dict:
    runtime, case = _get_or_analyze(txn_id)
    decision = runtime.decision_workflow.get_decision(case.case_id)
    report = runtime.report_generator.generate(case, analyst_decision=decision)
    return report.model_dump()


@router.get("/{txn_id}/pdf")
def get_report_pdf(txn_id: str) -> Response:
    runtime, case = _get_or_analyze(txn_id)
    decision = runtime.decision_workflow.get_decision(case.case_id)
    pdf_bytes = runtime.report_generator.generate_pdf(case, analyst_decision=decision)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report-{txn_id}.pdf"'},
    )
