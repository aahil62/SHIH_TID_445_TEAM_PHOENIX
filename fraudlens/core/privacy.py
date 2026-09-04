"""Masking helpers for anything that leaves the engine toward an API
response or a report — account IDs, device IDs, IPs. Scoring agents work
on raw data; nothing outward-facing should."""

from __future__ import annotations

import hashlib
from typing import Any, Optional

from fraudlens.models.schemas import AnalystDecision, FraudCase, FraudGraph, Transaction


def mask_identifier(value: str, visible: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= visible:
        return "•" * len(value)
    if "-" in value:
        prefix = value.split("-", 1)[0]
        return f"{prefix}-••{value[-visible:]}"
    return f"{value[:2]}••{value[-visible:]}"


def mask_ip(value: str) -> str:
    parts = value.split(".")
    if len(parts) == 4:
        return f"••.••.{parts[2]}.{parts[3]}"
    return mask_identifier(value)


def public_transaction(txn: Transaction) -> dict[str, Any]:
    return {
        "txn_id": txn.txn_id,
        "account_id": mask_identifier(txn.account_id),
        "amount": txn.amount,
        "merchant_id": mask_identifier(txn.merchant_id),
        "merchant_category": txn.merchant_category,
        "device_id": mask_identifier(txn.device_id),
        "ip_address": mask_ip(txn.ip_address),
        "timestamp": txn.timestamp,
        "location": txn.location,
        "channel": txn.channel,
    }


def public_case(case: FraudCase, analyst_decision: Optional[AnalystDecision] = None) -> dict[str, Any]:
    data = case.model_dump()
    data["transaction"] = public_transaction(case.transaction)
    for score in data["agent_scores"]:
        score["metadata"] = {}
    if case.graph_evidence:
        ge = data["graph_evidence"]
        ge["connected_accounts"] = [mask_identifier(v) for v in case.graph_evidence.connected_accounts]
        ge["shared_devices"] = [mask_identifier(v) for v in case.graph_evidence.shared_devices]
        ge["shared_ips"] = [mask_ip(v) for v in case.graph_evidence.shared_ips]
    # The analyst's own recorded decision — distinct from `decision` above,
    # which is always the engine's own recommendation and never changes
    # once the case is analyzed. `is_false_positive` is the explicit fact
    # this needs to be inspectable, not inferred from decision=="clear"
    # (which is also true of a transaction that was never flagged at all).
    data["analyst_decision"] = analyst_decision.decision if analyst_decision else None
    data["is_false_positive"] = bool(analyst_decision.is_false_positive) if analyst_decision else False
    return data


def public_fraud_graph(graph: FraudGraph, flagged_node_id: Optional[str]) -> dict[str, Any]:
    """Masks a FraudGraph for the frontend's fraud-ring graph view.

    Node labels are masked exactly like public_case() already masks
    graph_evidence — mask_identifier for account/device/merchant,
    mask_ip for ip. node_id itself is NOT just masked, it's replaced
    entirely: internal node ids embed the raw identifier verbatim (e.g.
    "account:ACC-00110" from GraphBuilder), so returning them as-is would
    leak a raw identifier even with the label masked. Every node id and
    edge source/target is replaced with a one-way SHA1-derived opaque id
    instead, which the frontend can still use to match nodes to edges
    (and to flagged_node_id) but can never reverse into the original
    value.
    """
    id_map: dict[str, str] = {
        n.node_id: hashlib.sha1(n.node_id.encode()).hexdigest()[:12] for n in graph.nodes
    }

    nodes = []
    for n in graph.nodes:
        label = mask_ip(n.label) if n.node_type == "ip" else mask_identifier(n.label)
        nodes.append({
            "id": id_map[n.node_id],
            "node_type": n.node_type,
            "label": label,
            "is_suspicious": n.is_suspicious,
        })

    edges = [
        {
            "source": id_map[e.source],
            "target": id_map[e.target],
            "edge_type": e.edge_type,
            "weight": e.weight,
        }
        for e in graph.edges
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "ring_id": graph.ring_id,
        "ring_size": graph.ring_size,
        "flagged_node_id": id_map.get(flagged_node_id) if flagged_node_id else None,
    }
