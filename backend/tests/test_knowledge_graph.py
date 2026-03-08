import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import networkx as nx
from unittest.mock import patch


class TestGraph(unittest.TestCase):

    def setUp(self):
        # Use temp file so tests don't touch real graph
        import knowledge.graph as g
        self._orig_file = g.GRAPH_FILE
        self._tmp       = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        g.GRAPH_FILE    = self._tmp.name
        g._graph        = None  # reset singleton

    def tearDown(self):
        import knowledge.graph as g
        g.GRAPH_FILE = self._orig_file
        g._graph     = None
        os.unlink(self._tmp.name)

    def test_add_entity(self):
        from knowledge.graph import add_entity, _get_graph
        add_entity("Arnav", entity_type="person")
        G = _get_graph()
        self.assertIn("arnav", G.nodes)
        self.assertEqual(G.nodes["arnav"]["entity_type"], "person")

    def test_add_relation(self):
        from knowledge.graph import add_relation, _get_graph
        add_relation("Arnav", "works_on", "ASTRA")
        G = _get_graph()
        self.assertTrue(G.has_edge("arnav", "astra"))
        self.assertEqual(G["arnav"]["astra"]["relation"], "works_on")

    def test_get_relations_outgoing(self):
        from knowledge.graph import add_relation, get_relations
        add_relation("Arnav", "likes", "Python")
        rels = get_relations("Arnav")
        self.assertTrue(any(r["relation"] == "likes" for r in rels))

    def test_get_relations_incoming(self):
        from knowledge.graph import add_relation, get_relations
        add_relation("Arnav", "works_on", "ASTRA")
        rels = get_relations("ASTRA")
        self.assertTrue(any(r["relation"] == "works_on" for r in rels))

    def test_query_graph_by_relation(self):
        from knowledge.graph import add_relation, query_graph
        add_relation("Arnav", "uses", "VSCode")
        add_relation("Arnav", "uses", "Python")
        results = query_graph(subject="Arnav", relation="uses")
        self.assertEqual(len(results), 2)

    def test_relation_weight_increases_on_repeat(self):
        from knowledge.graph import add_relation, _get_graph
        add_relation("Arnav", "likes", "Python")
        add_relation("Arnav", "likes", "Python")
        G = _get_graph()
        self.assertGreater(G["arnav"]["python"]["weight"], 1.0)

    def test_graph_context_string(self):
        from knowledge.graph import add_relation, build_graph_context
        add_relation("Arnav", "works_on", "ASTRA")
        ctx = build_graph_context("tell me about ASTRA", "Arnav")
        self.assertIsInstance(ctx, str)

    def test_get_stats(self):
        from knowledge.graph import add_relation, get_stats
        add_relation("Arnav", "works_on", "ASTRA")
        add_relation("Arnav", "likes",    "Python")
        stats = get_stats()
        self.assertEqual(stats["nodes"], 3)
        self.assertEqual(stats["edges"], 2)
        self.assertIn("works_on", stats["relations"])

    def test_persistence(self):
        from knowledge.graph import add_relation, save_graph
        import knowledge.graph as g
        add_relation("Arnav", "prefers", "FastAPI")
        save_graph()
        # Reset and reload
        g._graph = None
        from knowledge.graph import get_relations
        rels = get_relations("Arnav")
        self.assertTrue(any(r["relation"] == "prefers" for r in rels))


class TestEntityExtractor(unittest.TestCase):

    def setUp(self):
        import knowledge.graph as g
        self._orig_file = g.GRAPH_FILE
        self._tmp       = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        g.GRAPH_FILE    = self._tmp.name
        g._graph        = None

    def tearDown(self):
        import knowledge.graph as g
        g.GRAPH_FILE = self._orig_file
        g._graph     = None
        os.unlink(self._tmp.name)

    def test_extract_works_on(self):
        from knowledge.entity_extractor import extract_triples_rules
        triples = extract_triples_rules("I am working on ASTRA", "Arnav")
        self.assertTrue(any(r == "works_on" for _, r, _ in triples))

    def test_extract_likes(self):
        from knowledge.entity_extractor import extract_triples_rules
        triples = extract_triples_rules("I love Python", "Arnav")
        self.assertTrue(any(r == "likes" for _, r, _ in triples))

    def test_extract_lives_in(self):
        from knowledge.entity_extractor import extract_triples_rules
        triples = extract_triples_rules("I live in Mumbai", "Arnav")
        self.assertTrue(any(r == "lives_in" for _, r, _ in triples))

    def test_extract_uses(self):
        from knowledge.entity_extractor import extract_triples_rules
        triples = extract_triples_rules("I use VSCode for coding", "Arnav")
        self.assertTrue(any(r == "uses" for _, r, _ in triples))

    def test_extract_and_store_count(self):
        from knowledge.entity_extractor import extract_and_store
        count = extract_and_store("I am building ASTRA using Flask", "Arnav")
        self.assertGreaterEqual(count, 1)

    def test_no_false_positives(self):
        from knowledge.entity_extractor import extract_triples_rules
        triples = extract_triples_rules("what is the weather today", "Arnav")
        self.assertEqual(len(triples), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
