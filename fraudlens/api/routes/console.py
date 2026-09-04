"""System-wide (not per-case) views for the analyst console: dashboard
aggregates, the Fraud DNA pattern library, a global audit log, a reports
list, and a fraud-network summary.

Every number here is derived from the same live runtime every other route
uses — analyzing the full deterministic synthetic dataset once per process
(cached at module level, mirroring stats.py's benchmark cache) rather than
whatever subset of transactions happened to be touched by other endpoints,
so these aggregates don't depend on request order.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any

from fastapi import APIRouter

from fraudlens.api.state import state
from fraudlens.models.schemas import AuditEvent, Decision, FraudCase
from fraudlens.runtime import FraudLensRuntime

router = APIRouter(tags=["console"])

_cache_lock = threading.Lock()
_cache_runtime_id: int | None = None
_all_cases_cache: list[FraudCase] | None = None


def _all_cases(runtime: FraudLensRuntime) -> list[FraudCase]:
    """Every transaction in the fixed dataset, analyzed once. Cached at
    module level since the dataset and models are deterministic for the
    life of a given runtime — recomputing on every dashboard/reports/audit
    request would mean re-running all six agents over ~1,000 transactions
    per page load. Keyed on the runtime's identity (not just "is it None")
    so a fresh runtime — e.g. a new test class's own TestClient rebuilding
    the app's lifespan — invalidates the cache instead of silently reusing
    another runtime's cases.

    Lock-guarded: FastAPI runs sync routes in a thread pool, and the
    frontend's console pages fire dashboard/network/reports/audit requests
    in parallel — without this lock, two threads could both see a stale
    cache and call runtime.analyze() concurrently, mutating CaseEngine's
    internal cases dict from two threads at once ("dictionary changed size
    during iteration", a real crash hit and reproduced during live
    testing, not a hypothetical)."""
    global _cache_runtime_id, _all_cases_cache
    with _cache_lock:
        if _cache_runtime_id != id(runtime):
            _all_cases_cache = [runtime.analyze(t.txn_id) for t in runtime.transactions]
            _cache_runtime_id = id(runtime)
        return _all_cases_cache


# ── Dashboard ────────────────────────────────────────────────────────────

_REPORT_TYPE_BY_DECISION: dict[str, str] = {
    Decision.BLOCK_AND_REPORT.value: "SAR Draft",
    Decision.BLOCK.value: "Regulatory Report",
    Decision.REVIEW.value: "Investigation Report",
    Decision.CLEAR.value: "Case Summary",
}


@router.get("/stats/dashboard")
def get_dashboard() -> dict[str, Any]:
    runtime = state.runtime
    cases = _all_cases(runtime)

    critical_alerts = sum(1 for c in cases if c.decision == Decision.BLOCK_AND_REPORT)
    pending_reviews = sum(1 for c in cases if c.decision == Decision.REVIEW)
    blocked = sum(1 for c in cases if c.decision in (Decision.BLOCK, Decision.BLOCK_AND_REPORT))
    investigations = sum(1 for c in cases if c.decision != Decision.CLEAR)
    ring_ids = {
        c.graph_evidence.ring_id
        for c in cases
        if c.graph_evidence and c.graph_evidence.suspicious_cluster and c.graph_evidence.ring_id
    }

    by_day: dict[str, list[float]] = defaultdict(list)
    for c in cases:
        day = c.transaction.timestamp[:10]
        by_day[day].append(c.final_score)
    risk_trend = [
        {"date": day, "avg_score": sum(scores) / len(scores), "count": len(scores)}
        for day, scores in sorted(by_day.items())
    ][-14:]

    agent_totals: dict[str, list[float]] = defaultdict(list)
    for c in cases:
        for a in c.agent_scores:
            if a.confidence > 0.0:  # skip abstains (e.g. fraud_dna_agent on non-ring cases)
                agent_totals[a.agent_name].append(a.score)
    agent_averages = [
        {"agent_name": name, "avg_score": sum(scores) / len(scores)}
        for name, scores in sorted(agent_totals.items())
    ]

    return {
        "critical_alerts": critical_alerts,
        "pending_reviews": pending_reviews,
        "blocked_transactions": blocked,
        "investigations": investigations,
        "fraud_rings": len(ring_ids),
        "transactions_analyzed": len(cases),
        "risk_trend": risk_trend,
        "agent_averages": agent_averages,
    }


# ── Fraud DNA pattern library ───────────────────────────────────────────


@router.get("/dna/patterns")
def get_dna_patterns() -> dict[str, Any]:
    runtime = state.runtime
    cases = _all_cases(runtime)

    matches_by_ring: dict[str, list[float]] = defaultdict(list)
    for c in cases:
        if c.fraud_dna_match:
            matches_by_ring[c.fraud_dna_match.matched_ring_id].append(
                c.fraud_dna_match.similarity_score
            )

    patterns = []
    for profile in runtime.dna_store.all():
        scores = matches_by_ring.get(profile.ring_id, [])
        patterns.append({
            "ring_id": profile.ring_id,
            "fraud_type": profile.fraud_type,
            "name": profile.fraud_type.replace("_", " ").title(),
            "description": profile.modus_operandi,
            "matches": len(scores),
            "avg_confidence": (sum(scores) / len(scores)) if scores else None,
        })
    patterns.sort(key=lambda p: p["matches"], reverse=True)
    return {"patterns": patterns}


# ── Global audit log ─────────────────────────────────────────────────────

_TONE_BY_EVENT: dict[str, str] = {
    "case_created": "blue",
    "autonomous_action": "amber",
    "analyst_decision": "green",
}

_DECISION_TONE: dict[str, str] = {
    Decision.CLEAR.value: "green",
    Decision.REVIEW.value: "amber",
    Decision.BLOCK.value: "red",
    Decision.BLOCK_AND_REPORT.value: "red",
}


def _describe_event(event: AuditEvent) -> tuple[str, str]:
    """Plain-language text + a tone (red/amber/green/blue) for one audit
    event, for a human-readable global timeline — the raw event_type and
    metadata are still available on the event itself for anything that
    needs the structured form."""
    meta = event.metadata
    if event.event_type == "case_created":
        ring_id = meta.get("ring_id")
        text = (
            f"Case created — engine recommended {meta.get('engine_decision', '?').upper()}"
            + (f", ring {ring_id} detected" if ring_id else "")
        )
        return text, _DECISION_TONE.get(meta.get("engine_decision", ""), "blue")
    if event.event_type == "autonomous_action":
        text = (
            f"System auto-held case (score {meta.get('final_score', 0):.0%}, "
            f"confidence {meta.get('confidence', 0):.0%})"
        )
        return text, "amber"
    if event.event_type == "analyst_decision":
        analyst = meta.get("analyst") or "unknown"
        decision = str(meta.get("decision", "")).upper()
        if meta.get("is_false_positive"):
            # Distinct from a routine "recorded decision: CLEAR" — this
            # case was actually flagged, investigated, and confirmed to
            # NOT be fraud, not a transaction that was always fine.
            text = f"{analyst} marked case as a false positive — did not represent actual fraud"
            return text, "blue"
        if meta.get("reversed_autonomous_action"):
            text = f"{analyst} reviewed the auto-held case and recorded {decision}"
        elif meta.get("high_risk_override"):
            text = f"{analyst} overrode a ring-linked case to {decision}"
        else:
            text = f"{analyst} recorded decision: {decision}"
        return text, _DECISION_TONE.get(meta.get("decision", ""), "blue")
    return event.event_type.replace("_", " ").title(), "blue"


@router.get("/audit")
def get_global_audit(limit: int = 100) -> dict[str, Any]:
    runtime = state.runtime
    _all_cases(runtime)  # ensure every case (and its audit events) exists
    events = sorted(
        runtime.decision_workflow.get_all_events(), key=lambda e: e.occurred_at, reverse=True
    )[:limit]
    rows = []
    for e in events:
        text, tone = _describe_event(e)
        rows.append({
            "id": e.id,
            "case_id": e.case_id,
            "txn_id": e.txn_id,
            "event_type": e.event_type,
            "actor": e.actor,
            "occurred_at": e.occurred_at,
            "text": text,
            "tone": tone,
        })
    return {"events": rows}


# ── Reports list ─────────────────────────────────────────────────────────


@router.get("/reports")
def list_reports(limit: int = 50) -> dict[str, Any]:
    runtime = state.runtime
    cases = _all_cases(runtime)
    # created_at is wall-clock at analysis time, not transaction time — all
    # ~1,000 cases get built within the same cache-warming pass, seconds
    # apart at most, so it carries no real ordering signal here. Risk score
    # does: highest-risk cases are the ones most likely to need a report.
    cases = sorted(cases, key=lambda c: c.final_score, reverse=True)[:limit]

    rows = []
    for c in cases:
        decision_record = runtime.decision_workflow.get_decision(c.case_id)
        if decision_record:
            # A confirmed false positive reads identically to a routine
            # "CLEAR" otherwise — this case was actually flagged and
            # investigated, not a transaction that was always fine.
            status = "FALSE POSITIVE" if decision_record.is_false_positive else decision_record.decision.upper()
            analyst = decision_record.analyst or "—"
        elif c.system_action:
            status = "AUTO-HELD"
            analyst = "—"
        else:
            status = c.decision.value.upper()
            analyst = "—"
        rows.append({
            "txn_id": c.txn_id,
            "case_id": c.case_id,
            "risk_pct": c.final_score,
            "status": status,
            "tone": _DECISION_TONE.get(c.decision.value, "blue"),
            "analyst": analyst,
            "created_at": c.created_at,
            "report_type": _REPORT_TYPE_BY_DECISION.get(c.decision.value, "Case Summary"),
        })
    return {"rows": rows}


# ── Fraud network summary ───────────────────────────────────────────────


@router.get("/network/summary")
def get_network_summary() -> dict[str, Any]:
    runtime = state.runtime
    cases = _all_cases(runtime)

    ring_cases: dict[str, FraudCase] = {}
    for c in cases:
        ge = c.graph_evidence
        if ge and ge.suspicious_cluster and ge.ring_id and ge.ring_id not in ring_cases:
            ring_cases[ge.ring_id] = c

    linked_accounts = set()
    shared_devices = set()
    shared_ips = set()
    top_dna_pct = 0.0
    rings = []
    for ring_id, c in sorted(ring_cases.items(), key=lambda kv: kv[1].graph_evidence.ring_size, reverse=True):
        ge = c.graph_evidence
        linked_accounts.update(ge.connected_accounts)
        shared_devices.update(ge.shared_devices)
        shared_ips.update(ge.shared_ips)
        dna_pct = c.fraud_dna_match.similarity_score if c.fraud_dna_match else 0.0
        top_dna_pct = max(top_dna_pct, dna_pct)
        rings.append({
            "ring_id": ring_id,
            "txn_id": c.txn_id,
            "ring_size": ge.ring_size,
            "shared_devices": len(ge.shared_devices),
            "shared_ips": len(ge.shared_ips),
            "fraud_type": c.fraud_dna_match.fraud_type if c.fraud_dna_match else None,
            "dna_similarity": dna_pct or None,
        })

    return {
        "ring_count": len(ring_cases),
        "linked_accounts": len(linked_accounts),
        "shared_devices": len(shared_devices),
        "shared_ips": len(shared_ips),
        "top_dna_match_pct": top_dna_pct or None,
        "rings": rings,
    }
