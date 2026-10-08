# GraphRAG module

The assistant augments normal vector/keyword retrieval with a small knowledge graph of Made with Nestlé entities. When a question names a brand, product, recipe, ingredient or allergen, the graph finds related entities and pulls their pages from the search index, and adds short relationship facts (each with a page citation) to the answer prompt.

This is pragmatic GraphRAG: rule-based extraction, an in-memory graph, and one- or two-hop neighbor expansion. No LLM calls are spent on extraction or graph traversal.

## Pipeline

```text
data/nestle/*.md + scrape_output/nestle/raw/*.html
        │  scripts/nestle/extract_entities.py   (app/backend/graphrag/extract.py)
        ▼
app/backend/graphrag/data/nestle_graph.json      (deployed with the backend)
        │  GraphStore.load()                     (app/backend/graphrag/store.py)
        ▼
question ──► GraphRetriever.expand()             (app/backend/graphrag/retrieve.py)
               1. match seed entities in the question + rewritten search query
               2. intersect seeds (e.g. KIT KAT products that MAY_CONTAIN peanuts)
               3. expand each seed's neighbors, recipes first
        ▼
facts + source files ──► extra search restricted to those files (search.in on sourcefile)
        ▼
chat_answer prompt: retrieved chunks + "Knowledge graph facts" ──► answer with citations
```

The graph step shows up as **Knowledge graph expansion** in the answer's *Thought process* tab, listing the seeds, facts, and linked pages.

## Schema

Defined in [`app/backend/graphrag/schema.py`](../app/backend/graphrag/schema.py). Node ids are `<type>:<key>`; product and recipe keys are the page URL path, so ids are stable across re-scrapes.

| Node type | Example id | Source |
| --- | --- | --- |
| `Brand` | `brand:kit-kat` | URL section, names/aliases in `scripts/nestle/graph_config.json` |
| `Product` | `product:aero/products/hide-me-eggs-100g` | Pages with a "Nutrition Information" block or `/products/` URL |
| `Recipe` | `recipe:maggi/recipes/tacos-al-pastor` | Pages with Ingredients + Preparation sections or `/recipes/` URL |
| `Ingredient` | `ingredient:brown sugar` | Recipe ingredient lists and product ingredient statements |
| `Allergen` | `allergen:peanuts` | "Contains:" / "May contain:" statements, limited to the allergen list in config |

| Edge type | From → To | Meaning |
| --- | --- | --- |
| `BELONGS_TO` | Product/Recipe → Brand | Page lives in the brand's section |
| `USES_INGREDIENT` | Recipe → Ingredient | Line in the recipe's ingredient list (`text` property keeps the original line) |
| `FEATURES_PRODUCT` | Recipe → Product | An ingredient line names a specific product |
| `FEATURES_BRAND` | Recipe → Brand | An ingredient line names the brand but no specific product matched |
| `CONTAINS_INGREDIENT` | Product → Ingredient | Product ingredient statement |
| `CONTAINS_ALLERGEN` | Product → Allergen | "Contains: …" |
| `MAY_CONTAIN` | Product → Allergen | "May contain: …" |
| `RELATED_TO` | Product → Product | "You might be interested in" cards on the product page |

Product, recipe and brand nodes, and every extracted edge, carry `source_url` and `source_file` (the Markdown filename, which is also the `sourcefile`/`sourcepage` in Azure AI Search). Retrieval uses `source_file` to fetch chunks and cite pages.

## Rebuilding the graph

```shell
./.venv/bin/python scripts/nestle/extract_entities.py
```

This runs automatically in `./scripts/nestle/refresh.sh` (scrape → extract → ingest). Commit the regenerated `nestle_graph.json` and redeploy the backend (`azd deploy backend`).

## Adding an entity type or relationship

1. Add the type to `NODE_TYPES` or `EDGE_TYPES` in `app/backend/graphrag/schema.py`.
2. Write an extractor in `app/backend/graphrag/extract.py` with the signature `(page: Page, ctx: ExtractionContext) -> None` that calls `ctx.graph.add_node(...)` / `ctx.graph.add_edge(...)`. Use `ctx.page_kinds[page.url]` to see whether a page is a product or recipe, and `ctx.source(page)` for the provenance properties.
3. Append it to `EXTRACTORS`. Extractors run in order, each over all pages, so a linking extractor placed later can rely on nodes from earlier ones.
4. Optionally add a sentence template to `EDGE_VERBS` and a priority to `EDGE_PRIORITY` in `app/backend/graphrag/retrieve.py` so the new edge reads well as a fact and is expanded at the right point.
5. Add a case to `tests/test_graphrag_extract.py`, rebuild the graph, and check `GET /graph/stats`.

For example, a `Tag` node type (vegetarian, gluten-free, …) would be one regex-based extractor over product pages plus a `HAS_TAG` edge.

Config-only changes (no code) go in `scripts/nestle/graph_config.json`: brand display names and aliases, sections that aren't brands, and the allergen list and aliases.

## Graph API

Registered by [`app/backend/graphrag/api.py`](../app/backend/graphrag/api.py) on the backend.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/graph/stats` | Node/edge counts and allowed types |
| GET | `/graph/search?q=…` | Seeds, facts and linked pages the chat would use for a question |
| GET | `/graph/nodes/<node_id>` | A node and its neighbors |
| POST | `/graph/nodes` | Add a node: `{"type", "name", "id"?, "properties"?}` |
| POST | `/graph/edges` | Add an edge: `{"source", "target", "type", "properties"?}` |

Writes need an `X-Graph-Admin-Key` header that matches the `GRAPH_ADMIN_KEY` setting; they are refused when it isn't set. Set it with `azd env set GRAPH_ADMIN_KEY <secret>` (used locally by `app/start.sh` and pushed to App Service by `azd provision`/`azd up`).

```shell
BASE=http://localhost:50505   # or the deployed backend URL
KEY=<your GRAPH_ADMIN_KEY>

curl "$BASE/graph/search?q=Which%20KIT%20KAT%20products%20may%20contain%20peanuts"

curl -X POST "$BASE/graph/nodes" -H "X-Graph-Admin-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"type": "Ingredient", "name": "peanut butter"}'

curl -X POST "$BASE/graph/edges" -H "X-Graph-Admin-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"source": "recipe:smarties/the-original-smarties-cookies-recipe", "target": "ingredient:peanut butter", "type": "USES_INGREDIENT"}'
```

API additions are written to an overlay file (`GRAPH_OVERLAY_PATH`, default `app/backend/graphrag/data/graph_overlay.json`) and merged on startup, so re-extracting the base graph never wipes them. On App Service the app folder is replaced on each deploy; point `GRAPH_OVERLAY_PATH` at `/home/...` to keep additions across deploys.

## Settings

| Setting | Default | Effect |
| --- | --- | --- |
| `USE_GRAPHRAG` (azd env / app setting) | `true` | Load the graph and enable the graph step and API |
| `GRAPH_ADMIN_KEY` | empty | Enables graph writes when set |
| `GRAPH_OVERLAY_PATH` | `app/backend/graphrag/data/graph_overlay.json` | Where API additions are stored |
| `use_graph` (chat request override / *Developer settings* checkbox) | `true` | Turn graph expansion off per request to compare answers |

## Limitations

- Entity matching is lexical (token overlap with names and aliases), not semantic. Misspellings and paraphrases ("peanut-free bars") may not seed the graph; normal retrieval still runs.
- Recipe → product links come from ingredient-line text, because the site's "Product Featured" box is rendered client-side and isn't in the scraped HTML. About half the recipes link to a specific product; the rest link to the brand.
- Product ingredient names are lightly normalized, so near-duplicates exist (for example "mono and diglycerides" vs. "monoand diglycerides").
- The graph lives in memory (about 1,100 nodes and 8,000 edges, loaded in well under a second). `GraphStore` is the swap point for Neo4j or Cosmos DB Gremlin if it grows.
