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
                        # Rustdoc remains native, but its small version menu
                        # consumes the same mike versions.json manifest.
                        response = page.goto(
                            base + "dev/rust-api/quprs/", wait_until="networkidle"
                        )
                        if response is None or response.status != 200:
                            raise AssertionError("Missing native Rustdoc page")
                        selector = page.locator("[data-quprs-version-selector] select")
                        selector.wait_for(state="visible", timeout=20000)
                        page.wait_for_function(
                            "() => {const s=document.querySelector('[data-quprs-version-selector] select');"
                            "return s && !s.disabled && [...s.options].some(o=>o.value==='stable')"
                            " && [...s.options].some(o=>o.value==='v0.99.99-test');}",
                            timeout=20000,
                        )
                        if selector.input_value() != "dev":
                            raise AssertionError("Rustdoc selector did not select dev")
                        # Rustdoc owns the page's desktop flex layout. The
                        # selector must be inside main, never a sibling of the
                        # native sidebar that would form a wide empty column.
                        for width in (1366, 1024, 390):
                            page.set_viewport_size({"width": width, "height": 850})
                            layout = page.evaluate("""() => {
                                const nav = document.querySelector(
                                    "nav[data-quprs-version-selector]");
                                const main = document.querySelector("main");
                                const sidebar = document.querySelector(".sidebar");
                                const nr = nav?.getBoundingClientRect();
                                const mr = main?.getBoundingClientRect();
                                const sr = sidebar?.getBoundingClientRect();
                                return {
                                    nested: !!nav && main?.contains(nav),
                                    inBounds: !!nr && !!mr &&
                                      nr.left >= mr.left - 2 && nr.right <= mr.right + 2,
                                    sidebarLeft: sr?.left ?? -1,
                                    navVisible: !!nr && nr.width > 0 && nr.height > 0
                                };
                            }""")
                            if not layout["nested"] or not layout["inBounds"] or not layout["navVisible"]:
                                raise AssertionError(
                                    f"Rustdoc version selector escapes main at {width}px: {layout}"
                                )
                            if width >= 1024 and not (-2 <= layout["sidebarLeft"] <= 2):
                                raise AssertionError(
                                    f"Rustdoc sidebar shifted at {width}px: {layout}"
                                )
                        page.set_viewport_size({"width": 1366, "height": 850})
                        page.screenshot(
                            path=str(output / "rustdoc-dev-selector.png"), full_page=True
                        )
                        selector.select_option("v0.99.99-test")
                        page.wait_for_url(
                            base + "v0.99.99-test/rust-api/quprs/", timeout=20000
                        )
                        if not page.locator("nav[data-quprs-version-selector]").is_visible():
                            raise AssertionError("Rustdoc selector missing after version change")
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
    print("Version browser check: PASS (mike and native Rustdoc selection, desktop/mobile)")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--pages", required=True)
    p.add_argument("--output", default="docs-version-review")
    args = p.parse_args()
    browser_check(Path(args.pages), Path(args.output))


if __name__ == "__main__":
    main()
