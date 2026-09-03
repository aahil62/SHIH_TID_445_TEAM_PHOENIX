"""Ensemble scorer for FraudLens.

Combines per-agent scores into one decision. Takes AgentScore objects in,
not agent instances — it has no import dependency on rule_agent,
velocity_agent, graph_agent, or behavioral_agent, so this file never
conflicts with the branches that build those.
"""

from __future__ import annotations

from fraudlens.models.schemas import AgentScore, Decision, ScoringResult

# Graph evidence is the strongest fraud-ring signal; behavioral and
# velocity carry the anomaly signal; ml_agent learns nonlinear combinations
# of a transaction's own static features; rules catch simple high-risk
# patterns. Unlisted agents fall back to a 0.25 weight below.
#
# ml_agent's weight (0.35, matching graph_agent) is benchmarked, not
# guessed: fraudlens/evaluation/benchmark.py shows ensemble precision/
# recall/F1 are flat from 0.20-0.50 (the critical-signal boost below
# already dominates threshold-level decisions), but AUC-PR rises
# 0.9500 -> 0.9654 at 0.35 and keeps climbing past it. Not pushed
# higher than graph_agent's weight — that would start over-concentrating
# the ensemble on one model instead of staying genuinely multi-signal,
# for AUC-PR gains past this point that risk overfitting to one
# benchmark split. Re-check this if the benchmark's dataset composition
# changes meaningfully.
#
# fraud_dna_agent matches graph_agent/ml_agent's weight deliberately: a
# confirmed match against the known-pattern library is institutional
# memory, not a fresh guess, so when it fires it should carry at least as
# much weight as the strongest statistical signals. It abstains (see
# ABSTAIN_CONFIDENCE below) on the large majority of transactions that
# aren't part of a detected ring, so this weight only ever applies to the
# minority of cases where it actually has an opinion.
WEIGHTS: dict[str, float] = {
    "graph_agent": 0.35,
    "velocity_agent": 0.25,
    "behavioral_agent": 0.20,
    "rule_agent": 0.20,
    "ml_agent": 0.35,
    "fraud_dna_agent": 0.35,
}

# An agent reports confidence == 0.0 to mean "not applicable to this
# transaction," not "confidently clear." Fraud DNA is the first agent
# that needs this: most transactions aren't part of any detected ring, so
# it has nothing to compare. Without this exclusion, an abstaining
# agent's implicit 0.0 score would count as a confident "not fraud" vote
# in the weighted average — actively dragging down the score for exactly
# the novel-pattern transactions where the other agents are the only
# defense. Treated as a genuine abstention, excluded from both the
# weighted average and the confidence spread, but still surfaced in
# explanation_reasons so an analyst can see it was checked.
ABSTAIN_CONFIDENCE = 0.0

_BLOCK_AND_REPORT_THRESHOLD = 0.80
_BLOCK_THRESHOLD = 0.60
_REVIEW_THRESHOLD = 0.30


class EnsembleScorer:
    """Weighted-average ensemble over however many agents are registered."""

    def combine(self, agent_scores: list[AgentScore]) -> ScoringResult:
        if not agent_scores:
            return ScoringResult(
                final_score=0.0,
                decision=Decision.CLEAR,
                confidence=0.0,
                agent_scores=[],
                explanation_reasons=["No scoring agents registered"],
            )

        usable = [a for a in agent_scores if a.confidence > ABSTAIN_CONFIDENCE]
        if not usable:
            # Every agent abstained (only possible if fraud_dna_agent is the
            # sole registered agent and found nothing) — fall back to the
            # full list rather than divide by zero.
            usable = agent_scores

        total_weight = 0.0
        weighted_sum = 0.0
        for a in usable:
            w = WEIGHTS.get(a.agent_name, 0.25)
            weighted_sum += a.score * w
            total_weight += w
        final_score = weighted_sum / total_weight if total_weight else 0.0

        # Critical signal boost: one very strong, high-confidence agent
        # shouldn't get diluted into silence by agents that saw nothing.
        max_agent = max(usable, key=lambda a: a.score)
        if max_agent.score >= 0.9 and max_agent.confidence >= 0.8:
            final_score += (max_agent.score - final_score) * 0.7

        final_score = round(min(final_score, 1.0), 4)
        decision = self._decide(final_score)
        confidence = self._compute_confidence(usable, max_agent)

        reasons: list[str] = []
        for a in agent_scores:
            if a.reasons:
                reasons.extend(f"[{a.agent_name}] {r}" for r in a.reasons)
            else:
                reasons.append(f"[{a.agent_name}] No anomalies detected (score: {a.score:.2f})")

        return ScoringResult(
            final_score=final_score,
            decision=decision,
            confidence=confidence,
            agent_scores=agent_scores,
            explanation_reasons=reasons,
        )

    @staticmethod
    def _decide(score: float) -> Decision:
        if score >= _BLOCK_AND_REPORT_THRESHOLD:
            return Decision.BLOCK_AND_REPORT
        if score >= _BLOCK_THRESHOLD:
            return Decision.BLOCK
        if score >= _REVIEW_THRESHOLD:
            return Decision.REVIEW
        return Decision.CLEAR

    @staticmethod
    def _compute_confidence(agent_scores: list[AgentScore], max_agent: AgentScore) -> float:
        """Agents agreeing (low spread) implies confidence; one strong,
        high-confidence signal is trusted even if others disagree."""
        scores = [a.score for a in agent_scores]
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        confidence = max(0.0, min(1.0, 1.0 - variance ** 0.5))

        if max_agent.score >= 0.9 and max_agent.confidence >= 0.8:
            confidence = max(confidence, 0.85)

        return round(confidence, 4)
