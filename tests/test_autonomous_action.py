import os
import tempfile
import unittest

from fraudlens.core.cases.autonomous_action import (
    AUTO_HOLD_ACTION,
    CONFIDENCE_THRESHOLD,
    FINAL_SCORE_THRESHOLD,
    FRAUD_DNA_SIMILARITY_THRESHOLD,
    evaluate_autonomous_action,
)
from fraudlens.core.cases.case_engine import CaseEngine
from fraudlens.core.cases.decision_workflow import DecisionWorkflow
from fraudlens.models.schemas import (
    AgentScore,
    Decision,
    FraudCase,
    FraudDNAMatch,
    FraudDNAProfile,
    Transaction,
)


def _txn(txn_id: str = "TXN-AUTO-1") -> Transaction:
    return Transaction(
        txn_id=txn_id,
        account_id="ACC-1",
        amount=50000.0,
        merchant_id="M1",
        merchant_category="electronics",
        device_id="D1",
        ip_address="1.2.3.4",
        timestamp="2026-09-04T10:00:00+00:00",
    )


def _dna_match(similarity_score: float) -> FraudDNAMatch:
    profile = FraudDNAProfile(
        ring_id="RING-1",
        ring_size=3,
        shared_devices=1,
        shared_ips=1,
        avg_amount=50000.0,
        max_amount=60000.0,
        merchant_category_count=1,
        velocity_score=0.9,
        graph_density=0.8,
        fraud_type="card_testing_ring",
        modus_operandi="Rapid small-value probes across shared devices.",
        first_detected="2026-09-01T00:00:00+00:00",
    )
    return FraudDNAMatch(
        matched_ring_id="RING-1",
        similarity_score=similarity_score,
        fraud_type="card_testing_ring",
        modus_operandi="Rapid small-value probes across shared devices.",
        recommendation="Escalate immediately.",
        matched_profile=profile,
    )


def _case(
    final_score: float,
    confidence: float,
    dna_similarity: float | None = None,
    decision: Decision = Decision.BLOCK_AND_REPORT,
) -> FraudCase:
    txn = _txn()
    return FraudCase(
        case_id=f"CASE-{txn.txn_id}",
        txn_id=txn.txn_id,
        transaction=txn,
        final_score=final_score,
        decision=decision,
        confidence=confidence,
        agent_scores=[AgentScore(agent_name="graph_agent", score=final_score, confidence=confidence)],
        explanation_reasons=["[graph_agent] ring detected"],
        fraud_dna_match=_dna_match(dna_similarity) if dna_similarity is not None else None,
    )


class EvaluateAutonomousActionTests(unittest.TestCase):
    """Boundary tests — the conjunction of all three thresholds is the
    actual point of this feature, not the happy path alone."""

    def test_all_three_signals_at_threshold_triggers(self) -> None:
        case = _case(FINAL_SCORE_THRESHOLD, CONFIDENCE_THRESHOLD, FRAUD_DNA_SIMILARITY_THRESHOLD)
        self.assertEqual(evaluate_autonomous_action(case), AUTO_HOLD_ACTION)

    def test_comfortably_above_all_three_triggers(self) -> None:
        case = _case(0.97, 0.95, 0.95)
        self.assertEqual(evaluate_autonomous_action(case), AUTO_HOLD_ACTION)

    def test_just_under_final_score_threshold_does_not_trigger(self) -> None:
        case = _case(FINAL_SCORE_THRESHOLD - 0.01, 0.95, 0.95)
        self.assertIsNone(evaluate_autonomous_action(case))

    def test_just_under_confidence_threshold_does_not_trigger(self) -> None:
        case = _case(0.97, CONFIDENCE_THRESHOLD - 0.01, 0.95)
        self.assertIsNone(evaluate_autonomous_action(case))

    def test_just_under_dna_similarity_threshold_does_not_trigger(self) -> None:
        case = _case(0.97, 0.95, FRAUD_DNA_SIMILARITY_THRESHOLD - 0.01)
        self.assertIsNone(evaluate_autonomous_action(case))

    def test_high_score_alone_is_not_enough(self) -> None:
        """One number crossing one threshold must never be sufficient —
        this is the whole point of requiring corroborating signals."""
        case = _case(0.99, 0.50, None)
        self.assertIsNone(evaluate_autonomous_action(case))

    def test_no_dna_match_only_needs_score_and_confidence(self) -> None:
        case = _case(0.95, 0.90, dna_similarity=None)
        self.assertEqual(evaluate_autonomous_action(case), AUTO_HOLD_ACTION)

    def test_review_level_case_never_triggers(self) -> None:
        case = _case(0.35, 0.9, 0.95, decision=Decision.REVIEW)
        self.assertIsNone(evaluate_autonomous_action(case))

    def test_clear_level_case_never_triggers(self) -> None:
        case = _case(0.05, 0.9, decision=Decision.CLEAR)
        self.assertIsNone(evaluate_autonomous_action(case))


class _FakeAgent:
    def __init__(self, name: str, score: float, confidence: float = 0.95) -> None:
        self.name = name
        self._score = score
        self._confidence = confidence

    def score(self, txn: Transaction) -> AgentScore:
        return AgentScore(agent_name=self.name, score=self._score, confidence=self._confidence)


class CaseEngineAutonomousActionIntegrationTests(unittest.TestCase):
    """Proves the engine actually sets system_action end-to-end, and that
    an analyst override survives re-analysis instead of being silently
    resurrected on the next GET."""

    def setUp(self) -> None:
        self._cases_tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._cases_tmp.close()
        self.addCleanup(lambda: os.path.exists(self._cases_tmp.name) and os.remove(self._cases_tmp.name))

    def test_high_certainty_case_gets_auto_held(self) -> None:
        txn = _txn("TXN-AUTO-ENGINE-1")
        agents = [_FakeAgent("rule_agent", 0.97, confidence=0.95)]
        engine = CaseEngine([txn], agents=agents, cases_path=self._cases_tmp.name)

        case = engine.analyze(txn.txn_id)

        self.assertGreaterEqual(case.final_score, FINAL_SCORE_THRESHOLD)
        self.assertGreaterEqual(case.confidence, CONFIDENCE_THRESHOLD)
        self.assertEqual(case.system_action, AUTO_HOLD_ACTION)

    def test_borderline_case_stays_human_only(self) -> None:
        txn = _txn("TXN-AUTO-ENGINE-2")
        agents = [_FakeAgent("rule_agent", 0.65, confidence=0.6)]
        engine = CaseEngine([txn], agents=agents, cases_path=self._cases_tmp.name)

        case = engine.analyze(txn.txn_id)

        self.assertIsNone(case.system_action)

    def test_analyst_override_survives_reanalysis(self) -> None:
        txn = _txn("TXN-AUTO-ENGINE-3")
        agents = [_FakeAgent("rule_agent", 0.97, confidence=0.95)]
        engine = CaseEngine([txn], agents=agents, cases_path=self._cases_tmp.name)
        case = engine.analyze(txn.txn_id)
        self.assertEqual(case.system_action, AUTO_HOLD_ACTION)

        workflow = DecisionWorkflow(
            decisions_path=tempfile.mktemp(suffix=".json"),
            audit_path=tempfile.mktemp(suffix=".json"),
        )
        workflow.submit_decision(case, "review", analyst="alice", notes="False positive")
        self.assertIsNone(case.system_action)

        # A later re-analysis (e.g. another GET /cases/{txn_id}) must not
        # silently resurrect the auto-hold an analyst already reversed.
        reanalyzed = engine.analyze(txn.txn_id)
        self.assertIsNone(reanalyzed.system_action)


class DecisionWorkflowAutonomousActionTests(unittest.TestCase):
    """The audit trail is the other half of "bounded" autonomy — it must
    be distinct from analyst-driven events, carry the triggering scores,
    never duplicate on repeated analysis, and record a clean reversal."""

    def setUp(self) -> None:
        self._decisions_tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._decisions_tmp.close()
        self._audit_tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._audit_tmp.close()
        for f in (self._decisions_tmp, self._audit_tmp):
            self.addCleanup(lambda p=f.name: os.path.exists(p) and os.remove(p))

    def _workflow(self) -> DecisionWorkflow:
        return DecisionWorkflow(
            decisions_path=self._decisions_tmp.name, audit_path=self._audit_tmp.name
        )

    def test_auto_held_case_logs_distinct_audit_event(self) -> None:
        workflow = self._workflow()
        case = _case(0.95, 0.9, 0.9)
        case.system_action = evaluate_autonomous_action(case)

        event = workflow.record_autonomous_action(case)

        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, "autonomous_action")
        self.assertEqual(event.actor, "system")
        self.assertEqual(event.metadata["final_score"], 0.95)
        self.assertEqual(event.metadata["confidence"], 0.9)
        self.assertEqual(event.metadata["fraud_dna_similarity_score"], 0.9)

        events = workflow.get_audit_trail(case.case_id)
        self.assertEqual(len(events), 1)

    def test_non_triggering_case_logs_nothing(self) -> None:
        workflow = self._workflow()
        case = _case(0.5, 0.5)
        case.system_action = evaluate_autonomous_action(case)

        self.assertIsNone(workflow.record_autonomous_action(case))
        self.assertEqual(workflow.get_audit_trail(case.case_id), [])

    def test_repeated_recording_does_not_duplicate(self) -> None:
        """CaseEngine.analyze() re-runs on every GET — recording must be
        idempotent so the audit trail doesn't fill up with duplicates."""
        workflow = self._workflow()
        case = _case(0.95, 0.9, 0.9)
        case.system_action = evaluate_autonomous_action(case)

        workflow.record_autonomous_action(case)
        workflow.record_autonomous_action(case)
        workflow.record_autonomous_action(case)

        events = workflow.get_audit_trail(case.case_id)
        self.assertEqual(len(events), 1)

    def test_autonomous_event_distinct_from_analyst_event(self) -> None:
        workflow = self._workflow()
        case = _case(0.95, 0.9, 0.9)
        case.system_action = evaluate_autonomous_action(case)
        workflow.record_autonomous_action(case)

        workflow.submit_decision(case, "block_and_report", analyst="alice")

        events = workflow.get_audit_trail(case.case_id)
        event_types = {e.event_type for e in events}
        self.assertEqual(event_types, {"autonomous_action", "analyst_decision"})
        auto_event = next(e for e in events if e.event_type == "autonomous_action")
        self.assertEqual(auto_event.actor, "system")
        analyst_event = next(e for e in events if e.event_type == "analyst_decision")
        self.assertEqual(analyst_event.actor, "alice")

    def test_any_analyst_decision_reverses_auto_hold_cleanly(self) -> None:
        workflow = self._workflow()
        case = _case(0.95, 0.9, 0.9)
        case.system_action = evaluate_autonomous_action(case)
        self.assertEqual(case.system_action, AUTO_HOLD_ACTION)

        record = workflow.submit_decision(case, "review", analyst="bob", notes="Overriding hold")

        self.assertEqual(record.decision, "review")
        self.assertIsNone(case.system_action)
        self.assertIsNotNone(case.system_action_overridden_at)

        events = workflow.get_audit_trail(case.case_id)
        decision_event = next(e for e in events if e.event_type == "analyst_decision")
        self.assertEqual(decision_event.metadata.get("reversed_autonomous_action"), AUTO_HOLD_ACTION)

    def test_decision_on_non_held_case_does_not_claim_reversal(self) -> None:
        workflow = self._workflow()
        case = _case(0.5, 0.5)  # never auto-held
        record = workflow.submit_decision(case, "review", analyst="bob")

        events = workflow.get_audit_trail(case.case_id)
        decision_event = next(e for e in events if e.event_type == "analyst_decision")
        self.assertNotIn("reversed_autonomous_action", decision_event.metadata)


if __name__ == "__main__":
    unittest.main()
