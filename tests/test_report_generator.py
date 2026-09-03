import unittest

from fraudlens.core.reports.generator import ReportGenerator
from fraudlens.models.schemas import (
    AgentScore,
    AnalystDecision,
    Decision,
    FraudCase,
    GraphEvidence,
    Transaction,
)


def _sample_case(decision: Decision = Decision.BLOCK_AND_REPORT) -> FraudCase:
    txn = Transaction(
        txn_id="TXN-RPT-001",
        account_id="ACC-0099",
        amount=4200.50,
        merchant_id="MER-0012",
        merchant_category="electronics",
        device_id="DEV-0007",
        ip_address="192.168.1.42",
        timestamp="2026-09-03T14:00:00+00:00",
    )
    return FraudCase(
        case_id="CASE-TXN-RPT-001",
        txn_id=txn.txn_id,
        transaction=txn,
        final_score=0.85,
        decision=decision,
        confidence=0.9,
        agent_scores=[AgentScore(agent_name="graph_agent", score=0.9, confidence=0.85, reasons=["Shared device"])],
        explanation_reasons=["[graph_agent] Shared device"],
        graph_evidence=GraphEvidence(ring_size=4, ring_id="RING-01", suspicious_cluster=True, evidence_summary="4-account ring"),
        recommended_action="Block and escalate.",
    )


class ReportGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.generator = ReportGenerator()

    def test_report_masks_account_id(self) -> None:
        report = self.generator.generate(_sample_case())
        self.assertNotIn("ACC-0099", report.account_id)
        self.assertNotIn("ACC-0099", report.report_text)

    def test_report_without_analyst_decision_is_pending(self) -> None:
        report = self.generator.generate(_sample_case())
        self.assertIsNone(report.analyst_decision)
        self.assertIn("PENDING", report.report_text)

    def test_report_reflects_analyst_override(self) -> None:
        decision = AnalystDecision(
            id=1, case_id="CASE-TXN-RPT-001", txn_id="TXN-RPT-001",
            decision="review", analyst="jane", notes="Downgrading pending call",
            decided_at="2026-09-03T15:00:00+00:00", is_override=True,
        )
        report = self.generator.generate(_sample_case(), analyst_decision=decision)
        self.assertEqual(report.decision, "review")
        self.assertEqual(report.analyst, "jane")
        self.assertIn("jane", report.report_text)
        self.assertIn("Downgrading pending call", report.report_text)

    def test_report_includes_graph_and_recommendation_sections(self) -> None:
        report = self.generator.generate(_sample_case())
        self.assertIn("Graph Evidence", report.report_text)
        self.assertIn("Recommended Action", report.report_text)

    def test_report_omits_dna_section_when_no_match(self) -> None:
        report = self.generator.generate(_sample_case())
        self.assertNotIn("Fraud DNA Match", report.report_text)


if __name__ == "__main__":
    unittest.main()
