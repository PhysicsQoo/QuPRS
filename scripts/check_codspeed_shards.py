#!/usr/bin/env python3
"""Assert five CodSpeed shards collect exactly the unsharded benchmark suite.

Uses pytest collection hooks instead of parsing potentially version-dependent
stdout. Each collection runs in a fresh subprocess to avoid pytest plugin state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = (
    ROOT / "test/test_Feynman.py",
    ROOT / "test/test_MQT.py",
    ROOT / "benchmarks/codspeed/test_mqt_qasm261_simulation.py",
)
NUM_SHARDS = 5
CANONICAL_COUNT = 32
ADDON_COUNT = 12
TOTAL_COUNT = CANONICAL_COUNT + ADDON_COUNT
ADDON_PREFIX = "benchmarks/codspeed/test_mqt_qasm261_simulation.py::"
ADDON_SHA256 = "59d46eb951ca5280fddd19000ca14bfc45a71ea22717b178e76b76fd715e9a18"
# Immutable 8 Feynman + 24 MQT exact node IDs; changing any ID requires an
# explicit benchmark-baseline migration, not merely preserving the count.
CANONICAL_SHA256 = '7eb82617bf092c81c6a6bde6e8cd05cec9bab71879f17b2bf315c9c420c7c8ed'


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
        # Keep the main-published original 32 stable AND require every new
        # Qiskit 2.6.1 Level-0 URI as a separate additive identity.
        legacy = [uri for uri in whole if uri.startswith(
            ("test/test_Feynman.py::", "test/test_MQT.py::"))]
        addon = [uri for uri in whole if uri.startswith(ADDON_PREFIX)]
        digest = lambda values: hashlib.sha256(
            "\n".join(sorted(values)).encode("utf-8")
        ).hexdigest()
        if len(legacy) != CANONICAL_COUNT or digest(legacy) != CANONICAL_SHA256:
            raise SystemExit(
                "Canonical CodSpeed 32-node identity changed: "
                f"count={len(legacy)}, sha256={digest(legacy)}"
            )
        if len(addon) != ADDON_COUNT or digest(addon) != ADDON_SHA256:
            raise SystemExit(
                "QASM261 additive 24-node identity changed: "
                f"count={len(addon)}, sha256={digest(addon)}"
            )
        if len(whole) != TOTAL_COUNT:
            raise SystemExit(
                f"Simulation requires 32 legacy + 12 QASM261 = {TOTAL_COUNT} "
                f"unique identities; found {len(whole)}"
            )
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
            "unsharded": len(whole), "legacy": len(legacy),
            "qasm261_addon": len(addon), "num_shards": NUM_SHARDS,
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
