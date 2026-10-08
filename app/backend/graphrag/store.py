"""In-memory graph store backed by JSON files.

The base graph is the extracted `nestle_graph.json` (rebuilt by scripts/nestle/extract_entities.py).
Nodes and edges added through the API go to a separate overlay file so re-extraction never
wipes manual additions. Swap this class for a Neo4j/Cosmos implementation with the same
methods if the graph outgrows memory.
"""

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

from .schema import Edge, KnowledgeGraph, Node

logger = logging.getLogger("scripts")

DEFAULT_GRAPH_PATH = Path(__file__).parent / "data" / "nestle_graph.json"


class GraphStore:
    def __init__(self, graph: KnowledgeGraph, overlay_path: Path | None = None) -> None:
        self.graph = graph
        self.overlay_path = overlay_path
        self.overlay = KnowledgeGraph()
        self.adjacency: dict[str, list[Edge]] = defaultdict(list)
        for edge in graph.edges.values():
            self.index_edge(edge)

    @classmethod
    def load(cls, graph_path: Path = DEFAULT_GRAPH_PATH, overlay_path: Path | None = None) -> "GraphStore":
        store = cls(KnowledgeGraph.load(graph_path), overlay_path)
        if overlay_path and overlay_path.exists():
            data = json.loads(overlay_path.read_text())
            for node in data.get("nodes", []):
                store.add_node(Node(**node), persist=False)
            for edge in data.get("edges", []):
                store.add_edge(Edge(**edge), persist=False)
        logger.info("Loaded graph with %d nodes and %d edges", len(store.graph.nodes), len(store.graph.edges))
        return store

    def index_edge(self, edge: Edge) -> None:
        self.adjacency[edge.source].append(edge)
        self.adjacency[edge.target].append(edge)

    def get_node(self, node_id: str) -> Node | None:
        return self.graph.nodes.get(node_id)

    def neighbors(self, node_id: str) -> list[tuple[Edge, Node]]:
        return [
            (edge, self.graph.nodes[edge.target if edge.source == node_id else edge.source])
            for edge in self.adjacency.get(node_id, [])
        ]

    def add_node(self, node: Node, persist: bool = True) -> Node:
        added = self.graph.add_node(node)
        self.overlay.nodes[added.id] = added
        if persist:
            self.save_overlay()
        return added

    def add_edge(self, edge: Edge, persist: bool = True) -> Edge:
        is_new = edge.key not in self.graph.edges
        added = self.graph.add_edge(edge)
        if is_new:
            self.index_edge(added)
        for end in (added.source, added.target):
            self.overlay.nodes.setdefault(end, self.graph.nodes[end])
        self.overlay.edges[added.key] = added
        if persist:
            self.save_overlay()
        return added

    def save_overlay(self) -> None:
        if self.overlay_path is None:
            return
        self.overlay_path.parent.mkdir(parents=True, exist_ok=True)
        self.overlay_path.write_text(json.dumps(self.overlay.to_dict(), indent=1, ensure_ascii=False))

    def stats(self) -> dict[str, Any]:
        node_counts: dict[str, int] = defaultdict(int)
        edge_counts: dict[str, int] = defaultdict(int)
        for node in self.graph.nodes.values():
            node_counts[node.type] += 1
        for edge in self.graph.edges.values():
            edge_counts[edge.type] += 1
        return {"nodes": dict(node_counts), "edges": dict(edge_counts), "overlay_edges": len(self.overlay.edges)}
