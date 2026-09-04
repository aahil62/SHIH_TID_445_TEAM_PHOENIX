"""Deterministic markdown report generation from a FraudCase — the
document a compliance officer actually reads, not just a JSON dump."""

from __future__ import annotations

from typing import Optional

from fraudlens.core.privacy import mask_identifier, mask_ip
from fraudlens.core.reports.pdf_generator import build_case_report_pdf
from fraudlens.models.schemas import AnalystDecision, FraudCase, FraudReport

_BADGES = {
    "clear": "CLEAR",
    "review": "REVIEW",
    "block": "BLOCK",
    "block_and_report": "BLOCK & ESCALATE",
}


class ReportGenerator:
    def generate(
        self,
        case: FraudCase,
        analyst_decision: Optional[AnalystDecision] = None,
        report_status: str = "draft",
    ) -> FraudReport:
        report_text = self._build_markdown(case, analyst_decision, report_status)
        return FraudReport(
            report_id=f"RPT-{case.case_id}",
            case_id=case.case_id,
            txn_id=case.txn_id,
            account_id=mask_identifier(case.transaction.account_id),
            risk_score=case.final_score,
            decision=analyst_decision.decision if analyst_decision else case.decision.value,
            engine_recommendation=case.decision.value,
            analyst_decision=analyst_decision.decision if analyst_decision else None,
            analyst=analyst_decision.analyst if analyst_decision else None,
            analyst_notes=analyst_decision.notes if analyst_decision else None,
            confidence=case.confidence,
            agent_scores=case.agent_scores,
            graph_evidence=case.graph_evidence,
            fraud_dna_match=case.fraud_dna_match,
            recommended_action=case.recommended_action,
            report_status=report_status,
            report_text=report_text,
        )

    def generate_pdf(
        self,
        case: FraudCase,
        analyst_decision: Optional[AnalystDecision] = None,
    ) -> bytes:
        """A real laid-out PDF built straight from the case — same inputs
        as generate()/_build_markdown, not a rendering of the markdown
        text. See fraudlens/core/reports/pdf_generator.py."""
        return build_case_report_pdf(case, analyst_decision=analyst_decision)

    def _build_markdown(
        self,
        case: FraudCase,
        analyst_decision: Optional[AnalystDecision],
        report_status: str,
    ) -> str:
        engine_badge = _BADGES.get(case.decision.value, case.decision.value.upper())
        analyst_badge = _BADGES.get(analyst_decision.decision, analyst_decision.decision.upper()) if analyst_decision else "PENDING"
        txn = case.transaction

        sections = [
            f"# Investigation Report\n\n"
            f"| Field | Value |\n|---|---|\n"
            f"| **Case ID** | `{case.case_id}` |\n"
            f"| **Transaction ID** | `{case.txn_id}` |\n"
            f"| **FraudLens recommendation** | {engine_badge} |\n"
            f"| **Analyst decision** | {analyst_badge} |\n"
            f"| **Report status** | {report_status.replace('_', ' ').title()} |",

            f"## Transaction Summary\n\n"
            f"| Field | Value |\n|---|---|\n"
            f"| **Account** | `{mask_identifier(txn.account_id)}` |\n"
            f"| **Amount** | ₹{txn.amount:,.2f} |\n"
            f"| **Merchant** | {mask_identifier(txn.merchant_id)} ({txn.merchant_category}) |\n"
            f"| **Timestamp** | {txn.timestamp} |\n"
            f"| **Channel** | {txn.channel} |\n"
            f"| **Device** | `{mask_identifier(txn.device_id)}` |\n"
            f"| **IP** | `{mask_ip(txn.ip_address)}` |",

            f"## Risk Assessment\n\n"
            f"| Metric | Value |\n|---|---|\n"
            f"| **Risk score** | {case.final_score:.1%} |\n"
            f"| **Model agreement confidence** | {case.confidence:.1%} |",

            "## Agent Evidence\n\n"
            "| Agent | Score | Confidence | Key finding |\n|---|---|---|---|\n"
            + "\n".join(
                f"| {a.agent_name} | {a.score:.2f} | {a.confidence:.0%} | "
                f"{a.reasons[0] if a.reasons else '—'} |"
                for a in case.agent_scores
            ),
        ]

        if case.graph_evidence:
            ge = case.graph_evidence
            sections.append(
                f"## Graph Evidence\n\n"
                f"| Metric | Value |\n|---|---|\n"
                f"| **Ring size** | {ge.ring_size} |\n"
                f"| **Shared devices** | {len(ge.shared_devices)} |\n"
                f"| **Shared IPs** | {len(ge.shared_ips)} |\n"
                f"| **Suspicious cluster** | {'Yes' if ge.suspicious_cluster else 'No'} |\n\n"
                f"{ge.evidence_summary}"
            )

        if case.fraud_dna_match:
            dna = case.fraud_dna_match
            sections.append(
                f"## Fraud DNA Match\n\n"
                f"| Field | Value |\n|---|---|\n"
                f"| **Similarity** | {dna.similarity_score:.1%} |\n"
                f"| **Matched pattern** | `{dna.matched_ring_id}` ({dna.fraud_type}) |\n\n"
                f"**Modus operandi:** {dna.modus_operandi}\n\n"
                f"**Recommendation:** {dna.recommendation}"
            )

        sections.append(f"## Recommended Action\n\n{case.recommended_action}")

        if analyst_decision:
            sections.append(
                f"## Analyst Decision\n\n"
                f"**Decision:** {analyst_badge}\n\n"
                f"**Analyst:** {analyst_decision.analyst or 'Unspecified'}\n\n"
                f"**Notes:** {analyst_decision.notes or 'None provided.'}"
            )

        sections.append(
            "---\n\n*Generated by FraudLens. A qualified analyst must review the evidence "
            "before any action is taken; this report does not submit anything externally.*"
        )
        return "\n\n".join(sections)
