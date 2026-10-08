"""Build the Nestlé knowledge graph (brands, products, recipes, ingredients, allergens) from scraped pages.

Reads the scrape manifest, the clean Markdown in data/nestle/, and (when present) the raw HTML cache
for cross-links, then writes a JSON graph that the graph loader / GraphRAG retrieval consume.
No network or LLM calls; safe to re-run after every scrape.

Usage:
  python scripts/nestle/extract_entities.py
  python scripts/nestle/extract_entities.py --output /tmp/graph.json
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app" / "backend"))

from graphrag.extract import Page, extract_graph  # noqa: E402

DEFAULT_CONFIG = Path(__file__).with_name("graph_config.json")


def load_pages(manifest_path: Path, raw_dir: Path) -> list[Page]:
    pages = []
    for entry in json.loads(manifest_path.read_text())["pages"]:
        if not entry.get("file"):
            continue
        md_path = ROOT / entry["file"]
        if not md_path.exists():
            continue
        raw_path = raw_dir / f"{md_path.stem}.html"
        pages.append(
            Page(
                url=entry["url"],
                file=md_path.name,
                title=entry.get("title") or "",
                markdown=md_path.read_text(),
                html=raw_path.read_text() if raw_path.exists() else None,
            )
        )
    return pages


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, help="Override output_path from config")
    args = parser.parse_args()

    config = json.loads(args.config.read_text())
    manifest_path = ROOT / config["manifest_path"]
    scrape_config = json.loads(manifest_path.read_text())["config"]
    pages = load_pages(manifest_path, ROOT / scrape_config["raw_dir"])

    graph = extract_graph(pages, config)
    output = args.output or ROOT / config["output_path"]
    graph.save(output)

    print(f"Read {len(pages)} pages ({sum(p.html is not None for p in pages)} with raw HTML)")
    print("Nodes:", dict(Counter(n.type for n in graph.nodes.values())))
    print("Edges:", dict(Counter(e.type for e in graph.edges.values())))
    print(f"Wrote {output.relative_to(ROOT) if output.is_relative_to(ROOT) else output}")


if __name__ == "__main__":
    main()
