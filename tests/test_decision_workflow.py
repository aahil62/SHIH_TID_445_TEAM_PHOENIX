import os
import tempfile
import unittest

from fraudlens.core.cases.decision_workflow import DecisionWorkflow, DecisionWorkflowError
from fraudlens.models.schemas import (
    AgentScore,
    Decision,
    FraudCase,
    GraphEvidence,
    Transaction,
)


def _txn(txn_id="TXN-1") -> Transaction:
    return Transaction(
        txn_id=txn_id,
        account_id="ACC-1",
        amount=500.0,
        merchant_id="M1",
        merchant_category="electronics",
        device_id="D1",
        ip_address="1.2.3.4",
        timestamp="2026-09-01T10:00:00+00:00",
    )


def _ring_evidence() -> GraphEvidence:
    return GraphEvidence(
        connected_accounts=["ACC-1", "ACC-2", "ACC-3"],
        shared_devices=["D1"],
        shared_ips=["IP1"],
        ring_size=3,
        ring_id="RING-ABC123",
        suspicious_cluster=True,
        graph_density=0.8,
        evidence_summary="3-account ring",
    )


def _case(
    txn_id="TXN-1", decision=Decision.BLOCK_AND_REPORT, graph_evidence=None
) -> FraudCase:
    txn = _txn(txn_id)
    return FraudCase(
        case_id=f"CASE-{txn_id}",
        txn_id=txn_id,
        transaction=txn,
        final_score=0.9,
        decision=decision,
        confidence=0.85,
        agent_scores=[AgentScore(agent_name="graph_agent", score=0.9)],
        explanation_reasons=["[graph_agent] ring detected"],
        graph_evidence=graph_evidence,
    )


class DecisionWorkflowTests(unittest.TestCase):
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

    def test_rejects_invalid_decision(self) -> None:
        workflow = self._workflow()
        with self.assertRaises(DecisionWorkflowError):
            workflow.submit_decision(_case(), "maybe_block", analyst="alice")

    def test_accepts_all_valid_decisions(self) -> None:
        workflow = self._workflow()
        for value in ("clear", "review", "block", "block_and_report"):
            record = workflow.submit_decision(
                _case(txn_id=f"TXN-{value}"), value, analyst="alice"
            )
            self.assertEqual(record.decision, value)

    def test_matching_decision_is_not_an_override(self) -> None:
        workflow = self._workflow()
        case = _case(decision=Decision.REVIEW)
        record = workflow.submit_decision(case, "review", analyst="alice")
        self.assertFalse(record.is_override)

    def test_different_decision_is_an_override(self) -> None:
        workflow = self._workflow()
        case = _case(decision=Decision.BLOCK)
        record = workflow.submit_decision(case, "clear", analyst="alice")
        self.assertTrue(record.is_override)

    def test_downgrading_ring_linked_block_is_high_risk_override(self) -> None:
        workflow = self._workflow()
        case = _case(decision=Decision.BLOCK_AND_REPORT, graph_evidence=_ring_evidence())
        self.assertTrue(workflow.is_high_risk_override(case, "clear"))

        workflow.submit_decision(case, "clear", analyst="alice", notes="false positive")
        events = workflow.get_audit_trail(case.case_id)
        decision_event = next(e for e in events if e.event_type == "analyst_decision")
        self.assertTrue(decision_event.metadata.get("high_risk_override"))
        self.assertEqual(decision_event.metadata.get("ring_id"), "RING-ABC123")

    def test_downgrade_without_ring_evidence_is_not_high_risk(self) -> None:
        workflow = self._workflow()
        case = _case(decision=Decision.BLOCK, graph_evidence=None)
        self.assertFalse(workflow.is_high_risk_override(case, "clear"))

    def test_upgrading_decision_is_not_high_risk_even_with_ring(self) -> None:
        workflow = self._workflow()
        case = _case(decision=Decision.REVIEW, graph_evidence=_ring_evidence())
        self.assertFalse(workflow.is_high_risk_override(case, "block_and_report"))

    def test_record_case_created_logs_engine_decision(self) -> None:
        workflow = self._workflow()
        case = _case(decision=Decision.BLOCK_AND_REPORT, graph_evidence=_ring_evidence())
        workflow.record_case_created(case)

        events = workflow.get_audit_trail(case.case_id)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "case_created")
        self.assertEqual(events[0].metadata["ring_id"], "RING-ABC123")

    def test_get_decision_returns_latest_submission(self) -> None:
        workflow = self._workflow()
        case = _case()
        workflow.submit_decision(case, "review", analyst="alice")
        retrieved = workflow.get_decision(case.case_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.decision, "review")

    def test_decisions_and_audit_reload_from_disk(self) -> None:
        case = _case(decision=Decision.BLOCK, graph_evidence=_ring_evidence())
        first = self._workflow()
        first.record_case_created(case)
        first.submit_decision(case, "clear", analyst="bob")

        second = self._workflow()
        self.assertIsNotNone(second.get_decision(case.case_id))
        self.assertEqual(len(second.get_audit_trail(case.case_id)), 2)


if __name__ == "__main__":
    unittest.main()
