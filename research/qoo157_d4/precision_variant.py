"""Research-only GMP precision-timing A/B patch for a pinned d4 checkout.

Makes one anchored edit to upstream c++/counter/src/Main.cpp, setting GMP
precision before CLI parsing and before any complex weights are constructed.
Never publish or link patched d4 with QuPRS: it is an ephemeral CI control.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

UPSTREAM_SHA = "be15f91f3e9769e1f5cb175fa27e3eca3a1ea690"
MARKER = "// QOO-157 controlled GMP precision experiment (not an upstream patch)"
OLD = "int main(int argc, char** argv) {\n  auto start = std::chrono::system_clock::now();"
NEW = ("int main(int argc, char** argv) {\n"
       f"  {MARKER}\n"
       "  mpf_set_default_prec(426);\n"
       "  auto start = std::chrono::system_clock::now();")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def patch_source(content: str) -> str:
    if MARKER in content:
        raise ValueError("precision variant already patched")
    if content.count(OLD) != 1:
        raise ValueError("unrecognized pinned upstream Main.cpp anchor")
    return content.replace(OLD, NEW)


def apply_variant(upstream: Path, evidence: Path):
    upstream = upstream.resolve()
    evidence = evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    revision = subprocess.check_output(
        ["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != UPSTREAM_SHA:
        raise ValueError(f"unapproved upstream revision: {revision}")
    source = upstream / "c++" / "counter" / "src" / "Main.cpp"
    current = source.read_bytes()
    amended = patch_source(current.decode("utf-8")).encode("utf-8")
    source.write_bytes(amended)
    report = {
        "upstream_commit": revision,
        "patched_file": "c++/counter/src/Main.cpp",
        "original_source_sha256": sha256(current),
        "patched_source_sha256": sha256(amended),
        "patch_policy": "single anchored addition before counter/parser; research-only",
        "gmp_precision_bits_before_counter": 426,
        "precision_certified": False,
    }
    dest = evidence / "precision_variant_provenance.json"
    dest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(dest), **report}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    apply_variant(args.upstream, args.evidence)


if __name__ == "__main__":
    main()
