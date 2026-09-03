"""End-to-end proof: build the shared runtime and score real transactions
from the synthetic dataset.

Run this to see one transaction go from raw data through all five agents,
ring detection, Fraud DNA matching, to a final decision and recommendation.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fraudlens.runtime import build_runtime


def main() -> None:
    runtime = build_runtime()
    print(f"Loaded {len(runtime.transactions)} synthetic transactions.\n")

    ring_txn = next(t for t in runtime.transactions if t.fraud_pattern_type == "fraud_ring")
    normal_txn = next(t for t in runtime.transactions if t.fraud_pattern_type == "normal")

    for label, txn in [("FRAUD RING transaction", ring_txn), ("NORMAL transaction", normal_txn)]:
        case = runtime.engine.analyze(txn.txn_id)
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
