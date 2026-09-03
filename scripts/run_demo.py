"""End-to-end proof: assemble every merged agent plus the graph and Fraud
DNA layers into the case engine, and score real transactions from the
synthetic dataset.

Run this to see one transaction go from raw data through all four agents,
ring detection, Fraud DNA matching, to a final decision and recommendation.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fraudlens.core.cases.case_engine import CaseEngine
from fraudlens.core.scoring.behavioral_agent import BehavioralAgent
from fraudlens.core.scoring.graph_agent import GraphAgent
from fraudlens.core.scoring.rule_agent import RuleAgent
from fraudlens.core.scoring.velocity_agent import VelocityAgent
from fraudlens.data.synthetic_generator import generate_synthetic_transactions


def main() -> None:
    transactions = generate_synthetic_transactions(
        num_normal=200,
        num_high_amount=10,
        num_risky_merchant=10,
        num_odd_hour=8,
        num_card_testing_bursts=4,
        num_high_velocity_bursts=4,
        num_fraud_rings=3,
    )
    print(f"Generated {len(transactions)} synthetic transactions.\n")

    rule_agent = RuleAgent()
    velocity_agent = VelocityAgent()
    velocity_agent.set_transactions(transactions)
    graph_agent = GraphAgent()
    graph_agent.build_index(transactions)
    behavioral_agent = BehavioralAgent()
    behavioral_agent.build_profiles(transactions)

    engine = CaseEngine(
        transactions,
        agents=[rule_agent, velocity_agent, graph_agent, behavioral_agent],
        cases_path="fraudlens/data/cases.json",
    )

    ring_txn = next(t for t in transactions if t.fraud_pattern_type == "fraud_ring")
    normal_txn = next(t for t in transactions if t.fraud_pattern_type == "normal")

    for label, txn in [("FRAUD RING transaction", ring_txn), ("NORMAL transaction", normal_txn)]:
        case = engine.analyze(txn.txn_id)
        print(f"=== {label}: {txn.txn_id} (account {txn.account_id}) ===")
        print(f"  final_score = {case.final_score:.3f}   decision = {case.decision.value}   confidence = {case.confidence:.3f}")
        for score in case.agent_scores:
            print(f"    [{score.agent_name}] {score.score:.2f} — {score.reasons[:1]}")
        if case.graph_evidence:
            ge = case.graph_evidence
            print(f"  graph_evidence: ring_size={ge.ring_size} ({ge.ring_id}) — {ge.evidence_summary}")
        if case.fraud_dna_match:
            dna = case.fraud_dna_match
            print(f"  fraud_dna_match: {dna.similarity_score:.0%} match to '{dna.fraud_type}' ({dna.matched_ring_id})")
        print(f"  recommended_action:\n    {case.recommended_action.replace(chr(10), chr(10) + '    ')}")
        print()


if __name__ == "__main__":
    main()
