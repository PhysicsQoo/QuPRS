"""QOO-157 P6: source-isolated d4 SAT warm-start native science only.

Two scratch d4 executables differ only in DpllStyleMethod.hpp::run() at the
compute(setOfVar,m_out) call. Cache ON in both. Original weighted CNF, BiPe
and GMP 128-bit precision are held constant. No timing observations.
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

from gpmc_td_ablation import COMPLEX
from gpmc_vs_td_factorial import close_enough
from qoo157_preprocess_compare import D4_RESULT, D4_COUNTS

PIN = "be15f91f3e9769e1f5cb175fa27e3eca3a1ea690"
HEADER = "src/methods/DpllStyleMethod.hpp"
OLD = "    T result = compute(setOfVar, m_out);\n"
NEW = "    T result = compute(setOfVar, m_out, false);\n"
CASES = ("grover4_eq", "qaoa7_neq", "qpeexact8_eq", "qft16_eq")
BIPE = {
    "auto": (),
    "none": ("--preproc.auto-config=false", "--preproc.preproc-method=none"),
}
METRIC = re.compile(r"(?m)^c (Number of (?:recursive call|split formula|decision|positive hit|negative hit)):\s*(\d+)\s*$")
NAMES = {
    "Number of recursive call": "recursive_calls",
    "Number of split formula": "split_components",
    "Number of decision": "decisions",
    "Number of positive hit": "positive_cache_hits",
    "Number of negative hit": "negative_cache_misses",
}


def source_patch(root: Path, evidence: Path):
    if subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip() != PIN:
        raise ValueError("d4 warm-start patch upstream pin mismatch")
    # Precision and BiPe diagnostic temporary source edits are allowed in
    # Main.cpp/Counter.cpp but this solver header must still be original.
    header = root / HEADER
    original = subprocess.check_output(
        ["git", "-C", str(root), "show", f"HEAD:{HEADER}"])
    if header.read_bytes() != original:
        raise ValueError("warm-start header modified before source-pinned patch")
    old = original.decode()
    if old.count(OLD) != 1 or old.count(NEW) != 0:
        raise ValueError("warm-start compute call anchor not exactly once")
    if old.count("T result = compute(setOfVar, out, false);") != 1:
        raise ValueError("count/assumptions warm-start bypass must remain distinct")
    patched = old.replace(OLD, NEW)
    header.write_text(patched)
    evidence.mkdir(parents=True, exist_ok=True)
    report = {
        "source_sha": PIN, "file": HEADER,
        "only_changed_line": {"before": OLD.strip(), "after": NEW.strip()},
        "before_sha256": sha256(original).hexdigest(),
        "after_sha256": sha256(patched.encode()).hexdigest(),
        "warm_start_off_via_original_run_call": True,
        "warm_start_method_itself_unmodified": True,
        "assumption_count_path_unmodified": True,
        "cache_and_bipe_solver_algorithms_unmodified": True,
    }
    (evidence / "warmstart-source-patch.json").write_text(
        json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    return report


def one(binary: Path, cnf: Path, bipe: str, *, timeout=45):
    args = [str(binary), "-i", str(cnf), "--dpll.cache.isActivated=true", *BIPE[bipe]]
    try:
        p = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status": "CENSORED_TIMEOUT", "timeout_seconds": timeout}
    if p.returncode:
        return {"status": "CENSORED_NATIVE_NONZERO_EXIT",
                "exit_code": p.returncode,
                "stdout_tail": p.stdout[-300:],
                "stderr_tail": p.stderr[-300:]}
    counts = D4_RESULT.findall(p.stdout)
    if len(counts) != 1:
        return {"status": "CENSORED_COUNT_NOT_UNIQUE", "matches": len(counts)}
    m = COMPLEX.fullmatch(counts[0].strip())
    if m is None:
        return {"status": "CENSORED_COUNT_MALFORMED"}
    z = tuple(Decimal(x) for x in m.groups())
    if not all(x.is_finite() for x in z):
        return {"status": "CENSORED_NONFINITE"}
    native = {NAMES[k]: int(n) for k,n in METRIC.findall(p.stdout)}
    if len(native) != len(NAMES):
        return {"status": "CENSORED_NATIVE_STAT_MISSING", "present": native,
                "stdout_tail": p.stdout[-700:]}
    stages = {}
    for label, vs, cls, active, protected, weights, projected in D4_COUNTS.findall(p.stdout):
        if label in stages:
            raise ValueError("duplicate BiPe stage")
        stages[label] = {"vars": int(vs), "clauses": int(cls),
                         "active": int(active), "protected": int(protected),
                         "weight_entries": int(weights), "projected": int(projected)}
    if set(stages) != {"before", "after"}:
        raise ValueError("native BiPe before/after stages required")
    if bipe == "none" and any(
        stages["before"][key] != stages["after"][key]
        for key in ("vars", "clauses", "active")
    ):
        raise ValueError("BiPe none mutated source dimensions")
    return {"status":"COUNT_PRESENT", "complex": [str(x) for x in z],
            "native": native, "bipe": stages,
            "raw_count": counts[0].strip(),
            "stdout_sha256": sha256(p.stdout.encode()).hexdigest()}


def science(on: Path, off: Path, cnfs: Path, original: Path,
            patch: Path, output: Path):
    patch_info = json.loads(patch.read_text())
    if patch_info.get("source_sha") != PIN or not patch_info.get(
            "warm_start_off_via_original_run_call"):
        raise ValueError("source patch provenance not certified")
    if on.resolve() == off.resolve():
        raise ValueError("same executable cannot be two warm-start arms")
    originals = json.loads(original.read_text())
    if originals.get("complete") is not True:
        raise ValueError("original source science evidence incomplete")
    record = {
        "status": "INCOMPLETE", "issue": "QOO-157",
        "source_commit": PIN,
        "source_control": patch_info,
        "warm_on_binary_sha256": sha256(on.read_bytes()).hexdigest(),
        "warm_off_binary_sha256": sha256(off.read_bytes()).hexdigest(),
        "original_science_run_id": 41822549728,
        "warm_start_calls": "29 random-assumption SAT warmup rounds of up to 11 literals",
        "gmp_actual_bits": 128, "precision_effective_digits": 38,
        "cache_setting": "--dpll.cache.isActivated=true",
        "performance_measured": False,
        "count_acceptance": "COUNT_CONCORDANT_UNCERTIFIED_1e-12_SCALE",
        "cases": {}, "censored": [], "failures": [],
    }
    if record["warm_on_binary_sha256"] == record["warm_off_binary_sha256"]:
        raise ValueError("two compiled binaries have identical SHA unexpectedly")
    output.parent.mkdir(parents=True, exist_ok=True)
    for case in CASES:
        cnf = cnfs / (case + ".cnf")
        entry = originals["cases"][case]
        digest = sha256(cnf.read_bytes()).hexdigest()
        if digest != entry["same_cnf_sha256"]:
            raise ValueError(f"original CNF SHA changed: {case}")
        anchor = entry["precision_pairs"]["38"]["observations"]["d4-38"]
        if anchor["status"] != "COMPLETED":
            raise ValueError("historical d4 reference incomplete")
        with localcontext() as ctx:
            ctx.prec = 110
            oracle = tuple(
                Decimal(Fraction(anchor[k]).numerator) /
                Decimal(Fraction(anchor[k]).denominator)
                for k in ("real", "imag")
            )
        row = {"source_sha256": digest, "pairs": {}}
        record["cases"][case] = row
        for bipe in BIPE:
            pair = {"variants": {}, "effects": {"status": "INCOMPLETE"}}
            row["pairs"][bipe] = pair
            for state, binary in (("on",on),("off",off)):
                obs = one(binary, cnf, bipe)
                if obs["status"] == "COUNT_PRESENT":
                    ok,delta,limit = close_enough(
                        tuple(Decimal(v) for v in obs["complex"]), oracle)
                    obs.update(status="COUNT_CONCORDANT_UNCERTIFIED" if ok else
                               "CENSORED_NUMERICAL_DISAGREEMENT",
                               deviation=delta, threshold=limit)
                    if not ok:
                        record["failures"].append([case,bipe,state,"WRONG_WMC",delta])
                else:
                    record["censored"].append([case,bipe,state,obs["status"]])
                pair["variants"][state] = obs
                output.write_text(json.dumps(record,indent=2) + "\n")
            before, after = pair["variants"]["on"], pair["variants"]["off"]
            if before["status"] != "COUNT_CONCORDANT_UNCERTIFIED":
                record["failures"].append([case,bipe,"on","BASELINE_NOT_QUALIFIED"])
            if all(v["status"]=="COUNT_CONCORDANT_UNCERTIFIED"
                   for v in (before,after)):
                if before["bipe"] != after["bipe"]:
                    record["failures"].append([case,bipe,"BIPE_STRUCTURAL_MISMATCH"])
                pair["effects"] = {
                    "status": "BOTH_WMC_CONCORDANT",
                    "exact_printed_complex_equal": before["complex"] == after["complex"],
                    "decision_delta_warm_off_minus_on":
                        after["native"]["decisions"]-before["native"]["decisions"],
                    "recursive_calls_delta_warm_off_minus_on":
                        after["native"]["recursive_calls"]-before["native"]["recursive_calls"],
                    "positive_hits_delta_warm_off_minus_on":
                        after["native"]["positive_cache_hits"]-
                        before["native"]["positive_cache_hits"],
                    "native_stats_identical": before["native"] == after["native"],
                }
            else:
                pair["effects"] = {"status": "CENSORED_NO_TIMING_ELIGIBILITY"}
            output.write_text(json.dumps(record,indent=2) + "\n")
    record["qualified_pairs"] = [
        [case,bipe]
        for case,row in record["cases"].items()
        for bipe,pair in row["pairs"].items()
        if pair["effects"]["status"]=="BOTH_WMC_CONCORDANT"
    ]
    record["status"] = (
        "D4_WARMSTART_SCIENCE_FAILED" if record["failures"] else
        "D4_WARMSTART_SCIENCE_CENSORED" if record["censored"] else
        "D4_WARMSTART_SCIENCE_PASS_16_OF_16"
    )
    output.write_text(json.dumps(record,indent=2) + "\n")
    print(json.dumps({
        "status": record["status"], "qualified_pairs": record["qualified_pairs"],
        "failures": record["failures"], "censored": record["censored"],
        "effects": {c:{b:x["effects"] for b,x in v["pairs"].items()}
                   for c,v in record["cases"].items()},
    }), flush=True)
    if record["failures"]:
        raise ValueError("SCIENCE_FAIL: no warm-start timing admission")
    return record


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patch-scratch",type=Path)
    parser.add_argument("--evidence",type=Path)
    for arg in ("on","off","cnfs","original","patch","output"):
        parser.add_argument("--"+arg,type=Path)
    a=parser.parse_args()
    if a.patch_scratch is not None:
        if a.evidence is None:
            parser.error("--evidence required for --patch-scratch")
        source_patch(a.patch_scratch,a.evidence)
    else:
        for arg in ("on","off","cnfs","original","patch","output"):
            if getattr(a,arg) is None:
                parser.error("--"+arg+" required for --science mode")
        science(a.on,a.off,a.cnfs,a.original,a.patch,a.output)
