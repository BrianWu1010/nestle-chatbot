"""Smoke eval for the Nestlé assistant: relevance and citation checks against a running app.

Usage:
    python evals/nestle_smoke.py --url https://<app>.azurewebsites.net

Each question runs twice (GraphRAG off, GraphRAG on). Writes
evals/results/nestle-smoke/results.jsonl and evals/results_summaries/nestle_smoke.md.
"""

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path

EVALS_DIR = Path(__file__).parent
REFUSAL_PATTERNS = re.compile(
    r"don['’]t know|do not know|not sure|couldn['’]t find|could not find|no information|not able to|can['’]t help|cannot help|unable to",
    re.I,
)
INLINE_CITATION = re.compile(r"\[[^\]]+\.md[^\]]*\]")


def ask(url: str, question: str, use_graphrag: bool) -> dict:
    body = json.dumps(
        {
            "messages": [{"role": "user", "content": question}],
            "context": {"overrides": {"use_graph": use_graphrag}},
        }
    ).encode()
    request = urllib.request.Request(f"{url.rstrip('/')}/chat", data=body, headers={"Content-Type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return json.load(response)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(15 * (attempt + 1))
    raise RuntimeError("unreachable")


def score(item: dict, response: dict) -> dict:
    answer = response.get("output_text") or ""
    citations = response.get("context", {}).get("data_points", {}).get("citations", [])
    # Only an opening refusal counts; answers often end with a hedge about pages they didn't see.
    refused = bool(REFUSAL_PATTERNS.search(answer[:120]))
    if item.get("out_of_scope"):
        return {"answer": answer, "citations": citations, "correct_scope": refused}
    prefixes = item["source_prefixes"]
    cited_in_answer = INLINE_CITATION.findall(answer)
    return {
        "answer": answer,
        "citations": citations,
        "correct_scope": not refused,
        "relevant_source": any(c.startswith(p) or f"__{p}" in c for c in citations for p in prefixes),
        "inline_citation": bool(cited_in_answer),
        "keywords": all(k.lower() in answer.lower() for k in item["keywords"]),
    }


def pct(rows: list[dict], key: str) -> str:
    values = [r[key] for r in rows if key in r]
    return f"{sum(values)}/{len(values)} ({100 * sum(values) / len(values):.0f}%)" if values else "-"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--questions", default=str(EVALS_DIR / "nestle_smoke_questions.json"))
    parser.add_argument("--rescore", action="store_true", help="Re-score saved results.jsonl without calling the app")
    args = parser.parse_args()

    items = json.loads(Path(args.questions).read_text())
    results: dict[str, list[dict]] = {"rag": [], "graphrag": []}
    out_dir = EVALS_DIR / "results" / "nestle-smoke"
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "results.jsonl"
    saved: dict[tuple[str, str], dict] = {}
    if args.rescore:
        for line in filter(None, results_path.read_text().split("\n")):
            row = json.loads(line)
            saved[(row["question"], row["mode"])] = {
                "output_text": row["answer"],
                "context": {"data_points": {"citations": row["citations"]}},
            }
    rows_out = []
    for item in items:
        for mode in results:
            if args.rescore:
                response = saved[(item["question"], mode)]
            else:
                response = ask(args.url, item["question"], mode == "graphrag")
                time.sleep(2)
            row = {"question": item["question"], "mode": mode, **score(item, response)}
            results[mode].append(row)
            rows_out.append(json.dumps(row, ensure_ascii=False))
            print(
                f"[{mode}] {item['question']} -> scope={row['correct_scope']} source={row.get('relevant_source', '-')}"
            )
    results_path.write_text("\n".join(rows_out) + "\n")

    in_scope = {m: [r for r, i in zip(rows, items) if not i.get("out_of_scope")] for m, rows in results.items()}
    out_scope = {m: [r for r, i in zip(rows, items) if i.get("out_of_scope")] for m, rows in results.items()}
    lines = [
        "# Nestlé assistant smoke eval",
        "",
        f"Target: `{args.url}` · {len(items)} questions ({len(in_scope['rag'])} in scope, {len(out_scope['rag'])} out of scope).",
        "Regenerate with `python evals/nestle_smoke.py --url <app url>`.",
        "",
        "| Metric | RAG | RAG + GraphRAG |",
        "| --- | --- | --- |",
        f"| Answered in-scope question | {pct(in_scope['rag'], 'correct_scope')} | {pct(in_scope['graphrag'], 'correct_scope')} |",
        f"| Cited a page from the right brand/section | {pct(in_scope['rag'], 'relevant_source')} | {pct(in_scope['graphrag'], 'relevant_source')} |",
        f"| Answer has inline `[page.md]` citation | {pct(in_scope['rag'], 'inline_citation')} | {pct(in_scope['graphrag'], 'inline_citation')} |",
        f"| Expected keywords in answer | {pct(in_scope['rag'], 'keywords')} | {pct(in_scope['graphrag'], 'keywords')} |",
        f"| Declined out-of-scope question | {pct(out_scope['rag'], 'correct_scope')} | {pct(out_scope['graphrag'], 'correct_scope')} |",
        "",
        "## Per question",
        "",
        "| Question | RAG source / cite | GraphRAG source / cite |",
        "| --- | --- | --- |",
    ]
    for item, rag, graph in zip(items, results["rag"], results["graphrag"]):

        def cell(r: dict) -> str:
            if item.get("out_of_scope"):
                return "declined" if r["correct_scope"] else "**answered**"
            return f"{'✓' if r['relevant_source'] else '✗'} / {'✓' if r['inline_citation'] else '✗'}"

        lines.append(f"| {item['question']} | {cell(rag)} | {cell(graph)} |")
    summary = EVALS_DIR / "results_summaries" / "nestle_smoke.md"
    summary.write_text("\n".join(lines) + "\n")
    print(f"Wrote {summary}")


if __name__ == "__main__":
    main()
