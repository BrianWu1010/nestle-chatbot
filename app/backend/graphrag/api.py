"""HTTP API for inspecting and extending the knowledge graph without code changes.

  GET  /graph/stats                  node/edge counts
  GET  /graph/search?q=...           seed entities + facts the chat would use for this question
  GET  /graph/nodes/<node_id>        a node and its neighbors
  POST /graph/nodes                  {"type", "name", "id"?, "properties"?}
  POST /graph/edges                  {"source", "target", "type", "properties"?}

Writes require the X-Graph-Admin-Key header to match the GRAPH_ADMIN_KEY env var and are
disabled when it is unset. Added items are persisted to the overlay file (GRAPH_OVERLAY_PATH).
"""

import hmac
import os
from dataclasses import asdict

from quart import Blueprint, current_app, jsonify, request

from .extract import normalize
from .retrieve import GraphRetriever
from .schema import EDGE_TYPES, NODE_TYPES, Edge, Node
from .store import GraphStore

CONFIG_GRAPH_STORE = "graph_store"

graph_bp = Blueprint("graph", __name__, url_prefix="/graph")


def get_store() -> GraphStore | None:
    return current_app.config.get(CONFIG_GRAPH_STORE)


def write_denied():
    admin_key = os.getenv("GRAPH_ADMIN_KEY", "")
    if not admin_key:
        return jsonify({"error": "Graph writes are disabled. Set GRAPH_ADMIN_KEY to enable them."}), 403
    if not hmac.compare_digest(request.headers.get("X-Graph-Admin-Key", ""), admin_key):
        return jsonify({"error": "Invalid or missing X-Graph-Admin-Key header"}), 401
    return None


@graph_bp.before_request
async def require_graph():
    if get_store() is None:
        return jsonify({"error": "Knowledge graph is not enabled"}), 404
    return None


@graph_bp.get("/stats")
async def stats():
    store = get_store()
    assert store is not None
    return jsonify({**store.stats(), "node_types": sorted(NODE_TYPES), "edge_types": sorted(EDGE_TYPES)})


@graph_bp.get("/search")
async def search():
    store = get_store()
    assert store is not None
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "q is required"}), 400
    return jsonify(GraphRetriever(store).expand(query).serialize())


@graph_bp.get("/nodes/<path:node_id>")
async def get_node(node_id: str):
    store = get_store()
    assert store is not None
    node = store.get_node(node_id)
    if node is None:
        return jsonify({"error": f"Node {node_id!r} not found"}), 404
    neighbors = [{"edge": asdict(edge), "node": asdict(other)} for edge, other in store.neighbors(node_id)]
    return jsonify({"node": asdict(node), "neighbors": neighbors})


@graph_bp.post("/nodes")
async def add_node():
    if denied := write_denied():
        return denied
    store = get_store()
    assert store is not None
    body = await request.get_json(silent=True) or {}
    node_type, name = body.get("type"), (body.get("name") or "").strip()
    if node_type not in NODE_TYPES or not name:
        return jsonify({"error": f"type must be one of {sorted(NODE_TYPES)} and name is required"}), 400
    # Same id convention as the extractor ("ingredient:brown sugar"), so additions merge with extracted nodes.
    node_id = body.get("id") or f"{node_type.lower()}:{normalize(name)}"
    node = store.add_node(Node(node_id, node_type, name, dict(body.get("properties") or {})))
    return jsonify(asdict(node)), 201


@graph_bp.post("/edges")
async def add_edge():
    if denied := write_denied():
        return denied
    store = get_store()
    assert store is not None
    body = await request.get_json(silent=True) or {}
    try:
        edge = store.add_edge(
            Edge(
                body.get("source", ""), body.get("target", ""), body.get("type", ""), dict(body.get("properties") or {})
            )
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(asdict(edge)), 201
