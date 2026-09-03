"""Masking helpers for anything that leaves the engine toward an API
response or a report — account IDs, device IDs, IPs. Scoring agents work
on raw data; nothing outward-facing should."""

from __future__ import annotations

from typing import Any

from fraudlens.models.schemas import FraudCase, Transaction


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


def public_case(case: FraudCase) -> dict[str, Any]:
    data = case.model_dump()
    data["transaction"] = public_transaction(case.transaction)
    for score in data["agent_scores"]:
        score["metadata"] = {}
    if case.graph_evidence:
        ge = data["graph_evidence"]
        ge["connected_accounts"] = [mask_identifier(v) for v in case.graph_evidence.connected_accounts]
        ge["shared_devices"] = [mask_identifier(v) for v in case.graph_evidence.shared_devices]
        ge["shared_ips"] = [mask_ip(v) for v in case.graph_evidence.shared_ips]
    return data
