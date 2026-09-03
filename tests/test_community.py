import unittest

from fraudlens.core.graph.community import detect_communities


class DetectCommunitiesTests(unittest.TestCase):
    def test_empty_graph_returns_no_communities(self) -> None:
        self.assertEqual(detect_communities([]), [])

    def test_isolated_nodes_are_singleton_communities(self) -> None:
        communities = detect_communities([], nodes=["A1", "A2"])
        self.assertEqual(len(communities), 2)
        self.assertIn({"A1"}, communities)
        self.assertIn({"A2"}, communities)

    def test_fully_connected_triangle_stays_one_community(self) -> None:
        edges = [("A1", "A2", 2.0), ("A2", "A3", 2.0), ("A1", "A3", 2.0)]
        communities = detect_communities(edges, nodes=["A1", "A2", "A3"])
        self.assertEqual(len(communities), 1)
        self.assertEqual(communities[0], {"A1", "A2", "A3"})

    def test_two_dense_clusters_with_weak_bridge_split_apart(self) -> None:
        # Two tight triangles bridged by one weak (weight=1) edge -> Louvain
        # should keep the triangles separate rather than merging them into
        # one over-counted ring the way plain connected-components would.
        edges = [
            ("A1", "A2", 5.0), ("A2", "A3", 5.0), ("A1", "A3", 5.0),
            ("B1", "B2", 5.0), ("B2", "B3", 5.0), ("B1", "B3", 5.0),
            ("A3", "B1", 1.0),
        ]
        nodes = ["A1", "A2", "A3", "B1", "B2", "B3"]
        communities = detect_communities(edges, nodes=nodes)
        self.assertEqual(len(communities), 2)
        sizes = sorted(len(c) for c in communities)
        self.assertEqual(sizes, [3, 3])

    def test_deterministic_across_repeated_calls(self) -> None:
        edges = [("A1", "A2", 1.0), ("A2", "A3", 2.0), ("A3", "A4", 1.0), ("A4", "A1", 1.0)]
        nodes = ["A1", "A2", "A3", "A4"]
        first = detect_communities(edges, nodes=nodes)
        second = detect_communities(edges, nodes=nodes)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
