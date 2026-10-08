"""Record an animated GIF of the live chat demo for the README.

Usage: python scripts/record_demo.py [--url URL] [--question TEXT] [--out PATH]
"""

import argparse
import io
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

DEFAULT_URL = "https://app-backend-u6t5hmjsg6see.azurewebsites.net/#/chat"
DEFAULT_QUESTION = "Which KIT KAT products may contain peanuts?"


def grab(page, frames: list[Image.Image], durations: list[int], ms: int) -> None:
    frames.append(Image.open(io.BytesIO(page.screenshot())).convert("RGB"))
    durations.append(ms)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--out", default="docs/images/demo.gif")
    parser.add_argument("--width", type=int, default=960)
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    frames: list[Image.Image] = []
    durations: list[int] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(args.url, timeout=120_000)
        textbox = page.get_by_placeholder("Ask about a Nestlé product, recipe or allergen")
        textbox.wait_for(timeout=120_000)
        page.wait_for_timeout(1000)
        grab(page, frames, durations, 1500)

        for i in range(1, len(args.question) + 1, 3):
            textbox.fill(args.question[:i])
            grab(page, frames, durations, 80)
        textbox.fill(args.question)
        grab(page, frames, durations, 600)
        textbox.press("Enter")

        # Poll while the answer streams in; stop once the output has been stable for a few seconds.
        deadline = time.time() + 120
        last_text, stable_since = "", time.time()
        while time.time() < deadline:
            page.wait_for_timeout(700)
            grab(page, frames, durations, 300)
            text = page.inner_text("body")
            if text != last_text:
                last_text, stable_since = text, time.time()
            elif time.time() - stable_since > 4 and len(frames) > 15:
                break
        page.screenshot(path=str(out.with_name("demo-answer.png")))
        durations[-1] = 4000
        browser.close()

    height = round(frames[0].height * args.width / frames[0].width)
    resized = [f.resize((args.width, height), Image.LANCZOS).quantize(colors=128) for f in frames]
    resized[0].save(out, save_all=True, append_images=resized[1:], duration=durations, loop=0, optimize=True)
    print(f"Wrote {out} ({len(frames)} frames, {out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
