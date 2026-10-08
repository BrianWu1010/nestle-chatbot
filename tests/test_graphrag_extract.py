import pytest

from graphrag.extract import Page, classify, clean_title, extract_graph, ingredient_name
from graphrag.schema import Edge, KnowledgeGraph, Node

BASE = "https://www.madewithnestle.ca"
CONFIG = {
    "base_url": BASE,
    "non_brand_sections": ["help"],
    "allergens": {"peanuts": ["peanut"], "tree nuts": ["nuts"], "milk": [], "soy": []},
    "brand_overrides": {"kit-kat": {"name": "KIT KAT", "aliases": ["kitkat"]}},
}

PRODUCT_MD = """# SMARTIES Snack Size | Nestlé CA

Source URL: https://www.madewithnestle.ca/smarties/snack-size.html

### SMARTIES Snack Size Nutrition Information

#### SMARTIES Snack Size Ingredients

Sugar, Milk ingredients, Cocoa butter‡ (cocoa), Wheat flour. Contains: Milk. May contain: Peanuts, Other tree nuts.
‡Rainforest Alliance Certified
"""

KITKAT_MD = """# KIT KAT Mini 11.8g | Nestlé CA

### KIT KAT Nutrition Information
"""

RECIPE_MD = """# SMARTIES Cookie Recipe 250g | Nestlé CA

- Serves: 24
- Total Time: 30 minutes
Ingredients
- 1 cup (250 mL) packed brown sugar
- 2 large eggs, divided
- 5 boxes (5 x 10g) SMARTIES Snack-Size
- 4 snack-size bars KitKat
Preparation
- Preheat oven to 350°F.
"""

RELATED_HTML = """<html><body>
<nav><a href="/kit-kat/mini.html">KIT KAT Mini</a></nav>
<a href="https://www.madewithnestle.ca/kit-kat/mini.html">KIT KAT Mini See Product</a>
</body></html>"""


def make_pages() -> list[Page]:
    return [
        Page(
            f"{BASE}/smarties/snack-size.html",
            "smarties__snack-size.md",
            "SMARTIES Snack Size | Nestlé CA",
            PRODUCT_MD,
            RELATED_HTML,
        ),
        Page(f"{BASE}/kit-kat/mini.html", "kit-kat__mini.md", "KIT KAT Mini 11.8g | Nestlé CA", KITKAT_MD),
        Page(
            f"{BASE}/smarties/recipes/cookie.html",
            "smarties__recipes__cookie.md",
            "SMARTIES Cookie Recipe 250g | Nestlé CA",
            RECIPE_MD,
        ),
        Page(f"{BASE}/help/faq.html", "help__faq.md", "FAQ", "Ingredients\nPreparation\n"),
        Page(f"{BASE}/smarties.html", "smarties.md", "SMARTIES", "landing"),
    ]


def edges_of(graph: KnowledgeGraph, edge_type: str) -> set[tuple[str, str]]:
    return {(e.source, e.target) for e in graph.edges.values() if e.type == edge_type}


def test_classify():
    pages = make_pages()
    assert [classify(p) for p in pages] == ["product", "product", "recipe", None, None]


def test_clean_title_and_ingredient_name():
    assert clean_title("KitKat Pumpkin Cupcakes for Halloween Recipes 977g | Nestlé CA") == "KitKat Pumpkin Cupcakes"
    assert ingredient_name("- 1 cup (250 mL) packed brown sugar") == "packed brown sugar"
    assert ingredient_name("- 2 large eggs, divided") == "eggs"
    assert ingredient_name("- " + "word " * 20) is None


def test_extract_graph_entities_and_edges():
    graph = extract_graph(make_pages(), CONFIG)
    types = {n.id: n.type for n in graph.nodes.values()}
    assert types["brand:smarties"] == "Brand"
    assert graph.nodes["brand:kit-kat"].name == "KIT KAT"
    assert "brand:help" not in types
    assert types["product:smarties/snack-size"] == "Product"
    recipe = graph.nodes["recipe:smarties/recipes/cookie"]
    assert recipe.name == "SMARTIES Cookie"
    assert recipe.properties["serves"] == "24"
    assert recipe.properties["source_file"] == "smarties__recipes__cookie.md"

    assert ("recipe:smarties/recipes/cookie", "brand:smarties") in edges_of(graph, "BELONGS_TO")
    assert ("recipe:smarties/recipes/cookie", "ingredient:packed brown sugar") in edges_of(graph, "USES_INGREDIENT")
    assert ("recipe:smarties/recipes/cookie", "product:smarties/snack-size") in edges_of(graph, "FEATURES_PRODUCT")
    assert ("recipe:smarties/recipes/cookie", "brand:kit-kat") in edges_of(graph, "FEATURES_BRAND")

    product = "product:smarties/snack-size"
    assert {t for s, t in edges_of(graph, "CONTAINS_INGREDIENT") if s == product} == {
        "ingredient:sugar",
        "ingredient:milk ingredients",
        "ingredient:cocoa butter",
        "ingredient:wheat flour",
    }
    assert edges_of(graph, "CONTAINS_ALLERGEN") == {(product, "allergen:milk")}
    assert edges_of(graph, "MAY_CONTAIN") == {(product, "allergen:peanuts"), (product, "allergen:tree nuts")}
    assert edges_of(graph, "RELATED_TO") == {(product, "product:kit-kat/mini")}


def test_knowledge_graph_roundtrip_and_validation(tmp_path):
    graph = extract_graph(make_pages(), CONFIG)
    path = tmp_path / "graph.json"
    graph.save(path)
    loaded = KnowledgeGraph.load(path)
    assert loaded.to_dict() == graph.to_dict()
    assert any(n.id == "brand:smarties" for _, n in loaded.neighbors("product:smarties/snack-size"))

    with pytest.raises(ValueError, match="node type"):
        loaded.add_node(Node("x:1", "Planet", "x"))
    with pytest.raises(ValueError, match="edge type"):
        loaded.add_edge(Edge("brand:smarties", "brand:kit-kat", "LIKES"))
    with pytest.raises(ValueError, match="not a node"):
        loaded.add_edge(Edge("brand:smarties", "brand:missing", "RELATED_TO"))

    merged = loaded.add_node(Node("brand:smarties", "Brand", "Other", {"new": 1}))
    assert merged.name == "Smarties" and merged.properties["new"] == 1
