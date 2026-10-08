"""Rule-based entity/relationship extraction from scraped Made with Nestlé pages.

Each extractor is a function `(page, ctx) -> None` that adds nodes/edges to `ctx.graph`.
Extractors run in EXTRACTORS order, each over every page, so later extractors can rely on
nodes created by earlier ones (e.g. recipe -> product matching needs all products first).

To add a new entity type: add it to NODE_TYPES / EDGE_TYPES in schema.py, write an extractor
here, and append it to EXTRACTORS.
"""

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .schema import Edge, KnowledgeGraph, Node

HEADING = re.compile(r"^#{1,6}\s*")
SIZE_TOKENS = re.compile(
    r"\b\d+(\.\d+)?\s*(g|kg|ml|l|oz|x|ct|pack|pk|bars?|mini|minis|count)\b|\b\d+-pack\b|\b\d+x\d+\w*\b"
)
QUANTITY_PREFIX = re.compile(
    r"^[\d\s/.,½¼¾⅓⅔⅛-]*"
    r"(\([^)]*\)\s*)?"
    r"(cups?|tbsps?|tsps?|tablespoons?|teaspoons?|g|grams?|kg|ml|l|lb|lbs|oz|pkg|packages?|packets?|cans?|"
    r"bars?|boxes|box|tablets?|cubes?|pinch|dash|cloves?|large|medium|small|whole|each:?)?\b\s*"
    r"(\([^)]*\)\s*)?",
    re.I,
)
INGREDIENT_STOPWORDS = re.compile(r"\b(divided|optional|to taste|for garnish|softened|melted|chopped|diced)\b")
ALLERGEN_STATEMENT = re.compile(r"\b(may contain|contains)\s*:?\s*([^.]*)", re.I)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


@dataclass
class Page:
    url: str
    file: str
    title: str
    markdown: str
    html: str | None = None

    @property
    def path(self) -> str:
        return re.sub(r"\.html$", "", urlparse(self.url).path.strip("/"))

    @property
    def section(self) -> str:
        return self.path.split("/")[0]

    @property
    def lines(self) -> list[str]:
        return [line.strip() for line in self.markdown.splitlines()]


@dataclass
class ExtractionContext:
    config: dict[str, Any]
    graph: KnowledgeGraph = field(default_factory=KnowledgeGraph)
    page_kinds: dict[str, str] = field(default_factory=dict)

    def source(self, page: Page) -> dict[str, str]:
        return {"source_url": page.url, "source_file": page.file}


def classify(page: Page) -> str | None:
    """Return "recipe", "product", or None for pages that aren't entity pages (landing, help, promos)."""
    if page.section in ("help",) or "/" not in page.path:
        return None
    headings = [HEADING.sub("", line).lower() for line in page.lines]
    has_ingredients = "ingredients" in headings
    has_method = any(h in ("preparation", "directions", "method", "instructions") for h in headings)
    if "/recipes/" in f"/{page.path}/" and has_ingredients or has_ingredients and has_method:
        return "recipe"
    if page.path.endswith("/products") or "/recipes" in page.path:
        return None
    if "/products/" in page.path or "nutrition information" in page.markdown.lower():
        return "product"
    return None


def clean_title(title: str) -> str:
    title = title.split(" | ")[0]
    return re.sub(r"\s+(for Halloween\s+)?Recipes?\b.*$", "", title).strip()


def brand_id(section: str) -> str:
    return f"brand:{section}"


def entity_id(kind: str, page: Page) -> str:
    return f"{kind}:{page.path}"


def ingredient_name(line: str) -> str | None:
    text = line.removeprefix("- ").strip()
    text = QUANTITY_PREFIX.sub("", text, count=1)
    text = re.sub(r"\([^)]*\)", "", text).split(",")[0]
    text = INGREDIENT_STOPWORDS.sub("", normalize(text))
    text = re.sub(r"^(of|a|an|the)\s+", "", " ".join(text.split()))
    if not text or len(text) > 60 or len(text.split()) > 7:
        return None
    return text


def section_lines(page: Page, start: Callable[[str], bool], stop: Callable[[str], bool]) -> list[str]:
    result: list[str] = []
    inside = False
    for line in page.lines:
        heading = HEADING.sub("", line).lower().rstrip(":")
        if inside and (stop(heading) or line.startswith("#")):
            break
        if inside and line:
            result.append(line)
        elif start(heading):
            inside = True
    return result


def allergen_aliases(config: dict[str, Any]) -> dict[str, str]:
    """Map every normalized alias (and canonical name) to the canonical allergen name."""
    return {
        normalize(alias): canonical
        for canonical, aliases in config["allergens"].items()
        for alias in [canonical, *aliases]
    }


def extract_brands(page: Page, ctx: ExtractionContext) -> None:
    kind = ctx.page_kinds.get(page.url)
    if kind is None or page.section in ctx.config["non_brand_sections"]:
        return
    overrides = ctx.config["brand_overrides"].get(page.section, {})
    name = overrides.get("name") or page.section.replace("-", " ").title()
    aliases = sorted({normalize(name), normalize(page.section), *(normalize(a) for a in overrides.get("aliases", []))})
    ctx.graph.add_node(
        Node(
            id=brand_id(page.section),
            type="Brand",
            name=name,
            properties={"aliases": aliases, "source_url": f"{ctx.config['base_url']}/{page.section}.html"},
        )
    )


def extract_products(page: Page, ctx: ExtractionContext) -> None:
    if ctx.page_kinds.get(page.url) != "product":
        return
    node = ctx.graph.add_node(
        Node(id=entity_id("product", page), type="Product", name=clean_title(page.title), properties=ctx.source(page))
    )
    if brand_id(page.section) in ctx.graph.nodes:
        ctx.graph.add_edge(Edge(node.id, brand_id(page.section), "BELONGS_TO", ctx.source(page)))

    ingredients = section_lines(
        page, start=lambda h: h.endswith("ingredients") and h != "ingredients", stop=lambda h: False
    )
    for line in ingredients:
        for statement in ALLERGEN_STATEMENT.finditer(line):
            edge_type = "MAY_CONTAIN" if "may" in statement.group(1).lower() else "CONTAINS_ALLERGEN"
            for allergen in re.split(r",|\band\b|\bor\b", statement.group(2)):
                allergen_name = allergen_aliases(ctx.config).get(re.sub(r"^other\s+", "", normalize(allergen)))
                if allergen_name:
                    target = ctx.graph.add_node(Node(f"allergen:{allergen_name}", "Allergen", allergen_name))
                    ctx.graph.add_edge(Edge(node.id, target.id, edge_type, ctx.source(page)))
        ingredient_text = ALLERGEN_STATEMENT.split(line)[0]
        ingredient_text = re.split(r"‡?\s*rainforest alliance", ingredient_text, flags=re.I)[0]
        if "," in ingredient_text and not line.startswith("‡"):
            for part in re.split(r",(?![^(]*\))", re.sub(r"\([^)]*\)", "", ingredient_text)):
                name = normalize(part.replace("‡", ""))
                if name and len(name.split()) <= 5:
                    target = ctx.graph.add_node(Node(f"ingredient:{name}", "Ingredient", name))
                    ctx.graph.add_edge(Edge(node.id, target.id, "CONTAINS_INGREDIENT", ctx.source(page)))


def extract_recipes(page: Page, ctx: ExtractionContext) -> None:
    if ctx.page_kinds.get(page.url) != "recipe":
        return
    props: dict[str, Any] = ctx.source(page)
    for line in page.lines:
        match = re.match(r"^- (Serves|Preparation|Cooking/Cooling|Total Time|Makes|Yield):\s*(.+)$", line)
        if match:
            props[normalize(match.group(1)).replace(" ", "_")] = match.group(2)
    node = ctx.graph.add_node(Node(entity_id("recipe", page), "Recipe", clean_title(page.title), props))
    if brand_id(page.section) in ctx.graph.nodes:
        ctx.graph.add_edge(Edge(node.id, brand_id(page.section), "BELONGS_TO", ctx.source(page)))

    lines = section_lines(
        page,
        start=lambda h: h == "ingredients",
        stop=lambda h: h in ("preparation", "directions", "method", "instructions"),
    )
    for line in lines:
        if not line.startswith("- "):
            continue
        name = ingredient_name(line)
        if name:
            target = ctx.graph.add_node(Node(f"ingredient:{name}", "Ingredient", name))
            ctx.graph.add_edge(Edge(node.id, target.id, "USES_INGREDIENT", {**ctx.source(page), "text": line[2:]}))


def product_match_tokens(name: str) -> list[str]:
    return SIZE_TOKENS.sub(" ", normalize(name)).split()


def contains_phrase(haystack: list[str], needle: list[str]) -> bool:
    n = len(needle)
    return n > 0 and any(haystack[i : i + n] == needle for i in range(len(haystack) - n + 1))


def link_recipes_to_products(page: Page, ctx: ExtractionContext) -> None:
    if ctx.page_kinds.get(page.url) != "recipe":
        return
    recipe_id = entity_id("recipe", page)
    products = [n for n in ctx.graph.nodes.values() if n.type == "Product"]
    brands = [n for n in ctx.graph.nodes.values() if n.type == "Brand"]
    for edge in [e for e in ctx.graph.edges.values() if e.source == recipe_id and e.type == "USES_INGREDIENT"]:
        line_tokens = normalize(edge.properties["text"]).split()
        best: Node | None = None
        best_len = 0
        for product in products:
            tokens = product_match_tokens(product.name)
            if len(tokens) >= 2 and len(tokens) > best_len and set(tokens) <= set(line_tokens):
                best, best_len = product, len(tokens)
        if best is not None:
            ctx.graph.add_edge(
                Edge(recipe_id, best.id, "FEATURES_PRODUCT", {**ctx.source(page), "text": edge.properties["text"]})
            )
            continue
        for brand in brands:
            if any(contains_phrase(line_tokens, alias.split()) for alias in brand.properties["aliases"]):
                ctx.graph.add_edge(
                    Edge(recipe_id, brand.id, "FEATURES_BRAND", {**ctx.source(page), "text": edge.properties["text"]})
                )


def link_related_products(page: Page, ctx: ExtractionContext) -> None:
    if ctx.page_kinds.get(page.url) != "product" or not page.html:
        return
    source_id = entity_id("product", page)
    for a in BeautifulSoup(page.html, "html.parser").find_all("a", href=True):
        # Only "You might be interested in" cards; nav menus link to every product on the site.
        if "see product" not in a.get_text(" ").lower():
            continue
        href = urljoin(page.url, str(a["href"]))
        if urlparse(href).netloc != urlparse(page.url).netloc:
            continue
        target_id = f"product:{re.sub(r'.html$', '', urlparse(href).path.strip('/'))}"
        if target_id != source_id and target_id in ctx.graph.nodes:
            ctx.graph.add_edge(Edge(source_id, target_id, "RELATED_TO", ctx.source(page)))


EXTRACTORS: list[Callable[[Page, ExtractionContext], None]] = [
    extract_brands,
    extract_products,
    extract_recipes,
    link_recipes_to_products,
    link_related_products,
]


def extract_graph(pages: list[Page], config: dict[str, Any]) -> KnowledgeGraph:
    ctx = ExtractionContext(config=config)
    for page in pages:
        kind = classify(page)
        if kind:
            ctx.page_kinds[page.url] = kind
    for extractor in EXTRACTORS:
        for page in pages:
            extractor(page, ctx)
    return ctx.graph
