"""Graph-based scoring agent for FraudLens.

Flags device/IP sharing across accounts and estimates fraud-ring size via
Louvain community detection over a shared-devices/IPs account projection
(see fraudlens/core/graph/community.py — the same detector GraphBuilder
uses for GraphEvidence, so the two ring-size signals stay consistent).
Carries the heaviest ensemble weight (0.35 — see
fraudlens/core/scoring/ensemble.py), so its confidence is deliberately
scaled to how large and well-evidenced the estimated ring is, rather than
being a flat default.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from fraudlens.core.graph.community import detect_communities
from fraudlens.models.schemas import AgentScore, Transaction

_DEVICE_SHARE_MAJOR = 3   # other accounts sharing the device/IP
_DEVICE_SHARE_MINOR = 1
_MANY_DEVICES_THRESHOLD = 4  # distinct devices used by one account

_RING_MAJOR = 4  # connected accounts
_RING_MINOR = 2

_QUIET_SCORE = 0.05
_BASE_CONFIDENCE = 0.4


class GraphAgent:
    """Scores transactions on device/IP sharing and estimated ring size."""

    name = "graph_agent"

    def __init__(self) -> None:
        self._device_accounts: dict[str, set[str]] = {}
        self._ip_accounts: dict[str, set[str]] = {}
        self._account_devices: dict[str, set[str]] = {}
        self._ring_size_by_account: dict[str, int] = {}

    def build_index(self, transactions: list[Transaction]) -> None:
        """Index device/IP -> accounts (and vice versa) and precompute
        each account's estimated ring size via Louvain community
        detection over a shared-devices/IPs account projection."""
        device_accounts: dict[str, set[str]] = defaultdict(set)
        ip_accounts: dict[str, set[str]] = defaultdict(set)
        account_devices: dict[str, set[str]] = defaultdict(set)
        all_accounts: set[str] = set()

        for txn in transactions:
            device_accounts[txn.device_id].add(txn.account_id)
            ip_accounts[txn.ip_address].add(txn.account_id)
            account_devices[txn.account_id].add(txn.device_id)
            all_accounts.add(txn.account_id)

        # Project accounts that share a device/IP onto an edge, weighted
        # by how many devices/IPs they share — a stronger bridge than a
        # single shared IP, which lets Louvain resolve a weakly-bridged
        # pair of clusters into two rings instead of one over-counted one.
        projection_weights: Counter[tuple[str, str]] = Counter()
        for accounts in list(device_accounts.values()) + list(ip_accounts.values()):
            unique_accounts = sorted(accounts)
            for i in range(len(unique_accounts)):
                for j in range(i + 1, len(unique_accounts)):
                    projection_weights[(unique_accounts[i], unique_accounts[j])] += 1

        communities = detect_communities(
            edges=[(a, b, float(w)) for (a, b), w in projection_weights.items()],
            nodes=all_accounts,
        )

        ring_size_by_account: dict[str, int] = {}
        for community in communities:
            size = len(community)
            for account_id in community:
                ring_size_by_account[account_id] = size

        self._device_accounts = dict(device_accounts)
        self._ip_accounts = dict(ip_accounts)
        self._account_devices = dict(account_devices)
        self._ring_size_by_account = ring_size_by_account

    def score(self, txn: Transaction) -> AgentScore:
        reasons: list[str] = []
        signal_scores: list[float] = []
        metadata: dict[str, Any] = {}

        other_device_accounts = len(
            self._device_accounts.get(txn.device_id, set()) - {txn.account_id}
        )
        metadata["other_accounts_on_device"] = other_device_accounts
        if other_device_accounts >= _DEVICE_SHARE_MAJOR:
            signal_scores.append(0.85)
            reasons.append(
                f"Device {txn.device_id} shared with {other_device_accounts} other accounts"
            )
        elif other_device_accounts >= _DEVICE_SHARE_MINOR:
            signal_scores.append(0.5)
            reasons.append(
                f"Device {txn.device_id} shared with {other_device_accounts} other account(s)"
            )

        other_ip_accounts = len(self._ip_accounts.get(txn.ip_address, set()) - {txn.account_id})
        metadata["other_accounts_on_ip"] = other_ip_accounts
        if other_ip_accounts >= _DEVICE_SHARE_MAJOR:
            signal_scores.append(0.85)
            reasons.append(
                f"IP {txn.ip_address} shared with {other_ip_accounts} other accounts"
            )
        elif other_ip_accounts >= _DEVICE_SHARE_MINOR:
            signal_scores.append(0.5)
            reasons.append(
                f"IP {txn.ip_address} shared with {other_ip_accounts} other account(s)"
            )

        device_count = len(self._account_devices.get(txn.account_id, {txn.device_id}))
        metadata["account_device_count"] = device_count
        if device_count >= _MANY_DEVICES_THRESHOLD:
            signal_scores.append(0.6)
            reasons.append(f"Account has used {device_count} distinct devices")

        ring_size = self._ring_size_by_account.get(txn.account_id, 1)
        metadata["estimated_ring_size"] = ring_size
        if ring_size >= _RING_MAJOR:
            signal_scores.append(0.95)
            reasons.append(f"Estimated fraud ring of {ring_size} connected accounts")
        elif ring_size >= _RING_MINOR:
            signal_scores.append(0.6)
            reasons.append(f"Small connected cluster of {ring_size} accounts")

        score = max(signal_scores) if signal_scores else _QUIET_SCORE
        confidence = min(0.95, _BASE_CONFIDENCE + 0.1 * ring_size)

        return AgentScore(
            agent_name=self.name,
            score=round(min(score, 1.0), 4),
            confidence=round(confidence, 4),
            reasons=reasons,
            metadata=metadata,
        )
