"""Regulatory reference matrix for FraudLens.

REFERENCE CONTEXT ONLY. This module answers "what Indian regulatory
regime would a case like this typically fall under" for an analyst's own
judgment — it is not a compliance engine and makes no claim of actual
regulatory action. Nothing in FraudLens files a Suspicious Transaction
Report with FIU-IND, reports a fraud to the RBI, or notifies CERT-In;
only a human, through the bank's or NBFC's own compliance function, can
do that. Every reference below is phrased as "typically reportable
under..." or equivalent — never "this was reported to...". If a route
or report renders this data, that hedge must render with it.

Grounded in exactly three real frameworks, each cited at the level of
detail this project is confident is accurate (no invented section
numbers or specific obligations beyond this):

- RBI's Master Directions on Fraud Risk Management — require RBI-regulated
  entities (banks, NBFCs) to classify detected frauds, monitor for them
  via an Early Warning Signals framework, and report frauds above
  prescribed thresholds to the RBI, with board-level oversight of the
  fraud risk management function.
- Prevention of Money Laundering Act (PMLA), 2002, Section 12 — reporting
  entities (banks, financial institutions, intermediaries) must maintain
  records of, and furnish, Suspicious Transaction Reports (STRs) to the
  Director, FIU-IND (Financial Intelligence Unit – India).
- CERT-In's 2022 cyber incident reporting directions (effective June
  2022, issued under the IT Act, 2000) — mandate reporting specified
  categories of cyber security incidents, including unauthorised access
  to or unauthorised transactions in banking/financial systems, to
  CERT-In within 6 hours of detection or being made aware of them.
"""

from __future__ import annotations

from fraudlens.models.schemas import Decision, RegulatoryReference

_RBI_FRAUD_RISK_MGMT = RegulatoryReference(
    framework="RBI Master Directions on Fraud Risk Management",
    citation="RBI Master Directions on Fraud Risk Management (regulated entities — banks, NBFCs)",
    relevance=(
        "Cases at this severity typically fall within the fraud classification and Early "
        "Warning Signals monitoring this direction requires of regulated entities."
    ),
    hedge=(
        "Typically falls under the RBI's fraud risk management framework — this is reference "
        "context for the analyst, not a record that anything was filed with the RBI."
    ),
)

_RBI_FRAUD_RISK_MGMT_REVIEW = RegulatoryReference(
    framework="RBI Master Directions on Fraud Risk Management",
    citation="RBI Master Directions on Fraud Risk Management (Early Warning Signals monitoring)",
    relevance=(
        "Cases at review severity are the kind an Early Warning Signals framework is meant to "
        "surface for closer monitoring, short of formal fraud classification."
    ),
    hedge=(
        "Worth monitoring under the RBI's Early Warning Signals framework — reference context "
        "only, not a claim that any monitoring or filing has actually occurred."
    ),
)

_PMLA_STR = RegulatoryReference(
    framework="Prevention of Money Laundering Act (PMLA), 2002",
    citation="PMLA, 2002, Section 12 — Suspicious Transaction Report (STR) obligations",
    relevance=(
        "A blocked or escalated transaction is the kind of activity a reporting entity's "
        "own compliance function would typically assess for STR filing."
    ),
    hedge=(
        "This pattern is typically reportable under PMLA Section 12 as a Suspicious "
        "Transaction Report to FIU-IND — it has not been reported; that determination and "
        "filing belong to the institution's compliance officer, not to FraudLens."
    ),
)

_CERT_IN = RegulatoryReference(
    framework="CERT-In 2022 Cyber Incident Reporting Directions",
    citation="CERT-In directions under the IT Act, 2000 (effective June 2022) — 6-hour reporting window",
    relevance=(
        "The detected pattern involves compromised devices or account credentials — the kind "
        "of unauthorised access CERT-In's directions specifically cover for banking/financial "
        "systems."
    ),
    hedge=(
        "This pattern is typically reportable to CERT-In within 6 hours under its 2022 cyber "
        "incident reporting directions — it has not been reported; only the institution's own "
        "incident response process can do that."
    ),
)

# Fraud DNA fraud_type / Transaction fraud_pattern_type keywords that
# indicate a cyber-enabled pattern (compromised device or credentials,
# unauthorised access) rather than a purely financial-crime pattern —
# the CERT-In directions are scoped to unauthorised access/transactions
# in banking and financial systems specifically, not fraud in general.
_CYBER_ENABLED_KEYWORDS = ("takeover", "device_farm", "device farm")

_DECISION_REFERENCES: dict[Decision, list[RegulatoryReference]] = {
    Decision.CLEAR: [],
    Decision.REVIEW: [_RBI_FRAUD_RISK_MGMT_REVIEW],
    Decision.BLOCK: [_RBI_FRAUD_RISK_MGMT, _PMLA_STR],
    Decision.BLOCK_AND_REPORT: [_RBI_FRAUD_RISK_MGMT, _PMLA_STR],
}


def _is_cyber_enabled(fraud_type: str | None) -> bool:
    if not fraud_type:
        return False
    lowered = fraud_type.lower()
    return any(keyword in lowered for keyword in _CYBER_ENABLED_KEYWORDS)


def get_regulatory_context(
    decision: Decision, fraud_type: str | None = None
) -> list[RegulatoryReference]:
    """Reference-only regulatory context for a case, keyed by decision
    severity and (optionally) the matched Fraud DNA / graph fraud_type.

    `fraud_type` is typically `case.fraud_dna_match.fraud_type` when a
    match exists, or `case.transaction.fraud_pattern_type` as a fallback.
    Cyber-enabled patterns (account takeover, device-farm fraud) add the
    CERT-In reference only at block-level severity — CERT-In's directions
    are scoped to unauthorised access/transactions, not fraud broadly.
    """
    references = list(_DECISION_REFERENCES.get(decision, []))
    if decision in (Decision.BLOCK, Decision.BLOCK_AND_REPORT) and _is_cyber_enabled(fraud_type):
        references.append(_CERT_IN)
    return references
