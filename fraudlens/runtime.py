"""Runtime assembly for FraudLens.

Wires every agent, the case engine, the decision workflow, and the report
generator into one object. scripts/run_demo.py and the API both build off
this instead of hand-assembling agents themselves, so there's exactly one
place that knows how the pieces fit together.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fraudlens.core.cases.case_engine import CaseEngine
from fraudlens.core.cases.decision_workflow import DecisionWorkflow
from fraudlens.core.dna.store import FraudDNAStore
from fraudlens.core.reports.generator import ReportGenerator
from fraudlens.core.scoring.behavioral_agent import BehavioralAgent
from fraudlens.core.scoring.graph_agent import GraphAgent
from fraudlens.core.scoring.ml_agent import MLAgent
from fraudlens.core.scoring.rule_agent import RuleAgent
from fraudlens.core.scoring.velocity_agent import VelocityAgent
from fraudlens.data.synthetic_generator import generate_synthetic_transactions
from fraudlens.models.schemas import FraudCase, Transaction


@dataclass(frozen=True)
class RuntimeConfig:
    seed: int | None = 42
    cases_path: str = "fraudlens/data/cases.json"
    dna_store_path: str = "fraudlens/data/fraud_dna_library.json"
    decisions_path: str = "fraudlens/data/analyst_decisions.json"
    audit_path: str = "fraudlens/data/audit_log.json"


@dataclass
class FraudLensRuntime:
    engine: CaseEngine
    decision_workflow: DecisionWorkflow
    report_generator: ReportGenerator
    transactions: list[Transaction]
    dna_store: FraudDNAStore = field(repr=False)

    def transaction(self, txn_id: str) -> Transaction | None:
        return next((t for t in self.transactions if t.txn_id == txn_id), None)

    def analyze(self, txn_id: str) -> FraudCase:
        """engine.analyze() plus recording any autonomous action it
        triggers as its own audit event. Every route should call this
        instead of `engine.analyze()` directly, so the audit trail doesn't
        depend on which endpoint happened to touch the case first."""
        case = self.engine.analyze(txn_id)
        self.decision_workflow.record_autonomous_action(case)
        return case


def build_runtime(config: RuntimeConfig | None = None) -> FraudLensRuntime:
    """Build the complete in-process FraudLens runtime.

    Deterministic by default (fixed seed) so every run — API startup, the
    demo script, a teammate's laptop — sees the same synthetic dataset and
    therefore comparable case IDs during the hackathon.
    """
    config = config or RuntimeConfig()
    transactions = generate_synthetic_transactions(seed=config.seed)

    rule_agent = RuleAgent()
    velocity_agent = VelocityAgent()
    velocity_agent.set_transactions(transactions)
    graph_agent = GraphAgent()
    graph_agent.build_index(transactions)
    behavioral_agent = BehavioralAgent()
    behavioral_agent.build_profiles(transactions)
    ml_agent = MLAgent()
    ml_agent.fit(transactions)

    dna_store = FraudDNAStore(path=config.dna_store_path)
    engine = CaseEngine(
        transactions,
        agents=[rule_agent, velocity_agent, graph_agent, behavioral_agent, ml_agent],
        cases_path=config.cases_path,
        dna_store=dna_store,
    )

    return FraudLensRuntime(
        engine=engine,
        decision_workflow=DecisionWorkflow(
            decisions_path=config.decisions_path,
            audit_path=config.audit_path,
        ),
        report_generator=ReportGenerator(),
        transactions=transactions,
        dna_store=dna_store,
    )
