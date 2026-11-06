#!/usr/bin/env python3
"""Check all local links and static assets in a composed Zensical + rustdoc site.

This complements (does not replace) Zensical's strict Markdown link checks.
It resolves every generated HTML href/src against the actual deployment prefix.
"""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import unquote, urljoin, urlsplit


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refs: list[tuple[str, str]] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.add(attributes["id"])
        if tag in {"a", "link"} and attributes.get("href"):
            self.refs.append((tag, attributes["href"]))
        if tag in {"script", "img", "iframe", "source"} and attributes.get("src"):
            self.refs.append((tag, attributes["src"]))


def check_links(site: Path, base_url: str) -> int:
    site = site.resolve()
    prefix = base_url.rstrip("/") + "/"
    origin = urlsplit(prefix)
    if origin.scheme not in {"http", "https"} or not origin.netloc:
        raise AssertionError("Expected an absolute HTTP(S) preview URL")
    root_prefix = origin.path.rstrip("/") + "/"
    if ".." in root_prefix.split("/"):
        raise AssertionError("Unsafe preview URL prefix")

    page_data: dict[str, Page] = {}
    for path in site.rglob("*.html"):
        relative = path.relative_to(site).as_posix()
        parsed = Page()
        parsed.feed(path.read_text(encoding="utf-8"))
        page_data[relative] = parsed

    checked = 0
    failures: list[str] = []
    for relative, parsed in page_data.items():
        current_url = urljoin(prefix, relative)
        for tag, raw in parsed.refs:
            target = urlsplit(urljoin(current_url, raw))
            # External websites, mailto links and JS-only anchors are not
            # local resources; they need separate online/network checks.
            if target.scheme not in {"http", "https"} or target.netloc != origin.netloc:
                continue
            path = unquote(target.path)
            if not path.startswith(root_prefix):
                failures.append(f"{relative}: {tag} {raw!r} escapes deployment prefix")
                continue
            target_relative = path[len(root_prefix):]
            if not target_relative or path.endswith("/"):
                target_relative += "index.html"
            dest = (site / target_relative).resolve()
            if not dest.is_relative_to(site):
                failures.append(f"{relative}: {tag} {raw!r} escapes site directory")
                continue
            if not dest.is_file():
                failures.append(f"{relative}: {tag} {raw!r} targets a missing file")
                continue
            # Rustdoc creates some trait anchors with JavaScript at runtime.
            # All Zensical/Markdown anchors, however, must exist statically.
            if tag == "a" and target.fragment and not target_relative.startswith("rust-api/"):
                fragment = unquote(target.fragment)
                if target_relative.endswith(".html") and fragment not in page_data[target_relative].ids:
                    failures.append(f"{relative}: {tag} {raw!r} targets a missing anchor")
                    continue
            checked += 1
    if failures:
        raise AssertionError("Broken generated site links:\n" + "\n".join(failures[:35]))
    if checked < 100:
        raise AssertionError(f"Too few links were checked: {checked}")
    return checked


def negative_fixture() -> None:
    with TemporaryDirectory(prefix="quprs-links-") as d:
        root = Path(d)
        (root / "index.html").write_text(
            '<html><body><a href="missing/page.html">Missing</a></body></html>',
            encoding="utf-8",
        )
        try:
            check_links(root, "https://example.org/QuPRS/pr-preview/pr-1/")
        except AssertionError as exc:
            if "targets a missing file" not in str(exc):
                raise
        else:
            raise AssertionError("Broken link fixture incorrectly passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default="site")
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    negative_fixture()
    checked = check_links(Path(args.site), args.base_url)
    print(f"Generated site links: PASS ({checked} local links/assets validated)")
