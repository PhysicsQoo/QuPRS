#!/usr/bin/env python3
"""Exercise version selection at the intended GitHub Pages URL prefix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import os

from playwright.sync_api import sync_playwright


class SilentHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args: object) -> None:
        pass


def browser_check(root: Path, output: Path) -> None:
    root = root.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="quprs-version-preview-") as tmp:
        mount = Path(tmp) / "QuPRS"
        os.symlink(root, mount, target_is_directory=True)
        with ThreadingHTTPServer(("127.0.0.1", 0),
                                 partial(SilentHandler, directory=tmp)) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}/QuPRS/docs/"
            results = []
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    try:
                        page = browser.new_page(viewport={"width": 1366, "height": 850})
                        for version in ("dev", "v0.99.99-test"):
                            response = page.goto(base + version + "/", wait_until="networkidle")
                            if response is None or response.status != 200:
                                raise AssertionError(f"Missing version page: {version}")
                            if not page.locator("h1").first.is_visible():
                                raise AssertionError(f"Missing version heading: {version}")
                            page.screenshot(path=str(output / f"{version}-desktop.png"), full_page=True)
                            results.append(version)
                        page.goto(base + "dev/", wait_until="networkidle")
                        # Require live version entries in the page, not just versions.json.
                        page.wait_for_function("""() => {
                          const t = document.documentElement.innerText;
                          const links = [...document.querySelectorAll('a')];
                          return t.includes('dev') &&
                            links.some(a => (a.getAttribute('href') || '').includes('v0.99.99-test'));
                        }""", timeout=20000)
                        mobile = browser.new_page(viewport={"width": 390, "height": 844},
                                                  is_mobile=True, has_touch=True)
                        response = mobile.goto(base + "dev/", wait_until="networkidle")
                        if response is None or response.status != 200:
                            raise AssertionError("Missing mobile dev version")
                        mobile.screenshot(path=str(output / "dev-mobile.png"), full_page=True)
                        browser.close()
                    finally:
                        browser.close()
            finally:
                server.shutdown()
                thread.join(timeout=10)
    (output / "version-browser.json").write_text(
        json.dumps({"versions": results, "selector": "PASS"}, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Live mike version selector browser check: PASS (2 desktop, 1 mobile)")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--pages", required=True)
    p.add_argument("--output", default="docs-version-review")
    args = p.parse_args()
    browser_check(Path(args.pages), Path(args.output))


if __name__ == "__main__":
    main()
