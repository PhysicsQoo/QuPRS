#!/usr/bin/env python3
"""Confirm immutable crates.io publication after Cargo's index wait.

An accepted upload can precede index propagation. This verifier only reads
crates.io metadata: it never retries an upload or relaxes a mismatch.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class PublicationNotConfirmed(RuntimeError):
    """A registry upload is not confirmed by exact version and SHA-256."""


def is_index_propagation_timeout(output: str) -> bool:
    if re.search(r"(?i)\b(?:401|403|422|unauthori[sz]ed|forbidden|permission denied|invalid token)\b", output):
        return False
    return bool(re.search(
        r"(?i)(?:timed out|timeout).{0,160}\bindex\b|\bindex\b.{0,160}(?:timed out|timeout)",
        output,
    ))


def confirm_published(
    version: str,
    crate_file: Path,
    *,
    attempts: int = 8,
    delay_seconds: float = 5,
    opener=urlopen,
    sleeper=time.sleep,
) -> None:
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?", version):
        raise PublicationNotConfirmed("Invalid Cargo version")
    if not 1 <= attempts <= 12 or delay_seconds < 0:
        raise ValueError("Invalid bounded polling options")
    digest = hashlib.sha256(crate_file.read_bytes()).hexdigest()
    url = f"https://crates.io/api/v1/crates/quprs/{version}"
    for attempt in range(attempts):
        request = Request(url, headers={
            "User-Agent": "QuPRS-release-verification/1.0",
            "Accept": "application/json",
            "Cache-Control": "no-cache",
        })
        try:
            with opener(request, timeout=12) as response:
                if response.status != 200:
                    raise PublicationNotConfirmed(f"Unexpected registry HTTP {response.status}")
                metadata = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code in (404, 429, 500, 502, 503, 504):
                metadata = None
            else:
                raise PublicationNotConfirmed(f"Registry denied verification (HTTP {exc.code})") from exc
        except (URLError, TimeoutError, ConnectionError):
            metadata = None
        except (UnicodeError, ValueError) as exc:
            raise PublicationNotConfirmed("Malformed registry response") from exc
        if metadata is not None:
            record = metadata.get("version") if isinstance(metadata, dict) else None
            if not isinstance(record, dict):
                raise PublicationNotConfirmed("Missing version record")
            if (record.get("num") != version
                    or record.get("yanked") is not False
                    or record.get("checksum") != digest):
                raise PublicationNotConfirmed("Registry version, yanked state or SHA-256 differs")
            return
        if attempt + 1 < attempts:
            sleeper(delay_seconds)
    raise PublicationNotConfirmed("Exact registry version unavailable after bounded polling")


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit("Usage: reconcile_crates_io_publish.py VERSION CRATE_FILE CARGO_LOG CARGO_EXIT_CODE")
    version, crate, log, code = sys.argv[1:]
    try:
        if int(code) != 0 and not is_index_propagation_timeout(Path(log).read_text(encoding="utf-8")):
            raise PublicationNotConfirmed("Cargo failed without an identifiable index propagation timeout")
        confirm_published(version, Path(crate))
    except (PublicationNotConfirmed, OSError, ValueError) as exc:
        raise SystemExit(f"Crate publication not confirmed: {exc}") from exc


if __name__ == "__main__":
    main()
