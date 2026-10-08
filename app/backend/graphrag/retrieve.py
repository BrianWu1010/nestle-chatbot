"""GraphRAG retrieval: match query -> seed entities -> neighbor expansion -> facts + linked pages.

The chat approach uses `GraphRetriever.expand()` to get:
  * facts: short sentences describing graph edges, each citing the page it came from
  * source_files: Markdown filenames whose chunks should be pulled from the search index
"""

import re
from dataclasses import dataclass, field

from .extract import SIZE_TOKENS, normalize
from .schema import Edge, Node
from .store import GraphStore

STOPWORDS = {
    "a", "an", "and", "are", "can", "do", "does", "for", "how", "i", "in", "is", "it", "make", "me", "my",
    "nestle", "of", "on", "or", "recipe", "recipes", "the", "to", "what", "which", "with", "made", "any", "have",
    "you", "your", "there", "some", "use", "using", "product", "products", "contain", "contains",
}  # fmt: skip

# How to phrase an edge as a fact, and whether the neighbor's page is worth fetching.
EDGE_VERBS = {
    "BELONGS_TO": "belongs to brand",
    "USES_INGREDIENT": "uses ingredient",
    "FEATURES_PRODUCT": "is a recipe featuring the product",
    "FEATURES_BRAND": "is a recipe featuring the brand",
    "CONTAINS_INGREDIENT": "contains ingredient",
    "CONTAINS_ALLERGEN": "contains allergen",
    "MAY_CONTAIN": "may contain allergen",
    "RELATED_TO": "is related to product",
}
# Lower number = expanded first. Recipes linked to products/brands are the most useful hops.
EDGE_PRIORITY = {
    "FEATURES_PRODUCT": 0,
    "FEATURES_BRAND": 1,
    "USES_INGREDIENT": 2,
    "CONTAINS_ALLERGEN": 3,
    "MAY_CONTAIN": 3,
    "BELONGS_TO": 4,
    "RELATED_TO": 5,
    "CONTAINS_INGREDIENT": 6,
}
PAGE_TYPES = {"Product", "Recipe"}
ATTRIBUTE_TYPES = {"Ingredient", "Allergen"}


def stem(token: str) -> str:
    return token[:-1] if len(token) > 3 and token.endswith("s") and not token.endswith("ss") else token


def tokens(text: str) -> list[str]:
    return [stem(t) for t in SIZE_TOKENS.sub(" ", normalize(text)).split()]


@dataclass
class SeedMatch:
    node: Node
    score: float


@dataclass
class GraphContext:
    seeds: list[SeedMatch] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)

    def serialize(self) -> dict:
        return {
            "seeds": [{"id": s.node.id, "name": s.node.name, "score": round(s.score, 2)} for s in self.seeds],
            "facts": self.facts,
            "source_files": self.source_files,
        }


class GraphRetriever:
    def __init__(self, store: GraphStore, max_seeds: int = 5, max_facts: int = 25, max_files: int = 6) -> None:
        self.store = store
        self.max_seeds = max_seeds
        self.max_facts = max_facts
        self.max_files = max_files

    def brand_tokens(self) -> set[str]:
        return {
            stem(t)
            for node in self.store.graph.nodes.values()
            if node.type == "Brand"
            for alias in node.properties.get("aliases", [])
            for t in alias.split()
        }

    def match_seeds(self, query: str) -> list[SeedMatch]:
        query_tokens = [t for t in tokens(query) if t not in STOPWORDS]
        query_set = set(query_tokens)
        query_phrase = f" {' '.join(query_tokens)} "
        brand_tokens = self.brand_tokens()
        matches: list[SeedMatch] = []
        for node in self.store.graph.nodes.values():
            if node.type in PAGE_TYPES:
                core = [t for t in tokens(node.name) if t not in STOPWORDS]
                matched = set(core) & query_set
                # Require a word beyond the brand name, so "KIT KAT" alone seeds the brand, not every KIT KAT bar.
                if len(matched) >= 2 and len(matched) / len(core) >= 0.6 and matched - brand_tokens:
                    matches.append(SeedMatch(node, 2 + len(matched) / len(core)))
            else:
                phrases = node.properties.get("aliases", []) if node.type == "Brand" else [node.name]
                for phrase in phrases:
                    phrase_tokens = [stem(t) for t in phrase.split()]
                    if len("".join(phrase_tokens)) >= 3 and f" {' '.join(phrase_tokens)} " in query_phrase:
                        # Brands are stronger seeds than generic ingredients like "milk".
                        matches.append(
                            SeedMatch(node, (1.5 if node.type == "Brand" else 1.0) + 0.1 * len(phrase_tokens))
                        )
                        break
        matches.sort(key=lambda m: (-m.score, m.node.id))
        pages = [m for m in matches if m.node.type in PAGE_TYPES][:2]
        brands = [m for m in matches if m.node.type == "Brand"][:1]
        # Drop ingredient/allergen seeds whose name is just part of a matched product/brand name.
        attributes = [
            m
            for m in matches
            if m.node.type not in PAGE_TYPES | {"Brand"}
            and not any(m.node.name in normalize(s.node.name) for s in pages + brands)
        ]
        allergen_names = {m.node.name for m in attributes if m.node.type == "Allergen"}
        attributes = [m for m in attributes if m.node.type == "Allergen" or m.node.name not in allergen_names][:2]
        return (pages + brands + attributes)[: self.max_seeds]

    def describe(self, edge: Edge) -> str:
        source = self.store.graph.nodes[edge.source]
        target = self.store.graph.nodes[edge.target]
        verb = EDGE_VERBS.get(edge.type, edge.type.lower().replace("_", " "))
        cite = f" [{edge.properties['source_file']}]" if edge.properties.get("source_file") else ""
        return f"{source.name} {verb} {target.name}{cite}"

    def intersect(self, seeds: list[SeedMatch]) -> tuple[list[str], list[str]]:
        """Pages linked to two different seeds, e.g. KIT KAT products that MAY_CONTAIN peanuts."""
        facts: list[str] = []
        files: list[str] = []
        for i, a in enumerate(seeds):
            for b in seeds[i + 1 :]:
                if (a.node.type in ATTRIBUTE_TYPES) == (b.node.type in ATTRIBUTE_TYPES):
                    continue
                b_neighbors = {n.id for _, n in self.store.neighbors(b.node.id)}
                for edge_a, middle in self.store.neighbors(a.node.id):
                    if middle.type not in PAGE_TYPES or middle.id not in b_neighbors:
                        continue
                    edges_b = [e for e, n in self.store.neighbors(middle.id) if n.id == b.node.id]
                    facts += [self.describe(edge_a)] + [self.describe(e) for e in edges_b]
                    if middle.properties.get("source_file"):
                        files.append(middle.properties["source_file"])
        return facts, files

    def expand(self, query: str) -> GraphContext:
        context = GraphContext(seeds=self.match_seeds(query))
        files = [s.node.properties["source_file"] for s in context.seeds if s.node.properties.get("source_file")]
        facts, linked_files = self.intersect(context.seeds)
        facts, files = facts[: self.max_facts // 2], files + linked_files[: self.max_files // 2]
        per_seed_budget = max(1, self.max_facts // max(1, len(context.seeds)))
        for seed in context.seeds:
            neighbors = sorted(
                self.store.neighbors(seed.node.id),
                key=lambda pair: (EDGE_PRIORITY.get(pair[0].type, 9), pair[1].type != "Recipe", pair[1].id),
            )
            for edge, neighbor in neighbors[:per_seed_budget]:
                facts.append(self.describe(edge))
                if neighbor.type in PAGE_TYPES and neighbor.properties.get("source_file"):
                    files.append(neighbor.properties["source_file"])
        context.facts = list(dict.fromkeys(facts))[: self.max_facts]
        context.source_files = list(dict.fromkeys(files))[: self.max_files]
        return context


def sourcefile_filter(files: list[str]) -> str:
    """OData filter restricting search to the given files (search.in with '|' delimiter)."""
    safe = [re.sub(r"[|']", "", f) for f in files]
    return f"search.in(sourcefile, '{'|'.join(safe)}', '|')"
