"""Crawl madewithnestle.ca and write clean Markdown pages for prepdocs ingestion.

Stages:
  1. Discover URLs from the sitemap (+ extra_urls), filtered by allow/deny patterns.
  2. Fetch each page with a real Chrome window (the site's bot wall blocks headless clients),
     saving raw HTML to raw_dir.
  3. Extract the main text and write one Markdown file per page to clean_dir, with the
     source URL at the top so answers can cite the original page.

Usage:
  python scripts/nestle/scrape.py                       # full crawl using scrape_config.json
  python scripts/nestle/scrape.py --max-pages 20        # quick sample
  python scripts/nestle/scrape.py --from-cache          # re-extract from saved raw HTML, no network
"""

import argparse
import asyncio
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = Path(__file__).with_name("scrape_config.json")

REMOVE_TAGS = ["script", "style", "noscript", "header", "footer", "nav", "svg", "form", "iframe", "button"]
REMOVE_ATTR_PATTERN = re.compile(r"onetrust|cookie|consent|breadcrumb|skip-link|social-share", re.I)
BLOCK_TAGS = {"h1", "h2", "h3", "h4", "p", "li", "tr", "dt", "dd"}


def load_config(path: Path) -> dict:
    return json.loads(path.read_text())


def slug_for(url: str) -> str:
    path = urlparse(url).path.strip("/")
    path = re.sub(r"\.html$", "", path) or "home"
    return re.sub(r"[^a-zA-Z0-9-]+", "__", path)


def page_type_for(url: str) -> str:
    path = urlparse(url).path
    if "/recipes/" in path or path.endswith("/recipes.html"):
        return "recipe"
    if path.startswith("/help"):
        return "help"
    return "product"


def filter_urls(urls: list[str], config: dict) -> list[str]:
    allow = [re.compile(p) for p in config["allow_patterns"]]
    deny = [re.compile(p) for p in config["deny_patterns"]]
    seen: set[str] = set()
    result = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        if any(p.search(url) for p in allow) and not any(p.search(url) for p in deny):
            result.append(url)
    return result[: config["max_pages"]]


def extract_markdown(html: str, url: str) -> tuple[str, str] | None:
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string or "").strip() if soup.title else ""
    description_tag = soup.find("meta", attrs={"name": "description"})
    description = description_tag.get("content", "").strip() if description_tag else ""

    body = soup.find("main") or soup.body
    if body is None:
        return None
    for tag in body(REMOVE_TAGS):
        tag.decompose()
    for tag in body.find_all(True):
        if tag.decomposed:
            continue
        marker = " ".join([tag.get("id") or ""] + (tag.get("class") or []))
        if REMOVE_ATTR_PATTERN.search(marker):
            tag.decompose()

    lines: list[str] = []
    for tag in body.find_all(BLOCK_TAGS):
        if tag.find(BLOCK_TAGS):
            continue
        text = " ".join(tag.get_text(" ").split())
        if not text or text == "Go to main section":
            continue
        if tag.name in {"h1", "h2", "h3", "h4"}:
            lines.append(f"\n{'#' * (int(tag.name[1]) + 1)} {text}\n")
        elif tag.name == "li":
            lines.append(f"- {text}")
        elif tag.name == "tr":
            lines.append(" | ".join(" ".join(c.get_text(" ").split()) for c in tag.find_all(["th", "td"])))
        else:
            lines.append(text)

    deduped: list[str] = []
    for line in lines:
        if not deduped or deduped[-1] != line:
            deduped.append(line)
    content = "\n".join(deduped)
    content = re.sub(r"\n{3,}", "\n\n", content).strip()

    if "404" in title or content.startswith("404"):
        return None

    header = [
        f"# {title or slug_for(url)}",
        "",
        f"Source URL: {url}",
        f"Page type: {page_type_for(url)}",
        f"Brand section: {urlparse(url).path.strip('/').split('/')[0].removesuffix('.html')}",
    ]
    if description:
        header += ["", f"Summary: {description}"]
    return title, "\n".join(header) + "\n\n" + content + f"\n\nSource URL: {url}\n"


async def discover_urls(page, config: dict) -> list[str]:
    todo = [config["sitemap_url"]]
    urls: list[str] = []
    while todo:
        sitemap = todo.pop()
        response = await page.request.get(sitemap)
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", await response.text())
        print(f"sitemap {sitemap}: HTTP {response.status}, {len(locs)} entries")
        for loc in locs:
            (todo if loc.endswith(".xml") else urls).append(loc)
    return urls + config.get("extra_urls", [])


async def fetch_pages(config: dict, headless: bool) -> list[dict]:
    from playwright.async_api import async_playwright

    raw_dir = ROOT / config["raw_dir"]
    raw_dir.mkdir(parents=True, exist_ok=True)
    fetched = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=headless)
        page = await (await browser.new_context(locale="en-CA")).new_page()
        await page.goto(config["base_url"], wait_until="domcontentloaded", timeout=config["page_timeout_ms"])
        urls = filter_urls(await discover_urls(page, config), config)
        print(f"{len(urls)} URLs after allow/deny filtering")
        for i, url in enumerate(urls, 1):
            status = None
            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=config["page_timeout_ms"])
                await page.wait_for_timeout(500)
                status = response.status if response else None
                if status == 200:
                    (raw_dir / f"{slug_for(url)}.html").write_text(await page.content())
            except Exception as e:  # keep crawling past individual page failures
                print(f"  error {url}: {e}")
            print(f"[{i}/{len(urls)}] {status} {url}")
            fetched.append({"url": url, "status": status, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
            await asyncio.sleep(config["delay_seconds"])
        await browser.close()
    return fetched


def write_clean(config: dict, pages: list[dict]) -> list[dict]:
    raw_dir = ROOT / config["raw_dir"]
    clean_dir = ROOT / config["clean_dir"]
    clean_dir.mkdir(parents=True, exist_ok=True)
    for entry in pages:
        raw_path = raw_dir / f"{slug_for(entry['url'])}.html"
        entry["file"] = None
        if not raw_path.exists():
            continue
        result = extract_markdown(raw_path.read_text(), entry["url"])
        if result is None:
            continue
        title, markdown = result
        if len(markdown) < config["min_text_chars"]:
            continue
        out = clean_dir / f"{slug_for(entry['url'])}.md"
        out.write_text(markdown)
        entry.update(file=str(out.relative_to(ROOT)), title=title, page_type=page_type_for(entry["url"]))
    return pages


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--max-pages", type=int, help="Override max_pages from config")
    parser.add_argument("--from-cache", action="store_true", help="Re-extract from raw HTML without fetching")
    parser.add_argument("--headless", action="store_true", help="Run Chrome headless (usually blocked by the site)")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.max_pages:
        config["max_pages"] = args.max_pages
    manifest_path = ROOT / config["manifest_path"]

    if args.from_cache:
        pages = json.loads(manifest_path.read_text())["pages"]
    else:
        pages = asyncio.run(fetch_pages(config, headless=args.headless))

    pages = write_clean(config, pages)
    written = [p for p in pages if p.get("file")]
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"config": config, "pages": pages}, indent=2))
    print(f"Wrote {len(written)} Markdown pages to {config['clean_dir']} (manifest: {config['manifest_path']})")


if __name__ == "__main__":
    main()
