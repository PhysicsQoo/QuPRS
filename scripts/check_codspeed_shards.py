#!/usr/bin/env python3
"""Assert five CodSpeed shards collect exactly the unsharded benchmark suite.

Uses pytest collection hooks instead of parsing potentially version-dependent
stdout. Each collection runs in a fresh subprocess to avoid pytest plugin state.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = (ROOT / "test/test_Feynman.py", ROOT / "test/test_MQT.py")
NUM_SHARDS = 5


def capture(destination: Path, shard: int | None) -> None:
    import pytest

    class Collect:
        def pytest_collection_finish(self, session):
            destination.write_text(
                json.dumps([item.nodeid for item in session.items]),
                encoding="utf-8",
            )

    flags = [
        str(path) for path in BENCHMARKS
    ] + ["--codspeed", "--collect-only", "-q"]
    if shard is not None:
        flags += ["--shard-id", str(shard), "--num-shards", str(NUM_SHARDS)]
    result = pytest.main(flags, plugins=[Collect()])
    if result != 0 or not destination.exists():
        raise SystemExit(
            f"pytest collection failed for shard={shard}: exit={result}"
        )


def collect(destination: Path, shard: int | None) -> list[str]:
    args = [sys.executable, str(Path(__file__).resolve()),
            "--capture", str(destination)]
    if shard is not None:
        args += ["--shard-id", str(shard)]
    subprocess.run(args, cwd=ROOT, check=True)
    return json.loads(destination.read_text(encoding="utf-8"))


def validate() -> None:
    with tempfile.TemporaryDirectory() as temp:
        dest = Path(temp)
        whole = collect(dest / "whole.json", None)
        if not whole or len(whole) != len(set(whole)):
            raise SystemExit("Unsharded collection is empty or has duplicate node IDs")
        full = set(whole)
        owner: dict[str, int] = {}
        counts: dict[int, int] = {}
        for shard in range(NUM_SHARDS):
            ids = collect(dest / f"shard-{shard}.json", shard)
            counts[shard] = len(ids)
            if not ids or len(ids) != len(set(ids)):
                raise SystemExit(f"Unexpected empty or duplicated shard {shard}: {ids}")
            for node in ids:
                if node in owner:
                    raise SystemExit(
                        f"Duplicate benchmark node {node!r} in shards "
                        f"{owner[node]} and {shard}"
                    )
                owner[node] = shard
        collected = set(owner)
        if collected != full:
            raise SystemExit(
                f"Missing={sorted(full - collected)}, extra={sorted(collected - full)}"
            )
        print(json.dumps({
            "unsharded": len(whole), "num_shards": NUM_SHARDS,
            "shard_counts": counts, "union": len(collected),
            "missing": 0, "duplicate": 0,
        }, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--shard-id", type=int)
    a = parser.parse_args()
    if a.capture:
        if a.shard_id is not None and not 0 <= a.shard_id < NUM_SHARDS:
            parser.error("shard-id must be 0..4")
        capture(a.capture, a.shard_id)
    else:
        validate()
