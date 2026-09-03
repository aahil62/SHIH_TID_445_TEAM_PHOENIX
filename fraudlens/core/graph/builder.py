"""Transaction graph construction and ring detection for FraudLens.

Builds an account/device/ip/merchant graph from raw transactions and
supports BFS subgraph extraction with connected-component ring detection
over shared device/IP edges. Consumed by GraphAgent and, later, the
Fraud DNA matcher.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Optional

from fraudlens.models.schemas import FraudGraph, GraphEdge, GraphNode, Transaction

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
        detect a fraud ring via connected components over shared
        device/IP edges among the accounts reached (2+ connected
        accounts = a ring)."""
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

        ring_id, ring_size = self._detect_ring(start, visited, sub_edges)
        return FraudGraph(nodes=sub_nodes, edges=sub_edges, ring_id=ring_id, ring_size=ring_size)

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
    ) -> tuple[Optional[str], int]:
        account_ids = {n for n in visited if n.startswith(f"{NODE_ACCOUNT}:")}
        parent: dict[str, str] = {a: a for a in account_ids}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        # Two accounts are ring-connected if they share a device or IP node.
        shared_via: dict[str, list[str]] = defaultdict(list)
        for e in edges:
            if e.edge_type in _SHARED_EDGE_TYPES and e.source in account_ids:
                shared_via[e.target].append(e.source)

        for accounts_sharing in shared_via.values():
            for i in range(1, len(accounts_sharing)):
                union(accounts_sharing[0], accounts_sharing[i])

        if start not in parent:
            return None, 0

        root = find(start)
        component = [a for a in account_ids if find(a) == root]
        if len(component) < 2:
            return None, 0

        ring_members = sorted(a.split(":", 1)[1] for a in component)
        ring_id = "RING-" + hashlib.sha1("|".join(ring_members).encode()).hexdigest()[:8]
        return ring_id, len(component)
