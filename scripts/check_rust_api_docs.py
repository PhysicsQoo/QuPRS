#!/usr/bin/env python3
"""Compose and validate the native Rust API reference alongside the site."""

from __future__ import annotations

import argparse
from functools import partial
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import shutil
from threading import Thread
from urllib.parse import unquote, urlsplit
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
RUSTDOC_ROOT = ROOT / "rust" / "target" / "doc"
SITE_ROOT = ROOT / "site"
RUST_API = SITE_ROOT / "rust-api"
TRACKER = re.compile(r"\b[A-Z]{2,8}-[0-9]{1,6}\b")


class Assets(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.paths: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag in {"script", "img", "link"}:
            uri = values.get("src" if tag in {"script", "img"} else "href")
            if uri:
                self.paths.append(uri)


class SilentHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args: object) -> None:
        pass


def compose() -> None:
    if not (RUSTDOC_ROOT / "pathsum" / "index.html").is_file():
        raise AssertionError("cargo doc did not generate pathsum/index.html")
    if RUST_API.exists():
        raise AssertionError("Rust API destination must be absent before composition")
    shutil.copytree(RUSTDOC_ROOT, RUST_API)
    # Cargo may omit its top-level crate index for a single-package build.
    # Rustdoc's own Help/Settings navigation expects this landing page.
    (RUST_API / "index.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="robots" content="noindex,nofollow">'
        '<meta http-equiv="refresh" content="0;url=pathsum/index.html">'
        '<title>Rust API Reference</title></head>'
        '<body><a href="pathsum/index.html">pathsum crate reference</a></body></html>\n',
        encoding="utf-8",
    )


def check_assets() -> None:
    rust_index = RUST_API / "pathsum" / "index.html"
    if not rust_index.is_file():
        raise AssertionError("Missing Rust API entry point")
    if not (RUST_API / "index.html").is_file():
        raise AssertionError("Rustdoc landing page missing")
    static = RUST_API / "static.files"
    if not static.is_dir() or not any(static.iterdir()):
        raise AssertionError("Missing Rustdoc shared static assets")
    html = rust_index.read_text(encoding="utf-8")
    if "VerificationOptions" not in html:
        raise AssertionError("Public Rust verification types are not documented")

    # Native rustdoc assets are outside Zensical's Markdown link checker.
    checked = 0
    for page in RUST_API.rglob("*.html"):
        source = page.read_text(encoding="utf-8")
        if TRACKER.search(source):
            raise AssertionError(f"Non-public identifier in Rust API HTML: {page}")
        parser = Assets()
        parser.feed(source)
        for uri in parser.paths:
            split = urlsplit(uri)
            if split.scheme or split.netloc or uri.startswith("//") or not split.path:
                continue
            target = (page.parent / unquote(split.path)).resolve()
            if not target.is_relative_to(SITE_ROOT.resolve()) or not target.is_file():
                raise AssertionError(f"Invalid Rustdoc asset: {page}: {uri}")
            checked += 1
    if checked == 0:
        raise AssertionError("Rustdoc asset validation did not check any resources")

    reference = (SITE_ROOT / "reference" / "index.html").read_text(encoding="utf-8")
    if 'href="../rust-api/pathsum/index.html"' not in reference:
        raise AssertionError("The main site does not link to the Rust API")


def check_http() -> None:
    handler = partial(SilentHandler, directory=str(SITE_ROOT))
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            static = next((RUST_API / "static.files").glob("*.css"), None)
            if static is None:
                raise AssertionError("No Rustdoc stylesheet was generated")
            requests = [
                "reference/index.html",
                "python-api/index.html",
                "rust-api/pathsum/index.html",
                static.relative_to(SITE_ROOT).as_posix(),
            ]
            for path in requests:
                address = f"http://127.0.0.1:{server.server_port}/{path}"
                with urlopen(address, timeout=10) as response:
                    if response.status != 200 or not response.read(64):
                        raise AssertionError(f"Invalid site response: {path}")
        finally:
            server.shutdown()
            thread.join(timeout=10)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compose", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not (args.compose or args.check):
        parser.error("select --compose and/or --check")
    if args.compose:
        compose()
    if args.check:
        check_assets()
        check_http()


if __name__ == "__main__":
    main()
