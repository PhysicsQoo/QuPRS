#!/usr/bin/env python3
"""Browser review of the composed Zensical + rustdoc documentation preview.

Run after building the static site and placing native rustdoc under site/rust-api.
The browser uses the same URL prefix as the proposed GitHub Pages preview.
"""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


class SilentHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args: object) -> None:
        pass


def verify_browser(site: Path, output: Path, base_path: str) -> None:
    site = site.resolve()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    prefix = base_path.strip("/")
    if prefix != "QuPRS/pr-preview/pr-159":
        raise ValueError("Unexpected documentation preview location")
    with TemporaryDirectory(prefix="quprs-preview-") as temp:
        mount = Path(temp) / prefix
        mount.parent.mkdir(parents=True)
        os.symlink(site, mount, target_is_directory=True)
        handler = partial(SilentHandler, directory=temp)
        with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
            worker = Thread(target=server.serve_forever, daemon=True)
            worker.start()
            origin = f"http://127.0.0.1:{server.server_port}"
            base = f"{origin}/{prefix}/"
            records: list[dict[str, object]] = []
            failures: list[str] = []
            try:
                with sync_playwright() as engine:
                    browser = engine.chromium.launch(headless=True)
                    try:
                        scenarios = [
                            ("overview", "", "QuPRS"),
                            ("path-sum", "path-sum/", "Path-sum representation and reduction"),
                            ("wmc", "weighted-model-counting/", "Weighted model counting and solver contracts"),
                            ("examples", "examples/", "Executable examples"),
                            ("python-api", "python-api/", "Python API"),
                            ("rustdoc", "rust-api/pathsum/index.html", "pathsum"),
                        ]
                        for name, suffix, heading in scenarios:
                            page = browser.new_page(viewport={"width": 1366, "height": 900}, device_scale_factor=1)
                            broken: list[str] = []
                            page.on("response", lambda response, broken=broken:
                                    broken.append(f"{response.status} {response.url}")
                                    if response.status >= 400 and urlparse(response.url).netloc == urlparse(origin).netloc else None)
                            response = page.goto(base + suffix, wait_until="networkidle", timeout=30000)
                            if response is None or response.status != 200:
                                raise AssertionError(f"Unexpected HTTP result for {name}")
                            if heading.casefold() not in page.locator("h1").first.inner_text().casefold():
                                raise AssertionError(f"Missing heading on {name}")
                            if name in ("path-sum", "wmc"):
                                page.wait_for_function("document.querySelectorAll('mjx-container').length > 0",
                                                       timeout=20000)
                                math_count = page.locator("mjx-container").count()
                                display_count = page.locator('mjx-container[display="true"]').count()
                                required_displays = 6 if name == "path-sum" else 4
                                if display_count < required_displays:
                                    raise AssertionError(
                                        f"Unrendered display math on {name}: "
                                        f"{display_count}/{required_displays}"
                                    )
                                visible_text = page.locator("main").inner_text()
                                if re.search(r"\$\s*\\(?:sum|sqrt|frac|operatorname)|\$\s*D_\{", visible_text):
                                    raise AssertionError(f"Raw LaTeX leaked into rendered content: {name}")
                            else:
                                math_count = 0
                                display_count = 0
                            if name == "examples" and page.locator("pre code").count() < 5:
                                raise AssertionError("Published code blocks are not visible")
                            if name == "wmc" and page.locator("table").count() < 2:
                                raise AssertionError("Solver and result tables are not visible")
                            if name == "overview":
                                links = page.locator('a[href*="path-sum/"],a[href*="examples/"]')
                                if links.count() < 2:
                                    raise AssertionError("Expected navigation links missing")
                            if broken:
                                raise AssertionError(f"Broken local resources in {name}: {broken[:5]}")
                            page.screenshot(path=str(output / f"desktop-{name}.png"), full_page=True)
                            records.append({"page": name, "status": 200, "math": math_count, "display_math": display_count,
                                            "screenshot": f"desktop-{name}.png"})
                            page.close()

                        mobile = browser.new_page(viewport={"width": 390, "height": 844},
                                                  device_scale_factor=1, is_mobile=True,
                                                  has_touch=True)
                        for name, suffix in (("overview", ""), ("path-sum", "path-sum/"),
                                             ("wmc", "weighted-model-counting/"),
                                             ("examples", "examples/")):
                            response = mobile.goto(base + suffix, wait_until="networkidle", timeout=30000)
                            if response is None or response.status != 200:
                                raise AssertionError(f"Mobile page failed: {name}")
                            if not mobile.locator("h1").first.is_visible():
                                raise AssertionError(f"Mobile heading not visible: {name}")
                            if name in ("wmc", "path-sum"):
                                mobile.wait_for_function(
                                    "document.querySelectorAll('mjx-container[display=\\\"true\\\"]').length > 1",
                                    timeout=20000,
                                )
                                clipped = mobile.evaluate("""() => Array.from(
                                    document.querySelectorAll('mjx-container[display="true"] mjx-math')
                                ).map((node, index) => {
                                    const b = node.getBoundingClientRect();
                                    return {index, left: b.left, right: b.right};
                                }).filter(b => b.left < -1 || b.right > window.innerWidth + 1)""")
                                if clipped:
                                    raise AssertionError(f"MathJax content clipped on mobile {name}: {clipped}")
                            mobile.screenshot(path=str(output / f"mobile-{name}.png"), full_page=True)
                        mobile.close()
                    finally:
                        browser.close()
            except Exception as exc:
                failures.append(str(exc))
                raise
            finally:
                (output / "browser-review.json").write_text(
                    json.dumps({"base_path": base_path, "scenarios": records,
                                "failures": failures}, indent=2) + "\n",
                    encoding="utf-8",
                )
                server.shutdown()
                worker.join(timeout=10)
            print(f"Browser review: {len(records)} desktop pages, 4 mobile screenshots PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default="site")
    parser.add_argument("--output", default="docs-preview-review")
    parser.add_argument("--base-path", default="/QuPRS/pr-preview/pr-159/")
    args = parser.parse_args()
    verify_browser(Path(args.site), Path(args.output), args.base_path)


if __name__ == "__main__":
    main()
