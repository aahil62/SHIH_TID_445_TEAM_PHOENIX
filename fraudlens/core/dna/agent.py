"""Fraud DNA as a scoring signal.

Not a standalone ScoringAgent — it structurally can't be. A ring has to be
detected before it can be fingerprinted, so unlike rule/velocity/graph/
behavioral/ml agents, this can't score a transaction in isolation; it
depends on graph evidence computed first. What it *can* do is contribute
one more AgentScore into the same ensemble.combine() call as those five,
so a confirmed historical match actually influences the decision instead
of only decorating the recommendation text after the decision is final.

On the large majority of transactions (no detected ring), this abstains
rather than voting a confident "clear" — see ensemble.ABSTAIN_CONFIDENCE
for why that distinction matters.
"""

from __future__ import annotations

from fraudlens.core.dna.extractor import FraudDNAExtractor
from fraudlens.core.dna.matcher import FraudDNAMatcher
from fraudlens.models.schemas import AgentScore, FraudDNAMatch, GraphEvidence, Transaction

NAME = "fraud_dna_agent"


def score_fraud_dna(
    graph_evidence: GraphEvidence | None,
    ring_transactions: list[Transaction],
    extractor: FraudDNAExtractor,
    matcher: FraudDNAMatcher,
) -> tuple[AgentScore, FraudDNAMatch | None]:
    """Returns the ensemble-facing AgentScore, plus the full FraudDNAMatch
    (or None) for the case record and report — same call does both so the
    extractor/matcher only ever run once per transaction."""
    if graph_evidence is None or not ring_transactions:
        return (
            AgentScore(
                agent_name=NAME,
                score=0.0,
                confidence=0.0,
                reasons=["No ring detected — Fraud DNA not applicable"],
            ),
            None,
        )

    profile = extractor.extract_profile(ring_transactions, graph_evidence)
    match = matcher.match(profile)

    if match is None:
        return (
            AgentScore(
                agent_name=NAME,
                score=0.0,
                confidence=0.0,
                reasons=["Ring detected but no confident match against the known-pattern library"],
            ),
            None,
        )

    return (
        AgentScore(
            agent_name=NAME,
            score=match.similarity_score,
            confidence=match.similarity_score,
            reasons=[
                f"{match.similarity_score:.0%} match to known '{match.fraud_type}' "
                f"pattern ({match.matched_ring_id})"
            ],
            metadata={"matched_ring_id": match.matched_ring_id, "fraud_type": match.fraud_type},
        ),
        match,
    )
