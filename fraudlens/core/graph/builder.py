"""Transaction graph construction and ring detection for FraudLens.

Builds an account/device/ip/merchant graph from raw transactions and
supports BFS subgraph extraction with Louvain community-detection ring
membership over shared device/IP edges (see core/graph/community.py).
Consumed by GraphAgent and, via get_graph_evidence(), by CaseEngine and
the Fraud DNA extractor.
"""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from typing import Optional

from fraudlens.core.graph.community import detect_communities
from fraudlens.models.schemas import FraudGraph, GraphEdge, GraphEvidence, GraphNode, Transaction

NODE_ACCOUNT = "account"
NODE_DEVICE = "device"
NODE_IP = "ip"
NODE_MERCHANT = "merchant"

EDGE_USES_DEVICE = "uses_device"
EDGE_USES_IP = "uses_ip"
EDGE_TRANSACTS_WITH = "transacts_with"

_SHARED_EDGE_TYPES = (EDGE_USES_DEVICE, EDGE_USES_IP)


def _account_node_id(account_id: str) -> str:
    return f"{NODE_ACCOUNT}:{account_id}"


def _device_node_id(device_id: str) -> str:
    return f"{NODE_DEVICE}:{device_id}"


def _ip_node_id(ip_address: str) -> str:
    return f"{NODE_IP}:{ip_address}"


def _merchant_node_id(merchant_id: str) -> str:
    return f"{NODE_MERCHANT}:{merchant_id}"


class GraphBuilder:
    """Builds a FraudGraph from transactions and extracts BFS subgraphs."""

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[tuple[str, str, str], GraphEdge] = {}
        self._adjacency: dict[str, set[str]] = defaultdict(set)
        self._txn_by_id: dict[str, Transaction] = {}
        self._built = False

    def build(self, transactions: list[Transaction]) -> FraudGraph:
        """Build nodes for every account/device/ip/merchant and connecting
        edges, flagging device/IP nodes shared by multiple accounts."""
        self._nodes = {}
        self._edges = {}
        self._adjacency = defaultdict(set)
        self._txn_by_id = {t.txn_id: t for t in transactions}

        device_accounts: dict[str, set[str]] = defaultdict(set)
        ip_accounts: dict[str, set[str]] = defaultdict(set)

        for txn in transactions:
            acc_node = _account_node_id(txn.account_id)
            dev_node = _device_node_id(txn.device_id)
            ip_node = _ip_node_id(txn.ip_address)
            merch_node = _merchant_node_id(txn.merchant_id)

            self._add_node(acc_node, NODE_ACCOUNT, txn.account_id)
            self._add_node(dev_node, NODE_DEVICE, txn.device_id)
            self._add_node(ip_node, NODE_IP, txn.ip_address)
            self._add_node(merch_node, NODE_MERCHANT, txn.merchant_id)

            self._add_edge(acc_node, dev_node, EDGE_USES_DEVICE)
            self._add_edge(acc_node, ip_node, EDGE_USES_IP)
            self._add_edge(acc_node, merch_node, EDGE_TRANSACTS_WITH)

            device_accounts[dev_node].add(txn.account_id)
            ip_accounts[ip_node].add(txn.account_id)

        for dev_node, accounts in device_accounts.items():
            if len(accounts) > 1:
                self._nodes[dev_node].is_suspicious = True
        for ip_node, accounts in ip_accounts.items():
            if len(accounts) > 1:
                self._nodes[ip_node].is_suspicious = True

        self._built = True
        return FraudGraph(nodes=list(self._nodes.values()), edges=list(self._edges.values()))

    def get_subgraph(self, txn_id: str, depth: int = 2) -> FraudGraph:
        """BFS out `depth` hops from the transaction's account node, then
        detect a fraud ring via Louvain community detection over shared
        device/IP connections among the accounts reached (2+ accounts in
        the transaction's own community = a ring)."""
        sub_nodes, sub_edges, ring_id, ring_size, _ring_accounts = self._bfs_and_detect(txn_id, depth)
        return FraudGraph(nodes=sub_nodes, edges=sub_edges, ring_id=ring_id, ring_size=ring_size)

    def get_graph_evidence(self, txn_id: str, depth: int = 2) -> Optional[GraphEvidence]:
        """GraphEvidence for a transaction's subgraph, or None when no ring
        (2+ accounts in the same detected community) is found — a clean
        transaction carries no graph evidence worth reporting.

        Scoped to the *ring's own* accounts, not the wider BFS
        neighborhood: a weak bridge to a separate, unrelated cluster (see
        graph/community.py) must not blend into this ring's accounts,
        devices, or Fraud DNA fingerprint just because it's reachable
        within `depth` hops.
        """
        sub_nodes, sub_edges, ring_id, ring_size, ring_accounts = self._bfs_and_detect(txn_id, depth)
        if ring_id is None or ring_size < 2:
            return None

        node_by_id = {n.node_id: n for n in sub_nodes}

        ring_edges = [e for e in sub_edges if e.source in ring_accounts or e.target in ring_accounts]
        ring_node_ids = set(ring_accounts)
        for e in ring_edges:
            ring_node_ids.add(e.target if e.source in ring_accounts else e.source)
        ring_nodes = [n for n in sub_nodes if n.node_id in ring_node_ids]

        connected_accounts = sorted(n.label for n in ring_nodes if n.node_type == NODE_ACCOUNT)
        shared_devices = sorted(
            n.label for n in ring_nodes if n.node_type == NODE_DEVICE and n.is_suspicious
        )
        shared_ips = sorted(
            n.label for n in ring_nodes if n.node_type == NODE_IP and n.is_suspicious
        )

        merchant_accounts: dict[str, set[str]] = defaultdict(set)
        for e in ring_edges:
            if e.edge_type == EDGE_TRANSACTS_WITH and e.source in ring_accounts:
                merchant_accounts[e.target].add(e.source)
        shared_merchants = sorted(
            node_by_id[m].label
            for m, accounts in merchant_accounts.items()
            if len(accounts) > 1 and m in node_by_id
        )

        num_nodes = len(ring_nodes)
        num_edges = len(ring_edges)
        graph_density = (2 * num_edges) / (num_nodes * (num_nodes - 1)) if num_nodes > 1 else 0.0

        evidence_summary = (
            f"{ring_size}-account ring detected, sharing "
            f"{len(shared_devices)} device(s) and {len(shared_ips)} IP(s)."
        )

        return GraphEvidence(
            connected_accounts=connected_accounts,
            shared_devices=shared_devices,
            shared_ips=shared_ips,
            shared_merchants=shared_merchants,
            ring_size=ring_size,
            ring_id=ring_id,
            suspicious_cluster=True,
            graph_density=round(graph_density, 4),
            evidence_summary=evidence_summary,
        )

    def _bfs_and_detect(
        self, txn_id: str, depth: int
    ) -> tuple[list[GraphNode], list[GraphEdge], Optional[str], int, frozenset[str]]:
        if not self._built:
            raise ValueError("GraphBuilder.build() must be called before get_subgraph()")
        txn = self._txn_by_id.get(txn_id)
        if txn is None:
            raise ValueError(f"Transaction {txn_id!r} not found in built graph")

        start = _account_node_id(txn.account_id)
        visited = {start}
        frontier = {start}
        for _ in range(depth):
            next_frontier: set[str] = set()
            for node_id in frontier:
                next_frontier |= self._adjacency.get(node_id, set()) - visited
            if not next_frontier:
                break
            visited |= next_frontier
            frontier = next_frontier

        sub_nodes = [self._nodes[n] for n in visited if n in self._nodes]
        sub_edges = [
            e for e in self._edges.values() if e.source in visited and e.target in visited
        ]

        ring_id, ring_size, ring_accounts = self._detect_ring(start, visited, sub_edges)
        return sub_nodes, sub_edges, ring_id, ring_size, ring_accounts

    def _add_node(self, node_id: str, node_type: str, label: str) -> None:
        if node_id not in self._nodes:
            self._nodes[node_id] = GraphNode(node_id=node_id, node_type=node_type, label=label)

    def _add_edge(self, source: str, target: str, edge_type: str) -> None:
        key = (source, target, edge_type)
        existing = self._edges.get(key)
        if existing is not None:
            existing.weight += 1.0
        else:
            self._edges[key] = GraphEdge(source=source, target=target, edge_type=edge_type)
        self._adjacency[source].add(target)
        self._adjacency[target].add(source)

    @staticmethod
    def _detect_ring(
        start: str, visited: set[str], edges: list[GraphEdge]
    ) -> tuple[Optional[str], int, frozenset[str]]:
        account_ids = {n for n in visited if n.startswith(f"{NODE_ACCOUNT}:")}
        if start not in account_ids:
            return None, 0, frozenset()

        # Two accounts are ring-connected if they share a device or IP
        # node; the *number* of devices/IPs two accounts share becomes the
        # projected edge weight, so Louvain can tell a strong bridge
        # (several shared devices) from a weak one (a single shared IP) —
        # a plain connected-components walk can't make that distinction.
        shared_via: dict[str, list[str]] = defaultdict(list)
        for e in edges:
            if e.edge_type in _SHARED_EDGE_TYPES and e.source in account_ids:
                shared_via[e.target].append(e.source)

        projection_weights: Counter[tuple[str, str]] = Counter()
        for accounts_sharing in shared_via.values():
            unique_accounts = sorted(set(accounts_sharing))
            for i in range(len(unique_accounts)):
                for j in range(i + 1, len(unique_accounts)):
                    projection_weights[(unique_accounts[i], unique_accounts[j])] += 1

        communities = detect_communities(
            edges=[(a, b, float(w)) for (a, b), w in projection_weights.items()],
            nodes=account_ids,
        )

        community = next((c for c in communities if start in c), None)
        if community is None or len(community) < 2:
            return None, 0, frozenset()

        ring_members = sorted(a.split(":", 1)[1] for a in community)
        ring_id = "RING-" + hashlib.sha1("|".join(ring_members).encode()).hexdigest()[:8]
        return ring_id, len(community), frozenset(community)
