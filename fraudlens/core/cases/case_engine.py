"""Case engine — orchestrates registered agents into a FraudCase.

Stage A scope: run whatever ScoringAgents are registered, combine them via
the ensemble, and assemble a case. Stage B fills in the two extension
points below: _build_graph_evidence delegates to GraphBuilder's own
get_graph_evidence(), and _run_dna_analysis feeds the ring's transactions
through FraudDNAExtractor and FraudDNAMatcher. Both stay None for a
transaction with no detected ring — this class's shape doesn't change,
only those two methods do.
"""

from __future__ import annotations

import json
import os

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
        self._dna_matcher = dna_matcher or FraudDNAMatcher(dna_store or FraudDNAStore())

    def analyze(self, txn_id: str) -> FraudCase:
        """Full pipeline for one transaction: score, evaluate, persist."""
        txn = self._txn_map.get(txn_id)
        if txn is None:
            raise ValueError(f"Transaction {txn_id} not found")

        agent_scores = [agent.score(txn) for agent in self._agents]
        result = self._ensemble.combine(agent_scores)

        graph_evidence = self._build_graph_evidence(txn_id)
        fraud_dna_match: FraudDNAMatch | None = None
        if result.final_score >= 0.30:
            fraud_dna_match = self._run_dna_analysis(txn_id)

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

    def _run_dna_analysis(self, txn_id: str) -> FraudDNAMatch | None:
        evidence = self._build_graph_evidence(txn_id)
        if evidence is None:
            return None
        ring_accounts = set(evidence.connected_accounts)
        ring_txns = [t for t in self._txn_map.values() if t.account_id in ring_accounts]
        if not ring_txns:
            return None
        profile = self._dna_extractor.extract_profile(ring_txns, evidence)
        return self._dna_matcher.match(profile)

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
