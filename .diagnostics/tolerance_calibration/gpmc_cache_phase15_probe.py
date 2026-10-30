#!/usr/bin/env python3
"""Disposable-source instrumentation for pinned GPMC cache semantics.

Copies GPMC before patching; does not change the submodule or production tool.
Both unmodified and instrumented native binaries evaluate the same original CNF.
"""
from __future__ import annotations
import argparse
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

QFT_HASH = "20ee9e55eb1fc644d08daf130d180ded46f06f67897fa46f57b4f4ef4ef7f8f1"
SUMMARY = re.compile(r"P15_CACHE_SUMMARY stores=(\d+) zero_stores=(\d+) "
                     r"unsat_zero_stores=(\d+) sat_zero_stores=(\d+) "
                     r"hits=(\d+) zero_hits=(\d+)")
MARKER = "c s exact double prec-sci "


def patch(path: Path, old: str, new: str):
    source = path.read_text()
    if source.count(old) != 1:
        raise ValueError("pinned source patch anchor mismatch: " + str(path)
                         + " occurrences=" + str(source.count(old)))
    path.write_text(source.replace(old, new))


def prepare(source: Path, output: Path):
    shutil.copytree(source, output, ignore=shutil.ignore_patterns(".git", "build"))
    mgr = output / "core/ComponentManager.cc"
    cnt = output / "core/Counter.cc"
    helper = r'''
#include <iostream>
namespace {
struct P15Counters {
    unsigned long long stores=0, zero_stores=0, unsat_zero_stores=0;
    unsigned long long sat_zero_stores=0, hits=0, zero_hits=0;
    ~P15Counters() {
        std::cerr << "P15_CACHE_SUMMARY stores=" << stores
                  << " zero_stores=" << zero_stores
                  << " unsat_zero_stores=" << unsat_zero_stores
                  << " sat_zero_stores=" << sat_zero_stores
                  << " hits=" << hits << " zero_hits=" << zero_hits << "\n";
    }
};
P15Counters p15;
}
extern "C" void p15_store(int zero, int exists) {
    ++p15.stores;
    if (zero) {
        ++p15.zero_stores;
        if (exists) ++p15.sat_zero_stores;
        else ++p15.unsat_zero_stores;
    }
}
extern "C" void p15_hit(int zero) {
    ++p15.hits;
    if (zero) ++p15.zero_hits;
}
'''
    patch(mgr, "#define CACHE", "#define CACHE\n" + helper)
    anchor = "if (cache_.requestValueOf(*comp_stack_.back(), tmp_model_count, cachedNode)) {"
    patch(mgr, anchor, anchor + "\n"
          "                        p15_hit(tmp_model_count == 0);")
    patch(cnt, "#include \"c-mpfr/ComplexMPFR.h\"",
          "#include \"c-mpfr/ComplexMPFR.h\"\n"
          "extern \"C\" void p15_store(int zero, int exists);")
    anchor = ("cmpmgr.cacheModelCountOf(cmpmgr.topComponent().id(), "
              "cmpmgr.topDecision().totalModels(), snode);")
    patch(cnt, anchor, "p15_store(cmpmgr.topDecision().totalModels() == 0,\n"
          "                          cmpmgr.topDecision().hasModel());\n"
          "            " + anchor)


def count(text):
    fields = [s[len(MARKER):].strip().replace(" ", "")
              for s in text.splitlines() if s.startswith(MARKER)]
    if len(fields) != 1:
        raise ValueError("missing single complex WMC field")
    value = fields[0]
    if value == "0":
        return Fraction(0), Fraction(0)
    if not value.endswith("i"):
        raise ValueError("bad imaginary suffix")
    body = value[:-1]
    cuts = [i for i in range(1, len(body))
            if body[i] in "+-" and body[i-1] not in "eE"]
    if len(cuts) != 1:
        raise ValueError("ambiguous WMC count")
    return Fraction(Decimal(body[:cuts[0]])), Fraction(Decimal(body[cuts[0]:]))


def run(binary, cnf, label, switches, output):
    cmd = [str(binary), "-mode=1", "-prec=90", *switches, str(cnf)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    (output / (label + ".stdout")).write_text(p.stdout)
    (output / (label + ".stderr")).write_text(p.stderr)
    if p.returncode:
        raise RuntimeError(f"GPMC native exit={p.returncode}: {label}")
    return {"sat": re.findall(r"^s (SATISFIABLE|UNSATISFIABLE)$", p.stdout, re.M),
            "count": count(p.stdout),
            "trace": SUMMARY.findall(p.stderr),
            "stdout_sha256": sha256(p.stdout.encode()).hexdigest(),
            "stderr_sha256": sha256(p.stderr.encode()).hexdigest()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, type=Path)
    ap.add_argument("--qft", required=True, type=Path)
    ap.add_argument("--baseline", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if sha256(args.qft.read_bytes()).hexdigest() != QFT_HASH:
        raise SystemExit("QFT16 input SHA mismatch")
    rows = []
    with tempfile.TemporaryDirectory(prefix="p15-gpmc-cache-") as root:
        root = Path(root)
        source = root / "GPMC"
        prepare(args.source.resolve(), source)
        for cmd, name in (
            (["cmake", "-S", str(source), "-B", str(root / "build"),
              "-DCMAKE_BUILD_TYPE=Release"], "configure"),
            (["cmake", "--build", str(root / "build"), "-j", "4"], "build"),
        ):
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=250)
            (output / (name + ".stdout")).write_text(p.stdout)
            (output / (name + ".stderr")).write_text(p.stderr)
            if p.returncode:
                raise RuntimeError(f"instrumented C++ {name} failed exit={p.returncode}")
        instrumented = root / "build" / "gpmc"
        assert instrumented.is_file()
        (output / "instrumented-sha256.txt").write_text(
            sha256(instrumented.read_bytes()).hexdigest() + "\n")
        for name, flags in (("default", ["-cs=16"]),
                            ("mainloop-off", ["-cs=16", "-varlim=0"])):
            base = run(args.baseline.resolve(), args.qft, "baseline-" + name, flags, output)
            probe = run(instrumented, args.qft, "probe-" + name, flags, output)
            if len(probe["trace"]) != 1 or len(base["sat"]) != 1:
                raise AssertionError("native cache summary missing or duplicated")
            trace = [int(x) for x in probe["trace"][0]]
            row = {"mode": name, "baseline_sat": base["sat"][0],
                   "probe_sat": probe["sat"][0],
                   "exact_printed_count_match": base["count"] == probe["count"],
                   "stores": trace[0], "zero_stores": trace[1],
                   "unsat_zero_stores": trace[2], "sat_zero_stores": trace[3],
                   "hits": trace[4], "zero_hits": trace[5],
                   "baseline_stdout_sha256": base["stdout_sha256"],
                   "instrumented_stdout_sha256": probe["stdout_sha256"]}
            rows.append(row)
            print("GPMC_NATIVE_CACHE_TRACE " + json.dumps(row), flush=True)
            if base["sat"] != probe["sat"] or base["count"] != probe["count"]:
                raise AssertionError("instrumentation changed source CNF result")
            if trace[4] == 0:
                raise AssertionError("QFT16 control must exercise genuine native cache hits")
    result = {"source_sha": QFT_HASH, "status": "PASS_MATCHED_NATIVE",
              "rows": rows,
              "zero_hit_safety_certified": False,
              "note": "Counter aggregates quantify cache-use but do not prove per-key SAT-existence equality"}
    (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
