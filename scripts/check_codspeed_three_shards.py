#!/usr/bin/env python3
"""Exact 32-node integrity audit for the opt-in weighted 3-shard candidate."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def collect(dest: Path, shard: int | None):
    flags = [
        sys.executable, str(Path(__file__).resolve()),
        "--capture", str(dest),
    ]
    if shard is not None:
        flags += ["--shard-id", str(shard)]
    subprocess.run(flags, cwd=ROOT, check=True)
    return json.loads(dest.read_text(encoding="utf-8"))


def capture(dest: Path, shard: int | None):
    import pytest

    class Recorder:
        def pytest_collection_finish(self, session):
            dest.write_text(json.dumps([x.nodeid for x in session.items]), encoding="utf-8")

    args = ["test/test_Feynman.py", "test/test_MQT.py",
            "--codspeed", "--collect-only", "-q", "-p", "scripts.codspeed_three_shards"]
    if shard is not None:
        args.extend(["--weighted-shard-id", str(shard)])
    if pytest.main(args, plugins=[Recorder()]) != 0 or not dest.exists():
        raise SystemExit(f"Failed to collect three-shard pilot: {shard}")


def audit():
    from scripts.codspeed_three_shards import plan, weight

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        all_nodes = collect(root / "all.json", None)
        if len(all_nodes) != 32 or len(set(all_nodes)) != 32:
            raise SystemExit("Original 32-node CodSpeed catalog has changed")
        parts = [collect(root / f"{i}.json", i) for i in range(3)]
        if not all(parts):
            raise SystemExit("Three-shard candidate has an empty shard")
        found = [n for part in parts for n in part]
        if len(found) != 32 or set(found) != set(all_nodes) or len(set(found)) != 32:
            raise SystemExit("Three-shard candidate lost or duplicated a benchmark")
        alloc = plan(all_nodes)
        if any(alloc[n] != i for i, nodes in enumerate(parts) for n in nodes):
            raise SystemExit("Candidate selection does not match pinned weighted plan")
        print(json.dumps({
            "source": "CodSpeed Simulation 95f8942 placement proxy, not walltime",
            "num_shards": 3, "original_node_ids": len(all_nodes),
            "union": len(found), "missing": 0, "duplicates": 0,
            "counts": [len(x) for x in parts],
            "estimated_weights": [round(sum(weight(n) for n in p), 3) for p in parts],
        }, sort_keys=True))


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--capture":
        capture(Path(sys.argv[2]), None if sys.argv[3] == "all" else int(sys.argv[3]))
    elif len(sys.argv) == 1:
        audit()
    elif len(sys.argv) == 3 and sys.argv[1] == "--capture":
        capture(Path(sys.argv[2]), None)
    else:
        raise SystemExit("usage: check_codspeed_three_shards.py [--capture PATH [0|1|2]]")
