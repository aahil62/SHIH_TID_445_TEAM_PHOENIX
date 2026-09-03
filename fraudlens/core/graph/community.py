"""Shared Louvain community detection for FraudLens's ring/cluster
detection.

Both GraphBuilder (ring membership within a subgraph, for GraphEvidence)
and GraphAgent (ring-size estimation for its confidence scaling) reduce
to the same underlying question: given accounts connected by shared
devices/IPs, which ones form a community? Rather than each rolling its
own connected-components walk, both call this one networkx-backed
implementation.

Real community detection (modularity maximization) over connected-
components is the point of this module, not just a rename: a plain
walk treats "connected" as binary, so one bridging account can pull two
otherwise-separate clusters into a single reported ring. Louvain weighs
*how* connected — two accounts sharing several devices/IPs pull harder
than two that share just one — so a weak single-shared-device bridge
between two dense clusters can resolve into two separate communities
instead of one over-counted ring.
"""

from __future__ import annotations

from typing import Iterable

import networkx as nx
from networkx.algorithms.community import louvain_communities

# Louvain's local-move phase breaks ties randomly by default — fixed so
# ring membership/size are reproducible across runs, same spirit as
# ml_agent's random_state=42.
LOUVAIN_SEED = 42


def detect_communities(
    edges: Iterable[tuple[str, str, float]], nodes: Iterable[str] = ()
) -> list[set[str]]:
    """Communities (as sets of node ids) via Louvain modularity
    maximization over a weighted undirected graph.

    `edges` are (u, v, weight) triples — weight should reflect connection
    strength (e.g. how many devices/IPs two accounts share), since that's
    what lets Louvain out-perform plain connected components on
    overlapping clusters. `nodes` ensures nodes with no edges still
    appear as their own singleton community, so callers don't need to
    special-case isolated accounts.
    """
    graph = nx.Graph()
    graph.add_nodes_from(nodes)
    graph.add_weighted_edges_from(edges)
    if graph.number_of_nodes() == 0:
        return []
    return list(louvain_communities(graph, weight="weight", seed=LOUVAIN_SEED))
