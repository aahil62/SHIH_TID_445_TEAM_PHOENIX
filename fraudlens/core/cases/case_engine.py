"""Case engine — orchestrates registered agents into a FraudCase.

Fraud DNA is computed *before* the ensemble runs, not after: graph
evidence (ring detection) is the only real gate for whether Fraud DNA
applies at all, so it's built unconditionally first, then
fraud_dna_agent's score is combined into the *same* ensemble.combine()
call as the five direct-scoring agents. That's what makes a confirmed
historical match actually move the decision, instead of only appending
text to a decision the other five agents already finalized.

confirm_fraud_dna() closes the loop the other direction: when an analyst
confirms a ring-linked case as real fraud, its profile is added to the
library so the *next* similar ring — under different accounts — matches
against it. The library starts with 5 seed typologies and gets no
smarter than that until real confirmed cases start feeding back in.
"""

from __future__ import annotations

import json
import os

from fraudlens.core.dna.agent import score_fraud_dna
from fraudlens.core.dna.extractor import FraudDNAExtractor
from fraudlens.core.dna.matcher import FraudDNAMatcher
from fraudlens.core.dna.store import FraudDNAStore
from fraudlens.core.graph.builder import GraphBuilder
from fraudlens.core.scoring.base import ScoringAgent
from fraudlens.core.scoring.ensemble import EnsembleScorer
from fraudlens.models.schemas import (
    Decision,
    FraudCase,
    FraudDNAMatch,
    FraudDNAProfile,
    FraudGraph,
    GraphEvidence,
    Transaction,
)

_RECOMMENDED_ACTIONS: dict[Decision, str] = {
    Decision.CLEAR: "No action required. Transaction appears normal.",
    Decision.REVIEW: (
        "Flag for manual review. Assign to analyst for investigation. "
        "Monitor account for 48 hours."
    ),
    Decision.BLOCK: (
        "Block transaction immediately. Notify account holder. "
        "Initiate enhanced due diligence."
    ),
    Decision.BLOCK_AND_REPORT: (
        "Block transaction, freeze account for review, prepare the case evidence, "
        "and escalate to the compliance team for immediate review."
    ),
}


class CaseEngine:
    def __init__(
        self,
        transactions: list[Transaction],
        agents: list[ScoringAgent] | None = None,
        cases_path: str = "fraudlens/data/cases.json",
        graph_builder: GraphBuilder | None = None,
        dna_store: FraudDNAStore | None = None,
        dna_matcher: FraudDNAMatcher | None = None,
    ) -> None:
        self._txn_map: dict[str, Transaction] = {t.txn_id: t for t in transactions}
        self._agents: list[ScoringAgent] = agents or []
        self._ensemble = EnsembleScorer()
        self._cases_path = cases_path
        self._cases: dict[str, FraudCase] = {}
        self._load_cases()

        self._graph_builder = graph_builder or GraphBuilder()
        self._graph_builder.build(transactions)
        self._dna_extractor = FraudDNAExtractor()
        self._dna_store = dna_store or FraudDNAStore()
        self._dna_matcher = dna_matcher or FraudDNAMatcher(self._dna_store)

    def analyze(self, txn_id: str) -> FraudCase:
        """Full pipeline for one transaction: score, evaluate, persist."""
        txn = self._txn_map.get(txn_id)
        if txn is None:
            raise ValueError(f"Transaction {txn_id} not found")

        # Graph evidence first and unconditionally — ring presence is the
        # only real gate for Fraud DNA, not the other agents' score.
        graph_evidence = self._build_graph_evidence(txn_id)
        ring_txns = self._ring_transactions(graph_evidence)
        dna_agent_score, fraud_dna_match = score_fraud_dna(
            graph_evidence, ring_txns, self._dna_extractor, self._dna_matcher,
        )

        agent_scores = [agent.score(txn) for agent in self._agents] + [dna_agent_score]
        result = self._ensemble.combine(agent_scores)

        case = FraudCase(
            case_id=f"CASE-{txn_id}",
            txn_id=txn_id,
            transaction=txn,
            final_score=result.final_score,
            decision=result.decision,
            confidence=result.confidence,
            agent_scores=result.agent_scores,
            explanation_reasons=result.explanation_reasons,
            graph_evidence=graph_evidence,
            fraud_dna_match=fraud_dna_match,
            recommended_action=self._recommended_action(result.decision, fraud_dna_match),
        )
        self._cases[case.case_id] = case
        self._persist_cases()
        return case

    def confirm_fraud_dna(self, txn_id: str) -> FraudDNAProfile | None:
        """Add a ring-linked case's profile to the Fraud DNA library.

        Call this when an analyst confirms a case as real fraud (see
        api/routes/decisions.py) — not automatically on every engine
        decision, so the library only grows from validated cases, not raw
        unconfirmed alerts. Idempotent: re-confirming the same ring is a
        no-op. Returns None if the case has no detected ring to fingerprint.
        """
        case = self.get_case_by_txn(txn_id)
        if case is None or case.graph_evidence is None:
            return None

        confirmed_id = f"CONFIRMED-{case.graph_evidence.ring_id or txn_id}"
        existing = self._dna_store.get(confirmed_id)
        if existing is not None:
            return existing

        ring_txns = self._ring_transactions(case.graph_evidence)
        if not ring_txns:
            return None

        profile = self._dna_extractor.extract_profile(ring_txns, case.graph_evidence)
        profile.ring_id = confirmed_id
        profile.description = f"Analyst-confirmed fraud from {txn_id}: {profile.description}"
        self._dna_store.add(profile)
        return profile

    def get_fraud_graph(self, txn_id: str) -> tuple[FraudGraph, str] | None:
        """The real node/edge graph for a transaction's detected ring, plus
        the node id of the transaction's own account (for highlighting it).
        None when there's no detected ring — used by GET
        /cases/{txn_id}/graph, never by scoring (this is presentation
        data only, computed from the same GraphBuilder _build_graph_evidence
        already uses)."""
        try:
            graph = self._graph_builder.get_ring_graph(txn_id)
        except ValueError:
            return None
        if graph is None:
            return None
        flagged = self._graph_builder.flagged_account_node_id(txn_id)
        if flagged is None:
            return None
        return graph, flagged

    def get_case(self, case_id: str) -> FraudCase | None:
        return self._cases.get(case_id)

    def get_case_by_txn(self, txn_id: str) -> FraudCase | None:
        return self._cases.get(f"CASE-{txn_id}")

    def list_cases(self) -> list[FraudCase]:
        return list(self._cases.values())

    # ── Stage B extension points (feature/graph-behavioral) ────────────

    def _build_graph_evidence(self, txn_id: str) -> GraphEvidence | None:
        try:
            return self._graph_builder.get_graph_evidence(txn_id)
        except ValueError:
            return None

    def _ring_transactions(self, evidence: GraphEvidence | None) -> list[Transaction]:
        if evidence is None:
            return []
        ring_accounts = set(evidence.connected_accounts)
        return [t for t in self._txn_map.values() if t.account_id in ring_accounts]

    # ── Recommendations ──────────────────────────────────────────────

    @staticmethod
    def _recommended_action(decision: Decision, fraud_dna_match: FraudDNAMatch | None) -> str:
        action = _RECOMMENDED_ACTIONS.get(decision, "Review required.")
        if fraud_dna_match and fraud_dna_match.similarity_score >= 0.70:
            action += (
                f"\n\nFraud DNA Alert: {fraud_dna_match.similarity_score:.0%} match to known "
                f"'{fraud_dna_match.fraud_type}' pattern ({fraud_dna_match.matched_ring_id}). "
                f"{fraud_dna_match.recommendation}"
            )
        return action

    # ── Persistence ──────────────────────────────────────────────────

    def _persist_cases(self) -> None:
        directory = os.path.dirname(self._cases_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        data = [c.model_dump() for c in self._cases.values()]
        with open(self._cases_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _load_cases(self) -> None:
        if not os.path.exists(self._cases_path):
            return
        try:
            with open(self._cases_path, "r") as f:
                data = json.load(f)
            for item in data:
                case = FraudCase(**item)
                self._cases[case.case_id] = case
        except (json.JSONDecodeError, KeyError, TypeError):
            self._cases = {}
