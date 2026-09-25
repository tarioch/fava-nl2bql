"""Regenerate the screenshots and the animated GIF shown in the README.

Runs Fava in-process on a generated example ledger, with the extension's Ollama host
pointed at a small stand-in server that replays answers recorded from the real model,
and captures the Ask page with Playwright. No Ollama server or model is needed.

Usage (from the repository root)::

    uv sync --group screenshots
    uv run playwright install chromium
    uv run --group screenshots python scripts/readme_captures.py

Set ``CHROMIUM_PATH`` to use an already installed Chromium instead of Playwright's.
"""

from __future__ import annotations

import datetime
import io
import json
import logging
import os
import random
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import quote

from beancount.scripts.example import write_example_file
from fava.application import create_app
from PIL import Image
from playwright.sync_api import Page, sync_playwright
from werkzeug.serving import make_server

OUT = Path(__file__).resolve().parent.parent / "docs" / "_static"
VIEWPORT = {"width": 1200, "height": 640}

# Recorded verbatim from `ollama run tarioch/qwen2.5-coder-bql "<question>"` (2026-09-25).
# Re-record them when the model changes, so the captures keep showing real output.
RECORDED = {
    "How much did I spend on groceries per month this year?": """```sql
SELECT year, month, sum(position) AS total
WHERE year = year(today()) AND account ~ 'Groceries'
GROUP BY year, month
ORDER BY year, month
```

Sums the postings for Expenses:Food:Groceries this year, per month.""",
    "What were my biggest expense categories last year?": """```sql
SELECT root(account, 2) AS category, sum(position)
WHERE year = year(today()) - 1 AND account ~ '^Expenses'
GROUP BY category
ORDER BY sum(number) DESC
LIMIT 5
```

Sums the postings for all Expenses accounts last year, per top-level category.""",
}
QUESTIONS = list(RECORDED)


class _RecordedOllama(BaseHTTPRequestHandler):
    """Answers Ollama's ``/api/generate`` with the recorded responses."""

    def do_POST(self) -> None:
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        prompt = request["prompt"].strip()
        body = json.dumps(
            {"model": request["model"], "response": RECORDED[prompt], "done": True}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass


def _write_ledger(path: Path, ollama_host: str) -> None:
    """Write bean-example's synthetic ledger, ending today so ``today()`` queries match."""
    today = datetime.date.today()
    random.seed(42)
    buffer = io.StringIO()
    write_example_file(
        datetime.date(1980, 5, 12),
        datetime.date(today.year - 2, 1, 1),
        today,
        True,
        file=buffer,
    )
    config = repr({"ollama_host": ollama_host})
    extension = f'{today.year - 2}-01-01 custom "fava-extension" "fava_nl2bql.extension" "{config}"'
    path.write_text(f"{buffer.getvalue()}\n{extension}\n", encoding="utf-8")


def _serve(server: HTTPServer) -> str:
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_port}"


def _screenshots(page: Page, base: str) -> None:
    for number, question in enumerate(QUESTIONS, start=1):
        page.goto(f"{base}/extension/FavaNl2Bql/?question={quote(question)}")
        page.wait_for_selector("svelte-component table, .error")
        page.wait_for_timeout(500)
        page.screenshot(path=OUT / f"ask-{number}.png")


def _animation(page: Page, base: str) -> None:
    """Type the first question and submit it, as an animated GIF."""
    frames: list[tuple[Image.Image, int]] = []

    def frame(duration_ms: int) -> None:
        image = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
        frames.append((image.quantize(colors=128), duration_ms))

    page.goto(f"{base}/income_statement/")
    page.wait_for_timeout(500)
    frame(900)
    page.get_by_role("link", name="Ask", exact=True).click()
    question_input = page.locator("#nl2bql-question")
    question_input.wait_for()
    page.wait_for_timeout(300)
    frame(600)
    question = QUESTIONS[0]
    for start in range(0, len(question), 3):
        question_input.press_sequentially(question[start : start + 3], delay=20)
        frame(90)
    frame(500)
    page.get_by_role("button", name="Ask").click()
    page.wait_for_selector("svelte-component table")
    page.wait_for_timeout(400)
    frame(4000)

    images = [image for image, _ in frames]
    images[0].save(
        OUT / "ask-demo.gif",
        save_all=True,
        append_images=images[1:],
        duration=[duration for _, duration in frames],
        loop=0,
        optimize=True,
    )


def main() -> None:
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    ollama = HTTPServer(("127.0.0.1", 0), _RecordedOllama)
    ollama_host = _serve(ollama)
    with tempfile.TemporaryDirectory() as tmp:
        ledger = Path(tmp) / "example.beancount"
        _write_ledger(ledger, ollama_host)
        app = create_app([ledger], load=True)
        fava = make_server("127.0.0.1", 0, app, threaded=True)
        base = f"{_serve(fava)}/example-beancount-file"

        OUT.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=os.environ.get("CHROMIUM_PATH")
            )
            page = browser.new_page(viewport=VIEWPORT, device_scale_factor=2)
            _screenshots(page, base)
            page.close()
            page = browser.new_page(viewport=VIEWPORT)
            _animation(page, base)
            browser.close()
        fava.shutdown()
    ollama.shutdown()


if __name__ == "__main__":
    main()
