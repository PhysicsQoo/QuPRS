"""QOO-157 P3: source-pinned GPMC cache-query denominator SCIENCE ONLY.

Build an unmodified GPMC binary and a scratch *counter-only* version.
This script never patches a Git submodule, changes solver algorithms, times
performance, or invokes CodSpeed. Fail closed on source/semantic drift.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from gpmc_td_ablation import COUNT, COMPLEX
from gpmc_vs_td_factorial import close_enough

EXPECTED_PIN = "a1bda3489e959d3695b6798d327c5a1fc1bed305"
CASES = ("grover4_eq", "qaoa7_neq", "qpeexact8_eq", "qft16_eq")
REPORTED = (
    "conflicts", "decisions", "propagations", "Components", "Split",
    "Cache lookup", "Cache hit", "Cache reduce",
)
COUNTERS = re.compile(r"(?m)^c o (.+?)\s+=\s+(\d+)\b")


def replace_once(text: str, old: str, new: str, scope: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"fail closed: source drift: {scope}: {text.count(old)}")
    return text.replace(old, new, 1)


def prepare_scratch(scratch: Path, provenance: Path) -> None:
    """Mutate only the temp copy; pin source snippets and record exact changes."""
    cc = scratch / "core" / "ComponentCache.cc"
    hh = scratch / "core" / "Component.h"
    if not cc.is_file() or not hh.is_file():
        raise ValueError("GPMC scratch source files missing")
    cc_before, hh_before = cc.read_text(), hh.read_text()
    cc_after = replace_once(
        cc_before,
        "if (!isBucketAt(v))\n\t\treturn false;",
        "num_cache_all_queries_++;\n"
        "\tif (!isBucketAt(v)) {\n"
        "\t\tnum_cache_empty_bucket_misses_++;\n"
        "\t\treturn false;\n"
        "\t}",
        "pre-bucket query guard",
    )
    hh_after = replace_once(
        hh_before,
        "\tuint64_t num_cache_hits_ = 0;",
        "\tuint64_t num_cache_all_queries_ = 0;\n"
        "\tuint64_t num_cache_empty_bucket_misses_ = 0;\n"
        "\tuint64_t num_cache_hits_ = 0;",
        "counter declarations",
    )
    hh_after = replace_once(
        hh_after,
        '\t\tprintf("c o Cache lookup          = %"PRIu64"\\n", num_cache_look_ups_);',
        '\t\tprintf("c o Cache all queries     = %"PRIu64"\\n", num_cache_all_queries_);\n'
        '\t\tprintf("c o Cache empty misses    = %"PRIu64"\\n", num_cache_empty_bucket_misses_);\n'
        '\t\tprintf("c o Cache lookup          = %"PRIu64"\\n", num_cache_look_ups_);',
        "native printStats",
    )
    cc.write_text(cc_after)
    hh.write_text(hh_after)
    provenance.parent.mkdir(parents=True, exist_ok=True)
    provenance.write_text(json.dumps({
        "status": "COUNTER_ONLY_SCRATCH_PATCH_APPLIED",
        "pinned_gpmc_gitlink": EXPECTED_PIN,
        "source_files": {
            "core/ComponentCache.cc": {
                "before_sha256": sha256(cc_before.encode()).hexdigest(),
                "after_sha256": sha256(cc_after.encode()).hexdigest(),
            },
            "core/Component.h": {
                "before_sha256": sha256(hh_before.encode()).hexdigest(),
                "after_sha256": sha256(hh_after.encode()).hexdigest(),
            },
        },
        "does_not_change_solver_branching_cache_policy_or_weights": True,
        "not_a_performance_measurement": True,
    }, indent=2) + "\n")
    print("GPMC_CACHE_COUNTER_SCRATCH_PATCH_PASS")


def run_native(binary: Path, cnf: Path, td: bool) -> dict:
    cmd = [str(binary), "-mode=1", "-prec=38", "-vs=1", "-cs=4000",
           "-td" if td else "-no-td", str(cnf)]
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=55)
    if proc.returncode:
        raise RuntimeError(f"GPMC rc={proc.returncode}: {proc.stderr[:350]}")
    outputs = COUNT.findall(proc.stdout)
    if len(outputs) != 1:
        raise ValueError("exactly one native complex WMC required")
    m = COMPLEX.fullmatch(outputs[0].strip())
    if m is None:
        raise ValueError("malformed complex WMC print")
    vals = tuple(Decimal(z) for z in m.groups())
    if not all(z.is_finite() for z in vals):
        raise ValueError("nonfinite WMC")
    native = {k: int(v) for k, v in COUNTERS.findall(proc.stdout)}
    for key in REPORTED:
        if key not in native:
            raise ValueError(f"native source counter missing: {key}")
    flow = "FlowCutter is running..." in proc.stdout
    if flow != td or (td and ("skip td" in proc.stdout or "ignore td" in proc.stdout)):
        raise ValueError("requested/actual TD mismatch")
    return {"value": vals, "counters": native, "flowcutter": flow,
            "stdout_sha256": sha256(proc.stdout.encode()).hexdigest()}


def science(original: Path, instrumented: Path, cnfs: Path,
            archived: Path, dest: Path) -> None:
    baseline = json.loads(archived.read_text())
    if baseline.get("complete") is not True:
        raise ValueError("archived source science not complete")
    report = {
        "status": "INCOMPLETE",
        "source_pin": EXPECTED_PIN,
        "original_binary_sha256": sha256(original.read_bytes()).hexdigest(),
        "instrumented_binary_sha256": sha256(instrumented.read_bytes()).hexdigest(),
        "cases": {},
        "measurement_type": "source_pinned_count_semantics_only",
        "performance_measurements": False,
        "codspeed_triggered_by_this_workflow": False,
        "internal_mpfr_error_certified": False,
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    for case in CASES:
        source = cnfs / f"{case}.cnf"
        h = sha256(source.read_bytes()).hexdigest()
        row = baseline["cases"][case]
        if h != row["same_cnf_sha256"]:
            raise ValueError(f"source CNF SHA differs: {case}")
        reference = row["precision_pairs"]["38"]["observations"]["gpmc-38"]
        with localcontext() as ctx:
            ctx.prec = 110
            oracle = tuple(
                Decimal(Fraction(reference[k]).numerator) /
                Decimal(Fraction(reference[k]).denominator)
                for k in ("real", "imag")
            )
        data = {}
        for td in (True, False):
            label = "td_on" if td else "td_off"
            a = run_native(original, source, td)
            b = run_native(instrumented, source, td)
            for name, result in (("original", a), ("instrumented", b)):
                ok, delta, bound = close_enough(result["value"], oracle)
                if not ok:
                    raise ValueError(f"{case}/{label}/{name}: WMC mismatch {delta}>{bound}")
            if a["value"] != b["value"]:
                raise ValueError(f"{case}/{label}: counter patch changed native WMC print")
            counters_equal = all(
                a["counters"][key] == b["counters"][key] for key in REPORTED
            )
            diagnostic = None
            if not counters_equal:
                # Do not silently attribute divergence to the added counters:
                # independently rerun EACH binary, same CNF and flags.
                a2 = run_native(original, source, td)
                b2 = run_native(instrumented, source, td)
                for name, x in (("original_repeat", a2), ("instrumented_repeat", b2)):
                    ok, delta, bound = close_enough(x["value"], oracle)
                    if not ok or x["value"] != a["value"]:
                        raise ValueError(
                            f"{case}/{label}/{name}: repeated WMC print changed "
                            f"or science screen failed: {delta}>{bound}")
                diagnostic = {
                    "original_repeat_counters": a2["counters"],
                    "instrumented_repeat_counters": b2["counters"],
                    "original_repeat_identity": (
                        a["counters"] == a2["counters"]),
                    "instrumented_repeat_identity": (
                        b["counters"] == b2["counters"]),
                    "original_repeat_stdout_sha256": a2["stdout_sha256"],
                    "instrumented_repeat_stdout_sha256": b2["stdout_sha256"],
                    "repeat_cross_binary_identical": all(
                        a2["counters"][key] == b2["counters"][key]
                        for key in REPORTED),
                }
                print("QOO157_SEARCH_COUNTER_DIVERGENCE",
                      case, label, json.dumps(diagnostic), flush=True)
            native = b["counters"]
            C = native["Components"]
            H = native["Cache hit"]
            L = native["Cache lookup"]
            A = native.get("Cache all queries")
            E = native.get("Cache empty misses")
            formula_ok = (
                A is not None and E is not None and A > 0
                and C >= 1 and L >= H and A == H + C - 1
                and E == A - L
            )
            data[label] = {
                "cnf_sha256": h,
                "original_count_real_imag": [str(z) for z in a["value"]],
                "original_stdout_sha256": a["stdout_sha256"],
                "instrumented_stdout_sha256": b["stdout_sha256"],
                "native_original_counters": a["counters"],
                "native_instrumented_counters": b["counters"],
                "native_counters_unchanged": counters_equal,
                "native_repeat_controls": diagnostic,
                "measured_cache_all_queries": A,
                "measured_empty_bucket_misses": E,
                "occupied_bucket_lookups": L,
                "occupied_bucket_misses": L - H,
                "successful_cache_hits": H,
                "misses_from_components": C - 1,
                "source_derived_query_formula": H + C - 1,
                "hit_rate_eligible": str(Decimal(H) / Decimal(A)) if A else None,
                "count_screen_status": "COUNT_CONCORDANT_UNCERTIFIED",
                "science_gate": (
                    "PASS" if formula_ok and counters_equal else
                    "FORMULA_PASS_SEARCH_DIFFERENT" if formula_ok else
                    "COUNTER_FORMULA_FALSIFIED"
                ),
            }
            report["cases"][case] = data
            dest.write_text(json.dumps(report, indent=2) + "\n")
            if not formula_ok:
                report["status"] = "CACHE_DENOMINATOR_FORMULA_FALSIFIED"
                dest.write_text(json.dumps(report, indent=2) + "\n")
                raise ValueError(f"{case}/{label}: measured query formula failed")
    mismatches = [(case, mode) for case, case_data in report["cases"].items()
                  for mode, row in case_data.items()
                  if not row["native_counters_unchanged"]]
    report["status"] = (
        "GPMC_CACHE_DENOMINATOR_INDEPENDENT_NATIVE_COUNTER_PASS_8_OF_8"
        if not mismatches else
        "CACHE_FORMULA_PASS_BUT_CROSS_BINARY_SEARCH_IDENTITY_BLOCKED"
    )
    report["cross_binary_search_mismatches"] = mismatches
    dest.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"],
        "mismatches": mismatches,
        "summary": {k: {td: {"queries": v["measured_cache_all_queries"],
            "empty_miss": v["measured_empty_bucket_misses"],
            "hit_rate": v["hit_rate_eligible"],
            "same_search": v["native_counters_unchanged"]}
            for td, v in d.items()} for k, d in report["cases"].items()}}))
    if mismatches:
        raise ValueError("Native cache formula validated, but original vs "
                         "counter-only binary search workload differs: "
                         f"{mismatches}; see complete archived diagnostics")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    pre = sub.add_parser("patch")
    pre.add_argument("--scratch", type=Path, required=True)
    pre.add_argument("--provenance", type=Path, required=True)
    run = sub.add_parser("audit")
    for arg in ("original", "instrumented", "cnfs", "archived", "out"):
        run.add_argument("--" + arg, type=Path, required=True)
    args = p.parse_args()
    if args.action == "patch":
        prepare_scratch(args.scratch, args.provenance)
    else:
        science(args.original, args.instrumented, args.cnfs, args.archived, args.out)
