"""Analyst decision workflow for FraudLens.

Records an analyst's clear/review/block/block_and_report decision on a
FraudCase and keeps an audit trail (AuditEvent) of every case and
decision event — persisted the same way CaseEngine persists cases.json.

Flags "high-risk overrides": an analyst downgrading a decision on a case
whose graph_evidence shows a detected ring (suspicious_cluster=True).
That combination — reversing a ring-linked block — is exactly the
situation this branch's graph/ring evidence needs to surface loudest, so
it gets called out explicitly in the audit metadata rather than logged
identically to any other override.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional

from fraudlens.core.cases.autonomous_action import AUTO_HOLD_ACTION
from fraudlens.models.schemas import AnalystDecision, AuditEvent, Decision, FraudCase

_VALID_DECISIONS = {d.value for d in Decision}

_SEVERITY_RANK: dict[str, int] = {
    Decision.CLEAR.value: 0,
    Decision.REVIEW.value: 1,
    Decision.BLOCK.value: 2,
    Decision.BLOCK_AND_REPORT.value: 3,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DecisionWorkflowError(ValueError):
    """Raised for an invalid decision value."""


class DecisionWorkflow:
    """Analyst decision + audit trail on top of engine-produced FraudCases."""

    def __init__(
        self,
        decisions_path: str = "fraudlens/data/analyst_decisions.json",
        audit_path: str = "fraudlens/data/audit_log.json",
    ) -> None:
        self._decisions_path = decisions_path
        self._audit_path = audit_path
        self._decisions: dict[str, AnalystDecision] = {}
        self._audit_events: list[AuditEvent] = []
        self._next_decision_id = 1
        self._next_audit_id = 1
        self._load()

    def record_case_created(self, case: FraudCase) -> AuditEvent:
        """Log the engine's own decision as the case's first audit event."""
        metadata: dict = {"engine_decision": case.decision.value, "final_score": case.final_score}
        if case.graph_evidence and case.graph_evidence.suspicious_cluster:
            metadata["ring_id"] = case.graph_evidence.ring_id
            metadata["ring_size"] = case.graph_evidence.ring_size
        return self._log_event(case.case_id, case.txn_id, "case_created", "engine", metadata)

    def submit_decision(
        self,
        case: FraudCase,
        decision: str,
        analyst: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> AnalystDecision:
        if decision not in _VALID_DECISIONS:
            raise DecisionWorkflowError(
                f"Unknown decision {decision!r}; expected one of {sorted(_VALID_DECISIONS)}"
            )

        is_override = decision != case.decision.value
        high_risk_override = self.is_high_risk_override(case, decision)

        # A human decision always reverses a system auto-hold, cleanly and
        # permanently — this is what keeps "autonomy within limits" true:
        # the case is never final without a human able to undo it. Mutates
        # the same FraudCase object CaseEngine holds (analyze() preserves
        # this reversal on every future re-analysis of the same case), so
        # every later reader of case.system_action sees it cleared too.
        reversed_autonomous_action = (
            case.system_action == AUTO_HOLD_ACTION and case.system_action_overridden_at is None
        )
        if reversed_autonomous_action:
            case.system_action = None
            case.system_action_overridden_at = _now_iso()

        record = AnalystDecision(
            id=self._next_decision_id,
            case_id=case.case_id,
            txn_id=case.txn_id,
            decision=decision,
            analyst=analyst,
            notes=notes,
            decided_at=_now_iso(),
            is_override=is_override,
        )
        self._next_decision_id += 1
        self._decisions[case.case_id] = record
        self._persist_decisions()

        audit_metadata: dict = {
            "decision": decision,
            "engine_decision": case.decision.value,
            "is_override": is_override,
            "analyst": analyst,
        }
        if high_risk_override:
            audit_metadata["high_risk_override"] = True
            audit_metadata["ring_id"] = case.graph_evidence.ring_id
            audit_metadata["ring_size"] = case.graph_evidence.ring_size
        if reversed_autonomous_action:
            audit_metadata["reversed_autonomous_action"] = AUTO_HOLD_ACTION
        self._log_event(
            case.case_id, case.txn_id, "analyst_decision", analyst or "unknown", audit_metadata
        )

        return record

    def record_autonomous_action(self, case: FraudCase) -> Optional[AuditEvent]:
        """Log the system's own auto-hold as its own distinct, fully
        explainable audit event — event_type="autonomous_action",
        actor="system", never folded into "analyst_decision" or
        "case_created". Records the exact scores that triggered it so the
        decision is inspectable after the fact, not a silent action.

        No-op when the case didn't trigger a hold, and idempotent per case
        (CaseEngine.analyze() re-runs on every GET /cases/{txn_id}, so this
        must not spam the audit trail with a duplicate event on every
        request for the same held case).
        """
        if case.system_action != AUTO_HOLD_ACTION:
            return None
        if any(
            e.case_id == case.case_id and e.event_type == "autonomous_action"
            for e in self._audit_events
        ):
            return None

        metadata: dict = {
            "system_action": case.system_action,
            "engine_decision": case.decision.value,
            "final_score": case.final_score,
            "confidence": case.confidence,
        }
        if case.fraud_dna_match is not None:
            metadata["fraud_dna_similarity_score"] = case.fraud_dna_match.similarity_score

        return self._log_event(
            case.case_id, case.txn_id, "autonomous_action", "system", metadata
        )

    def get_decision(self, case_id: str) -> Optional[AnalystDecision]:
        return self._decisions.get(case_id)

    def get_audit_trail(self, case_id: str) -> list[AuditEvent]:
        return [e for e in self._audit_events if e.case_id == case_id]

    def is_high_risk_override(self, case: FraudCase, decision: str) -> bool:
        """True when `decision` downgrades a case whose graph evidence shows
        a detected ring — an analyst reversing a ring-linked block."""
        if decision not in _VALID_DECISIONS:
            return False
        is_downgrade = _SEVERITY_RANK[decision] < _SEVERITY_RANK[case.decision.value]
        ring_linked = bool(case.graph_evidence and case.graph_evidence.suspicious_cluster)
        return is_downgrade and ring_linked

    # ── Audit logging ───────────────────────────────────────────────

    def _log_event(
        self, case_id: str, txn_id: Optional[str], event_type: str, actor: str, metadata: dict
    ) -> AuditEvent:
        event = AuditEvent(
            id=self._next_audit_id,
            case_id=case_id,
            txn_id=txn_id,
            event_type=event_type,
            actor=actor,
            occurred_at=_now_iso(),
            metadata=metadata,
        )
        self._next_audit_id += 1
        self._audit_events.append(event)
        self._persist_audit()
        return event

    # ── Persistence ──────────────────────────────────────────────────

    def _persist_decisions(self) -> None:
        self._write_json(self._decisions_path, [d.model_dump() for d in self._decisions.values()])

    def _persist_audit(self) -> None:
        self._write_json(self._audit_path, [e.model_dump() for e in self._audit_events])

    @staticmethod
    def _write_json(path: str, data: list) -> None:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _load(self) -> None:
        self._decisions = {}
        if os.path.exists(self._decisions_path):
            try:
                with open(self._decisions_path, "r") as f:
                    data = json.load(f)
                for item in data:
                    record = AnalystDecision(**item)
                    self._decisions[record.case_id] = record
                    self._next_decision_id = max(self._next_decision_id, record.id + 1)
            except (json.JSONDecodeError, KeyError, TypeError):
                self._decisions = {}

        self._audit_events = []
        if os.path.exists(self._audit_path):
            try:
                with open(self._audit_path, "r") as f:
                    data = json.load(f)
                for item in data:
                    event = AuditEvent(**item)
                    self._audit_events.append(event)
                    self._next_audit_id = max(self._next_audit_id, event.id + 1)
            except (json.JSONDecodeError, KeyError, TypeError):
                self._audit_events = []
