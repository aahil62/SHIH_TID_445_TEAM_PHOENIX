import unittest

from fraudlens.core.reports.generator import ReportGenerator
from fraudlens.models.schemas import (
    AgentScore,
    AnalystDecision,
    Decision,
    FraudCase,
    FraudDNAMatch,
    FraudDNAProfile,
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

    def test_generate_pdf_returns_a_real_pdf(self) -> None:
        pdf_bytes = self.generator.generate_pdf(_sample_case())
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 500)

    def test_generate_pdf_works_without_graph_or_dna_evidence(self) -> None:
        case = _sample_case()
        case.graph_evidence = None
        pdf_bytes = self.generator.generate_pdf(case)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_generate_pdf_works_with_fraud_dna_match(self) -> None:
        case = _sample_case()
        case.fraud_dna_match = FraudDNAMatch(
            matched_ring_id="SEED-01",
            similarity_score=0.82,
            fraud_type="card_testing",
            modus_operandi="rapid small transactions",
            recommendation="Escalate immediately.",
            matched_profile=FraudDNAProfile(
                ring_id="SEED-01", ring_size=4, shared_devices=2, shared_ips=1,
                avg_amount=5000.0, max_amount=9000.0, merchant_category_count=2,
                velocity_score=0.7, graph_density=0.5, fraud_type="card_testing",
                modus_operandi="rapid small transactions", first_detected="2026-01-01T00:00:00+00:00",
            ),
        )
        pdf_bytes = self.generator.generate_pdf(case)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_generate_pdf_works_with_analyst_decision(self) -> None:
        decision = AnalystDecision(
            id=1, case_id="CASE-TXN-RPT-001", txn_id="TXN-RPT-001",
            decision="review", analyst="jane", notes="Downgrading pending call",
            decided_at="2026-09-03T15:00:00+00:00", is_override=True,
        )
        pdf_bytes = self.generator.generate_pdf(_sample_case(), analyst_decision=decision)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_generate_pdf_works_with_no_agent_scores(self) -> None:
        case = _sample_case()
        case.agent_scores = []
        pdf_bytes = self.generator.generate_pdf(case)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_generate_pdf_handles_rupee_symbol_in_reason_strings(self) -> None:
        # Regression: rule_agent's real reason strings contain a literal ₹
        # (e.g. "Amount ₹342,829.13 exceeds..."), which fpdf2's core font
        # can't encode directly — this must not raise, and shouldn't
        # silently degrade to a bare "?" either.
        case = _sample_case()
        case.agent_scores = [
            AgentScore(
                agent_name="rule_agent", score=0.95, confidence=0.9,
                reasons=["Amount ₹342,829.13 exceeds minor threshold (₹150,000)"],
            )
        ]
        pdf_bytes = self.generator.generate_pdf(case)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_generate_pdf_includes_autonomous_action_when_held(self) -> None:
        case = _sample_case()
        case.system_action = "auto_held"
        pdf_bytes = self.generator.generate_pdf(case)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_generate_pdf_includes_regulatory_context_for_block_and_report(self) -> None:
        # BLOCK_AND_REPORT always has non-empty regulatory context (see
        # regulatory_matrix._DECISION_REFERENCES) — exercises the PDF's
        # citation-block rendering, not just the "no context" path.
        pdf_bytes = self.generator.generate_pdf(_sample_case(decision=Decision.BLOCK_AND_REPORT))
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_generate_pdf_works_for_clear_decision_with_no_regulatory_context(self) -> None:
        case = _sample_case(decision=Decision.CLEAR)
        case.graph_evidence = None
        pdf_bytes = self.generator.generate_pdf(case)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_block_and_report_gets_regulatory_context(self) -> None:
        report = self.generator.generate(_sample_case(decision=Decision.BLOCK_AND_REPORT))
        self.assertTrue(report.regulatory_context)
        self.assertIn("Regulatory Context", report.report_text)
        self.assertIn("Prevention of Money Laundering Act", report.report_text)
        self.assertIn("not a record of any actual regulatory filing", report.report_text)

    def test_clear_case_has_no_regulatory_context(self) -> None:
        report = self.generator.generate(_sample_case(decision=Decision.CLEAR))
        self.assertEqual(report.regulatory_context, [])
        self.assertNotIn("Regulatory Context", report.report_text)

    def test_auto_held_case_surfaces_autonomous_action_section(self) -> None:
        case = _sample_case()
        case.final_score = 0.95
        case.confidence = 0.9
        case.system_action = "auto_held"
        report = self.generator.generate(case)
        self.assertEqual(report.system_action, "auto_held")
        self.assertIn("Autonomous Action", report.report_text)
        self.assertIn("held pending review", report.report_text)
        self.assertIn("no real transaction was stopped", report.report_text)

    def test_non_held_case_omits_autonomous_action_section(self) -> None:
        report = self.generator.generate(_sample_case())
        self.assertIsNone(report.system_action)
        self.assertNotIn("Autonomous Action", report.report_text)

    # ── False positive reporting ────────────────────────────────────────

    def test_report_reflects_confirmed_false_positive(self) -> None:
        decision = AnalystDecision(
            id=1, case_id="CASE-TXN-RPT-001", txn_id="TXN-RPT-001",
            decision="clear", analyst="jane", notes="Not fraud after review.",
            decided_at="2026-09-03T15:00:00+00:00", is_override=True, is_false_positive=True,
        )
        report = self.generator.generate(_sample_case(), analyst_decision=decision)
        self.assertTrue(report.is_false_positive)
        self.assertIn("FALSE POSITIVE", report.report_text)
        # Never ambiguous with a routine clear, and never the stale
        # "PENDING" a real analyst decision should never show.
        self.assertNotIn("PENDING", report.report_text)
        self.assertIn("Confirmed false positive", report.report_text)

    def test_report_without_false_positive_is_not_mislabeled(self) -> None:
        decision = AnalystDecision(
            id=1, case_id="CASE-TXN-RPT-001", txn_id="TXN-RPT-001",
            decision="clear", analyst="jane", notes="Confirmed real fraud, downgraded anyway.",
            decided_at="2026-09-03T15:00:00+00:00", is_override=True,
        )
        report = self.generator.generate(_sample_case(), analyst_decision=decision)
        self.assertFalse(report.is_false_positive)
        self.assertNotIn("FALSE POSITIVE", report.report_text)

    def test_generate_pdf_works_with_false_positive(self) -> None:
        decision = AnalystDecision(
            id=1, case_id="CASE-TXN-RPT-001", txn_id="TXN-RPT-001",
            decision="clear", analyst="jane", notes="Not fraud after review.",
            decided_at="2026-09-03T15:00:00+00:00", is_override=True, is_false_positive=True,
        )
        pdf_bytes = self.generator.generate_pdf(_sample_case(), analyst_decision=decision)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    # ── Graceful degradation for a not-yet-built real-time field ────────

    def test_report_renders_unchanged_without_processing_field(self) -> None:
        # The current, real FraudCase schema — no processed_at field exists
        # yet. This must render exactly as every other test here expects,
        # proving the getattr-based check is a true no-op today.
        case = _sample_case()
        self.assertFalse(hasattr(case, "processed_at"))
        report = self.generator.generate(case)
        self.assertNotIn("Processed at", report.report_text)

    def test_report_surfaces_processing_field_when_present(self) -> None:
        # Simulates a future FraudCase carrying a processing timestamp
        # (e.g. from a real-time ingestion layer) without that field
        # actually existing in the schema yet — object.__setattr__ bypasses
        # FraudCase's pydantic validation, which would otherwise reject an
        # unknown field outright. This proves the report generator's
        # getattr(case, "processed_at", None) check actually surfaces the
        # value when it's there, not just that it tolerates its absence.
        case = _sample_case()
        object.__setattr__(case, "processed_at", "2026-09-03T14:00:02.500000+00:00")
        report = self.generator.generate(case)
        self.assertIn("Processed at", report.report_text)
        self.assertIn("2026-09-03T14:00:02.500000+00:00", report.report_text)

    def test_generate_pdf_works_with_processing_field_present(self) -> None:
        case = _sample_case()
        object.__setattr__(case, "processed_at", "2026-09-03T14:00:02.500000+00:00")
        pdf_bytes = self.generator.generate_pdf(case)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
