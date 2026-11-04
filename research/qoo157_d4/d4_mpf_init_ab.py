"""Research-only pinned d4 GMP precision-initialization A/B.

Only a throwaway upstream checkout is patched. QuPRS/GPMC/Ganak source and
product defaults are unchanged. Printed output is not an error certificate.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess

from poc_d4 import UPSTREAM_SHA, parse_d4_count, oracle_count
from precision_probe import cases

ANCHOR = "  // Use the provided configuration.\n"
MARKER = "QOO157_GMP_INIT_AB_ONLY"
INSERT = r'''  // QOO157_GMP_INIT_AB_ONLY: opt-in in a temporary external d4 checkout.
  // GMP default precision must be set BEFORE the semiring weights are created.
  if (const char* qoo157_bits = std::getenv("QOO157_D4_MPF_BITS")) {
    char* end = nullptr;
    unsigned long bits = std::strtoul(qoo157_bits, &end, 10);
    if (end == qoo157_bits || *end != '\0' || bits < 64 || bits > 2048) {
      std::cerr << "QOO157_INVALID_PRECISION\n";
      std::exit(2);
    }
    mpf_set_default_prec(bits);
    std::cerr << "QOO157_DEFAULT_BITS=" << mpf_get_default_prec() << "\n";
  }
'''
BITS = (64, 128, 256, 426)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def patched_source(source: str) -> str:
    if MARKER in source:
        raise ValueError("research patch already applied")
    if source.count(ANCHOR) != 1 or source.count("T result = counter->run();") != 1:
        raise ValueError("pinned d4 source structure changed")
    if source.index(ANCHOR) < source.index("T result = counter->run();"):
        raise ValueError("expected counter() after countModels()")
    if "#include <cstdlib>" not in source:
        source = source.replace("#include <cassert>\n",
                                "#include <cassert>\n#include <cstdlib>\n", 1)
    return source.replace(ANCHOR, INSERT + ANCHOR, 1)


def patch(root: Path, file: Path, out: Path) -> None:
    sha = subprocess.check_output(["git", "-C", str(root),
                                   "rev-parse", "HEAD"], text=True).strip()
    if sha != UPSTREAM_SHA:
        raise ValueError("d4 upstream SHA not pinned: " + sha)
    before = file.read_bytes()
    after = patched_source(before.decode()).encode()
    out.mkdir(parents=True, exist_ok=True)
    file.write_bytes(after)
    (out / "source-patch-provenance.json").write_text(json.dumps({
        "upstream_sha": sha, "source": str(file),
        "before_sha256": sha256(before), "after_sha256": sha256(after),
        "patch_scope": "ephemeral external d4 checkout only",
    }, indent=2) + "\n")


def native(binary: Path, cnf: Path, bits: int | None, prefix: Path):
    env = os.environ.copy()
    env.pop("QOO157_D4_MPF_BITS", None)
    if bits is not None:
        env["QOO157_D4_MPF_BITS"] = str(bits)
    process = subprocess.Popen(
        [str(binary.resolve()), "-i", str(cnf.resolve())],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, env=env, start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=30)
    except subprocess.TimeoutExpired as exc:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise RuntimeError("d4 timed out") from exc
    prefix.parent.mkdir(parents=True, exist_ok=True)
    prefix.with_suffix(".stdout").write_text(stdout)
    prefix.with_suffix(".stderr").write_text(stderr)
    if process.returncode:
        raise RuntimeError(f"d4 exited {process.returncode}: {stderr[:400]}")
    if bits is not None:
        found = re.search(r"QOO157_DEFAULT_BITS=(\d+)", stderr)
        if not found or int(found.group(1)) < bits:
            raise RuntimeError("requested GMP precision was not effective")
    return parse_d4_count(stdout)


def pair(value):
    return [str(value[0]), str(value[1])]


def sweep(baseline: Path, changed: Path, out: Path, extra_cnfs: list[Path]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    if sha256(baseline.read_bytes()) == sha256(changed.read_bytes()):
        raise ValueError("identical experimental and baseline binaries")
    records = []
    experimental_inputs = list(cases().items())
    for path in extra_cnfs:
        experimental_inputs.append(("quprs_" + path.stem, path.read_text()))
    for name, source in experimental_inputs:
        inp = out / (name + ".cnf")
        inp.write_text(source)
        expected = oracle_count(source)
        record = {"name": name, "input_sha256": sha256(source.encode()),
                  "oracle": pair(expected), "arms": {}}
        for bits in (None, *BITS):
            arm = "original" if bits is None else "bits_" + str(bits)
            measured = native(baseline if bits is None else changed, inp,
                              bits, out / "raw" / (name + "_" + arm))
            difference = tuple(abs(a-b) for a,b in zip(measured, expected))
            scale = max(Fraction(1), abs(expected[0]), abs(expected[1]))
            strict_count_screen = all(d <= scale * Fraction(1, 10**25)
                                      for d in difference)
            # A small count needs relative accuracy; 0 must not pass as 1e-40.
            relative_ok = all(
                (a == b) if b == 0
                else a != 0 and abs(a-b) <= abs(b) * Fraction(1, 10**10)
                for a,b in zip(measured, expected)
            )
            record["arms"][arm] = {
                "measured": pair(measured),
                "absolute_error": [str(v) for v in difference],
                "strict_1e25_count_screen": strict_count_screen,
                "nonzero_relative_1e-10": relative_ok,
            }
        records.append(record)
        (out / "report.json").write_text(json.dumps({
            "complete": False, "arithmetic_precision_certified": False,
            "records": records}, indent=2) + "\n")
    baseline_lost = any(not r["arms"]["original"]["nonzero_relative_1e-10"]
                        for r in records)
    fixed = all(r["arms"]["bits_426"]["nonzero_relative_1e-10"]
                for r in records)
    source_rows = [r for r in records if r["name"].startswith("quprs_")]
    source_gate = (
        (not extra_cnfs)
        or (len(source_rows) == len(extra_cnfs)
            and all(r["arms"]["bits_426"]["strict_1e25_count_screen"]
                    for r in source_rows))
    )
    report = {
        "complete": True, "upstream_sha": UPSTREAM_SHA,
        "baseline_binary_sha256": sha256(baseline.read_bytes()),
        "experimental_binary_sha256": sha256(changed.read_bytes()),
        "ab_gate": "PASS" if fixed and baseline_lost and source_gate else "FAIL",
        "quprs_source_cnf_gate": "PASS" if source_gate else "FAIL",
        "quprs_source_cnf_count": len(source_rows),
        "arithmetic_precision_certified": False,
        "warning": "finite GMP mpf and 50-digit stdout are not an error certificate",
        "records": records,
    }
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"report": str(out / "report.json"),
                      "ab_gate": report["ab_gate"],
                      "cases": len(records)}))
    if report["ab_gate"] != "PASS":
        raise SystemExit(2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("patch")
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--file", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("sweep")
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--patched", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--cnf", type=Path, action="append", default=[])
    args = parser.parse_args()
    if args.action == "patch":
        patch(args.root, args.file, args.out)
    else:
        sweep(args.baseline, args.patched, args.out, args.cnf)


if __name__ == "__main__":
    main()
