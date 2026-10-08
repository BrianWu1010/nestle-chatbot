import json

import pytest

from graphrag.api import CONFIG_GRAPH_STORE
from graphrag.retrieve import GraphRetriever, sourcefile_filter
from graphrag.schema import Edge, KnowledgeGraph, Node
from graphrag.store import GraphStore


def make_store(overlay_path=None) -> GraphStore:
    graph = KnowledgeGraph()
    graph.add_node(Node("brand:kit-kat", "Brand", "KIT KAT", {"aliases": ["kit kat", "kitkat"]}))
    graph.add_node(Node("allergen:peanuts", "Allergen", "peanuts"))
    graph.add_node(Node("ingredient:peanuts", "Ingredient", "peanuts"))
    graph.add_node(Node("product:kit-kat/mega", "Product", "KIT KAT Mega Bar 75g", {"source_file": "kit-kat__mega.md"}))
    graph.add_node(Node("product:kit-kat/mini", "Product", "KIT KAT Mini 11.8g", {"source_file": "kit-kat__mini.md"}))
    graph.add_node(
        Node("recipe:kit-kat/recipes/pizza", "Recipe", "KitKat Pizza", {"source_file": "kit-kat__recipes__pizza.md"})
    )
    for product in ("product:kit-kat/mega", "product:kit-kat/mini"):
        graph.add_edge(
            Edge(product, "brand:kit-kat", "BELONGS_TO", {"source_file": f"{product[8:].replace('/', '__')}.md"})
        )
    graph.add_edge(Edge("product:kit-kat/mega", "allergen:peanuts", "MAY_CONTAIN", {"source_file": "kit-kat__mega.md"}))
    graph.add_edge(
        Edge(
            "recipe:kit-kat/recipes/pizza",
            "product:kit-kat/mini",
            "FEATURES_PRODUCT",
            {"source_file": "kit-kat__recipes__pizza.md"},
        )
    )
    return GraphStore(graph, overlay_path)


def test_retriever_matches_seeds_and_intersects():
    context = GraphRetriever(make_store()).expand("Does KitKat contain peanuts?")
    assert [s.node.id for s in context.seeds] == ["brand:kit-kat", "allergen:peanuts"]
    assert context.facts[:2] == [
        "KIT KAT Mega Bar 75g belongs to brand KIT KAT [kit-kat__mega.md]",
        "KIT KAT Mega Bar 75g may contain allergen peanuts [kit-kat__mega.md]",
    ]
    assert context.source_files[0] == "kit-kat__mega.md"
    assert GraphRetriever(make_store()).expand("What is the capital of France?").seeds == []


def test_retriever_product_seed_expands_to_recipes():
    context = GraphRetriever(make_store()).expand("recipes with kit kat mini")
    assert context.seeds[0].node.id == "product:kit-kat/mini"
    assert "kit-kat__recipes__pizza.md" in context.source_files
    assert (
        "KitKat Pizza is a recipe featuring the product KIT KAT Mini 11.8g [kit-kat__recipes__pizza.md]"
        in context.facts
    )
    assert context.serialize()["seeds"][0]["id"] == "product:kit-kat/mini"


def test_sourcefile_filter_escapes():
    assert sourcefile_filter(["a.md", "b'|c.md"]) == "search.in(sourcefile, 'a.md|bc.md', '|')"


def test_store_overlay_roundtrip(tmp_path):
    graph_path = tmp_path / "graph.json"
    overlay_path = tmp_path / "overlay.json"
    make_store().graph.save(graph_path)
    store = GraphStore.load(graph_path, overlay_path)
    store.add_node(Node("ingredient:peanut butter", "Ingredient", "peanut butter"))
    store.add_edge(Edge("recipe:kit-kat/recipes/pizza", "ingredient:peanut butter", "USES_INGREDIENT"))
    assert json.loads(overlay_path.read_text())["edges"][0]["target"] == "ingredient:peanut butter"

    reloaded = GraphStore.load(graph_path, overlay_path)
    assert any(n.id == "ingredient:peanut butter" for _, n in reloaded.neighbors("recipe:kit-kat/recipes/pizza"))
    assert reloaded.stats()["overlay_edges"] == 1
    assert reloaded.stats()["nodes"]["Ingredient"] == 2


@pytest.fixture
def graph_client(client, tmp_path):
    client.app.config[CONFIG_GRAPH_STORE] = make_store(tmp_path / "overlay.json")
    return client


@pytest.mark.asyncio
async def test_graph_read_endpoints(graph_client):
    response = await graph_client.get("/graph/stats")
    assert (await response.get_json())["nodes"]["Product"] == 2

    response = await graph_client.get("/graph/search?q=Does KitKat contain peanuts?")
    assert (await response.get_json())["seeds"][0]["id"] == "brand:kit-kat"
    assert (await graph_client.get("/graph/search")).status_code == 400

    response = await graph_client.get("/graph/nodes/brand:kit-kat")
    result = await response.get_json()
    assert result["node"]["name"] == "KIT KAT"
    assert len(result["neighbors"]) == 2
    assert (await graph_client.get("/graph/nodes/brand:nope")).status_code == 404


@pytest.mark.asyncio
async def test_graph_write_endpoints(graph_client, monkeypatch):
    node = {"type": "Ingredient", "name": "Peanut Butter"}
    monkeypatch.delenv("GRAPH_ADMIN_KEY", raising=False)
    assert (await graph_client.post("/graph/nodes", json=node)).status_code == 403

    monkeypatch.setenv("GRAPH_ADMIN_KEY", "secret")
    assert (
        await graph_client.post("/graph/nodes", json=node, headers={"X-Graph-Admin-Key": "wrong"})
    ).status_code == 401

    headers = {"X-Graph-Admin-Key": "secret"}
    response = await graph_client.post("/graph/nodes", json=node, headers=headers)
    assert response.status_code == 201
    assert (await response.get_json())["id"] == "ingredient:peanut butter"
    assert (
        await graph_client.post("/graph/nodes", json={"type": "Planet", "name": "x"}, headers=headers)
    ).status_code == 400

    edge = {"source": "recipe:kit-kat/recipes/pizza", "target": "ingredient:peanut butter", "type": "USES_INGREDIENT"}
    assert (await graph_client.post("/graph/edges", json=edge, headers=headers)).status_code == 201
    bad_edge = {**edge, "target": "ingredient:missing"}
    response = await graph_client.post("/graph/edges", json=bad_edge, headers=headers)
    assert response.status_code == 400
    assert "not a node" in (await response.get_json())["error"]


@pytest.mark.asyncio
async def test_graph_disabled_returns_404(client):
    client.app.config.pop(CONFIG_GRAPH_STORE, None)
    assert (await client.get("/graph/stats")).status_code == 404


@pytest.mark.asyncio
async def test_chat_uses_graph_expansion(graph_client):
    graph_client.app.config["chat_approach"].graph_retriever = GraphRetriever(
        graph_client.app.config[CONFIG_GRAPH_STORE]
    )
    response = await graph_client.post(
        "/chat",
        json={"messages": [{"content": "Does KitKat contain peanuts?", "role": "user"}]},
    )
    assert response.status_code == 200
    result = await response.get_json()
    graph_step = next(t for t in result["context"]["thoughts"] if t["title"] == "Knowledge graph expansion")
    assert graph_step["description"]["source_files"][0] == "kit-kat__mega.md"
    assert "kit-kat__mega.md" in result["context"]["data_points"]["citations"]

    response = await graph_client.post(
        "/chat",
        json={
            "messages": [{"content": "Does KitKat contain peanuts?", "role": "user"}],
            "context": {"overrides": {"use_graph": False}},
        },
    )
    result = await response.get_json()
    assert all(t["title"] != "Knowledge graph expansion" for t in result["context"]["thoughts"])
