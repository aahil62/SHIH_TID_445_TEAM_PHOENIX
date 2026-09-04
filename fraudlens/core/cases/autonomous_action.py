"""Bounded autonomous action for FraudLens.

Suggest-only stays the default: every real decision is made by a human via
POST /decisions -> DecisionWorkflow.submit_decision(). This module adds one
narrow, conservative exception on top of that — not a replacement for
human review, an addition for the small minority of cases with
overwhelming, multi-signal certainty.

The bar is deliberately a conjunction, not a single threshold: a case only
triggers when final_score, confidence, AND (when Fraud DNA has an opinion
at all) fraud_dna_match.similarity_score all independently clear a high
bar together. One number crossing one threshold — even a final_score of
0.99 alone — is not enough; the whole point is that a false positive here
should require multiple independent signals to be wrong at once.

The action itself is "auto_held", never "auto_blocked" or "auto_rejected"
— there is no real payment gateway behind this system, so the only honest
framing is "held pending review." This module never claims to have
stopped a real transaction, and nothing downstream should either.

An auto-held case is not final. See DecisionWorkflow.record_autonomous_action
for the audit trail it produces, and DecisionWorkflow.submit_decision for
how a human analyst reverses it — cleanly, and permanently, the moment
they record a real decision on the case.
"""

from __future__ import annotations

from typing import Optional

from fraudlens.models.schemas import FraudCase

# The one system_action value this module ever produces. Named "held", not
# "blocked" — see module docstring.
AUTO_HOLD_ACTION = "auto_held"

# All three must clear together (see module docstring) — tuned so the
# action only ever fires at the very top of the confidence range, where a
# false positive is genuinely least likely.
FINAL_SCORE_THRESHOLD = 0.90
CONFIDENCE_THRESHOLD = 0.85
FRAUD_DNA_SIMILARITY_THRESHOLD = 0.85


def evaluate_autonomous_action(case: FraudCase) -> Optional[str]:
    """Return AUTO_HOLD_ACTION when `case` clears every corroborating
    threshold at once, else None.

    Pure function of the case's own scores — safe to recompute on every
    re-analysis of the same transaction, since the same inputs always
    produce the same verdict.
    """
    if case.final_score < FINAL_SCORE_THRESHOLD:
        return None
    if case.confidence < CONFIDENCE_THRESHOLD:
        return None

    dna = case.fraud_dna_match
    if dna is not None and dna.similarity_score < FRAUD_DNA_SIMILARITY_THRESHOLD:
        return None

    return AUTO_HOLD_ACTION
