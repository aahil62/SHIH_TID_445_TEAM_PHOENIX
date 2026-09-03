"""Ensemble scorer for FraudLens.

Combines per-agent scores into one decision. Takes AgentScore objects in,
not agent instances — it has no import dependency on rule_agent,
velocity_agent, graph_agent, or behavioral_agent, so this file never
conflicts with the branches that build those.
"""

from __future__ import annotations

from fraudlens.models.schemas import AgentScore, Decision, ScoringResult

# Graph evidence is the strongest fraud-ring signal; behavioral and
# velocity carry the anomaly signal; rules catch simple high-risk patterns.
# feature/rules-velocity adds "ml_agent" here in Stage B once it exists —
# unlisted agents fall back to a 0.25 weight below.
WEIGHTS: dict[str, float] = {
    "graph_agent": 0.35,
    "velocity_agent": 0.25,
    "behavioral_agent": 0.20,
    "rule_agent": 0.20,
}

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

        total_weight = 0.0
        weighted_sum = 0.0
        for a in agent_scores:
            w = WEIGHTS.get(a.agent_name, 0.25)
            weighted_sum += a.score * w
            total_weight += w
        final_score = weighted_sum / total_weight if total_weight else 0.0

        # Critical signal boost: one very strong, high-confidence agent
        # shouldn't get diluted into silence by agents that saw nothing.
        max_agent = max(agent_scores, key=lambda a: a.score)
        if max_agent.score >= 0.9 and max_agent.confidence >= 0.8:
            final_score += (max_agent.score - final_score) * 0.7

        final_score = round(min(final_score, 1.0), 4)
        decision = self._decide(final_score)
        confidence = self._compute_confidence(agent_scores, max_agent)

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
