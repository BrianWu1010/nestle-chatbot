"""Graph data model shared by extraction, loading, and retrieval.

Node ids are "<type>:<key>" (e.g. "product:aero/products/hide-me-eggs-100g", "ingredient:brown sugar")
so the same entity found on many pages merges into one node.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

NODE_TYPES = {"Brand", "Product", "Recipe", "Ingredient", "Allergen"}

EDGE_TYPES = {
    "BELONGS_TO",  # Product|Recipe -> Brand
    "USES_INGREDIENT",  # Recipe -> Ingredient
    "FEATURES_PRODUCT",  # Recipe -> Product (ingredient line names the product)
    "FEATURES_BRAND",  # Recipe -> Brand (ingredient line names the brand, no specific product matched)
    "CONTAINS_INGREDIENT",  # Product -> Ingredient (from the product's ingredient list)
    "CONTAINS_ALLERGEN",  # Product -> Allergen ("Contains: ...")
    "MAY_CONTAIN",  # Product -> Allergen ("May contain: ...")
    "RELATED_TO",  # Product -> Product ("You might be interested in" links)
}


@dataclass
class Node:
    id: str
    type: str
    name: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    source: str
    target: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.source, self.target, self.type)


class KnowledgeGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: dict[tuple[str, str, str], Edge] = {}

    def add_node(self, node: Node) -> Node:
        if node.type not in NODE_TYPES:
            raise ValueError(f"Unknown node type {node.type!r}; add it to NODE_TYPES")
        existing = self.nodes.get(node.id)
        if existing is None:
            self.nodes[node.id] = node
            return node
        for k, v in node.properties.items():
            existing.properties.setdefault(k, v)
        return existing

    def add_edge(self, edge: Edge) -> Edge:
        if edge.type not in EDGE_TYPES:
            raise ValueError(f"Unknown edge type {edge.type!r}; add it to EDGE_TYPES")
        for end in (edge.source, edge.target):
            if end not in self.nodes:
                raise ValueError(f"Edge endpoint {end!r} is not a node")
        return self.edges.setdefault(edge.key, edge)

    def neighbors(self, node_id: str) -> list[tuple[Edge, Node]]:
        result = []
        for edge in self.edges.values():
            if edge.source == node_id:
                result.append((edge, self.nodes[edge.target]))
            elif edge.target == node_id:
                result.append((edge, self.nodes[edge.source]))
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [asdict(n) for n in sorted(self.nodes.values(), key=lambda n: n.id)],
            "edges": [asdict(e) for e in sorted(self.edges.values(), key=lambda e: e.key)],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeGraph":
        graph = cls()
        for n in data["nodes"]:
            graph.add_node(Node(**n))
        for e in data["edges"]:
            graph.add_edge(Edge(**e))
        return graph

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=1, ensure_ascii=False))

    @classmethod
    def load(cls, path: Path) -> "KnowledgeGraph":
        return cls.from_dict(json.loads(path.read_text()))
