#!/usr/bin/env python3
"""Source-pinned six-family native discovery/HH/Omega/Elim cost attribution.

A single machine + identical native wheel + single packaged GPMC executable.
Three opt-in modes separate observer overhead from nested rule costs.
Research-only: neither a performance regression gate nor a scheduler model.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time

from QuPRS import _pathsum_rust
from QuPRS.utils import WMC

CASES = {
    "qaoa7": ("qaoa_nativegates_ibm_qiskit_opt0_7.qasm", "Proportional", False),
    "qft16": ("qft_nativegates_ibm_qiskit_opt0_16.qasm", "Proportional", True),
    "grover4": ("grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm", "Proportional", True),
    "vqe4": ("vqe_nativegates_ibm_qiskit_opt0_4.qasm", "Proportional", False),
    "graphstate16": ("graphstate_nativegates_ibm_qiskit_opt0_16.qasm", "Naive", False),
    "ghz32": ("ghz_nativegates_ibm_qiskit_opt0_32.qasm", "Straightforward", True),
}
MODES = ("base", "other", "joint")
RULES = ("candidate_discovery", "hh", "omega", "elim")
WARMUPS = 2
ROUNDS = 10
OUT = Path("native-rule-attribution-results").resolve()
BENCH = Path("benchmarks/MQTBench").resolve()
ROOT_TOLERANCE_SEC = 1e-5


def hash_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, sort_keys=True, indent=2) + "\n")


def command(args):
    try:
        proc = subprocess.run(args, text=True, capture_output=True, timeout=40)
        return {"exit": proc.returncode, "stdout": proc.stdout[-12000:],
                "stderr": proc.stderr[-12000:]}
    except Exception as exc:
        return {"exception": repr(exc)}


def inputs(case):
    filename, strategy, reverse = CASES[case]
    pair = (BENCH / filename, BENCH / "h,ry,rz,cx" / filename)
    if not all(p.is_file() for p in pair):
        raise FileNotFoundError(str(pair))
    return pair[::-1] if reverse else pair, strategy


def classify_and_profile(case, mode):
    pair, strategy = inputs(case)
    os.environ["QUPRS_STAGE_LEDGER"] = "1"
    if mode in ("other", "joint"):
        os.environ["QUPRS_OTHER_RULE_TIMING"] = "1"
    else:
        os.environ.pop("QUPRS_OTHER_RULE_TIMING", None)
    if mode == "joint":
        os.environ["QUPRS_ELIM_TIMING"] = "1"
    else:
        os.environ.pop("QUPRS_ELIM_TIMING", None)

    with WMC("gpmc") as binary:
        if binary.resolve() != Path(os.environ["QUPRS_GPMC_PATH"]).resolve():
            raise RuntimeError("Packaged GPMC executable changed across modes")
        t0 = time.perf_counter_ns()
        native = _pathsum_rust.check_equivalence(
            str(pair[0]), str(pair[1]), method="hybrid",
            strategy=strategy, tool_name="gpmc", timeout=60)
        ffi_ns = time.perf_counter_ns() - t0

    ledger = native.get("stage_ledger")
    failures = []
    if native["status"] not in ("Equivalent", "Equivalent (Up to Global Phase)"):
        failures.append("incorrect/undecided native verification")
    if not isinstance(ledger, dict):
        failures.append("missing Stage Ledger")
    else:
        if ledger["schema"] != "quprs-rust-native-exclusive-v0":
            failures.append("unexpected exclusive stage schema")
        if ledger["has_stage_overlap"] or abs(ledger["closure_error_seconds"]) > 1e-6:
            failures.append("root stage overlap/closure error")
        if abs(sum(ledger["exclusive_seconds"].values()) -
               ledger["total_native_wall_seconds"]) > 1e-6:
            failures.append("exclusive root partition broken")

        candidates = ledger["structural_elim_attempts"]
        if not isinstance(candidates, list):
            failures.append("missing structural counters")
            candidates = []
        for f in candidates:
            if (set(f) != {"k_r", "l_r", "v_r", "d_r", "w_redundant_estimated"}
                or f["w_redundant_estimated"] != max(f["k_r"] - 1, 0)*f["l_r"]):
                failures.append("invalid K/L/V/D/W")
                break

        other = ledger.get("other_rule_timings")
        elim = ledger.get("elim_attempt_timings")
        if (other is not None) != (mode != "base"):
            failures.append("other_rule_timings opt-in violated")
        if (elim is not None) != (mode == "joint"):
            failures.append("elim_attempt_timings opt-in violated")
        if other is not None:
            for t in other:
                if (set(t) != {"rule","elapsed_ns","success","candidate_count",
                               "within_reduction"}
                    or t["rule"] not in RULES[:3]
                    or type(t["elapsed_ns"]) is not int or t["elapsed_ns"] < 0
                    or type(t["success"]) is not bool
                    or type(t["within_reduction"]) is not bool
                    or type(t["candidate_count"]) is not int
                    or t["candidate_count"] < 0):
                    failures.append("invalid other-rule timing record")
                    break
        if elim is not None:
            if len(elim) != len(candidates):
                failures.append("Elim index/count mismatch")
            for i, t in enumerate(elim):
                if (set(t) != {"structural_index","elapsed_ns","success"}
                    or t["structural_index"] != i
                    or type(t["elapsed_ns"]) is not int or t["elapsed_ns"] < 0
                    or type(t["success"]) is not bool):
                    failures.append("invalid Elim elapsed record")
                    break

        if mode == "joint" and other is not None and elim is not None:
            total_child_seconds = (
                sum(t["elapsed_ns"] for t in other if t["within_reduction"])
                + sum(t["elapsed_ns"] for t in elim)
            ) / 1e9
            if total_child_seconds > (ledger["exclusive_seconds"]["reduction"]
                                      + ROOT_TOLERANCE_SEC):
                failures.append("nested rule child time exceeds Root Reduction")

    return {
        "schema": "quprs-native-other-rules-attribution-observation-v1",
        "case": case, "mode": mode, "strategy": strategy,
        "status": native["status"], "stats": native["stats"],
        "input_sha256": [hash_file(p) for p in pair],
        "final_ps_sha256": hashlib.sha256(native["final_ps"].encode()).hexdigest(),
        "extension_path": str(Path(_pathsum_rust.__file__).resolve()),
        "ffi_wrapper_ns": ffi_ns,
        "native_verification_seconds": native["verification_time_sec"],
        "pathsum_strategy_seconds": native["pathsum_time_sec"],
        "stage_ledger": ledger, "errors": failures,
    }


def percentiles(values, draws=2000):
    rng = random.Random(112062)
    boot = sorted(statistics.median([rng.choice(values) for _ in values])
                  for _ in range(draws))
    return [boot[int(draws*.025)], boot[int(draws*.975)-1]]


def rule_attribution(ledger):
    root = ledger["exclusive_seconds"]["reduction"]
    buckets = {r: {"count":0, "successes":0, "inside_root":0,
                   "within_root_ns":0, "outside_root_ns":0} for r in RULES}
    for t in ledger["other_rule_timings"]:
        z = buckets[t["rule"]]
        z["count"] += 1
        z["successes"] += int(t["success"])
        z["inside_root"] += int(t["within_reduction"])
        if t["within_reduction"]:
            z["within_root_ns"] += t["elapsed_ns"]
        else:
            z["outside_root_ns"] += t["elapsed_ns"]
    for t in ledger["elim_attempt_timings"]:
        z = buckets["elim"]
        z["count"] += 1
        z["successes"] += int(t["success"])
        z["inside_root"] += 1  # Native verification calls Elim only via full_reduce.
        z["within_root_ns"] += t["elapsed_ns"]
    nested_ns = sum(x["within_root_ns"] for x in buckets.values())
    residual_s = root - nested_ns / 1e9
    return {
        "root_reduction_seconds": root,
        "rule_counts_and_duration": buckets,
        "nested_sum_seconds": nested_ns / 1e9,
        "root_unattributed_seconds": residual_s,
        "root_unattributed_fraction": residual_s/root if root else None,
        "root_fraction_by_rule": {k:v["within_root_ns"]/1e9/root if root else None
                                  for k,v in buckets.items()},
        "caution": "per-rule elapsed time is nested in (not additional to) root reduction",
    }


def experiment():
    OUT.mkdir(parents=True, exist_ok=True)
    cpu_choices = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {cpu_choices[0]})
    os.environ.update(
        PYTHONHASHSEED="0", OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    os.environ.pop("QUPRS_OTHER_RULE_TIMING", None)
    os.environ.pop("QUPRS_ELIM_TIMING", None)
    with WMC("gpmc") as binary:
        binary = binary.resolve()
        if not binary.is_file():
            raise FileNotFoundError("GPMC binary unavailable")
        os.environ["QUPRS_GPMC_PATH"] = str(binary)
        manifest = {
            "schema": "quprs-native-other-rules-attribution-v1",
            "source_head": command(["git","rev-parse","HEAD"]),
            "solver_gitlink": command(["git","rev-parse","HEAD:GPMC"]),
            "solver_sha256": hash_file(binary),
            "extension_path": str(Path(_pathsum_rust.__file__).resolve()),
            "python_version": sys.version,
            "python_packages": command([sys.executable,"-m","pip","freeze"]),
            "rust": command(["rustc","--version"]),
            "cpuinfo": command(["lscpu"]), "platform": platform.platform(),
            "cpu_affinity_before": cpu_choices,
            "cpu_affinity_pinned": cpu_choices[0],
            "pilot_source_sha256": hash_file(__file__),
            "inputs_sha256": {case:[hash_file(p) for p in inputs(case)[0]]
                              for case in CASES},
            "experimental_design": {
                "cases": list(CASES), "modes": MODES, "warmups": WARMUPS,
                "rounds": ROUNDS, "seed":112062, "timeout_native_seconds":60,
                "hard_timeout_child_seconds":100, "method":"hybrid", "solver":"gpmc",
            }
        }
        write_json(OUT/"environment.json", manifest)
        entries, errors = [], []
        with (OUT/"samples.jsonl").open("w", buffering=1) as fh:
            for case in CASES:
                for trial in range(-WARMUPS, ROUNDS):
                    order = list(MODES)
                    random.Random(112062 + 1000*list(CASES).index(case)
                                  + trial).shuffle(order)
                    round_samples = {}
                    for mode in order:
                        output = OUT/"individual"/f"{case}_{trial:03d}_{mode}.json"
                        child = [sys.executable,"-u",str(Path(__file__).resolve()),
                                 "--one","--case",case,"--mode",mode]
                        row = {"case":case,"round":trial,"mode":mode,
                               "warmup":trial<0,"raw_path":str(output.relative_to(OUT))}
                        try:
                            result = subprocess.run(child, capture_output=True,
                                                    text=True, timeout=100,
                                                    env=os.environ.copy())
                            row["returncode"] = result.returncode
                            row["stderr"] = result.stderr[-5000:]
                            if result.returncode == 0:
                                sample = json.loads(result.stdout)
                                write_json(output, sample)
                                row["data"] = sample
                                round_samples[mode] = sample
                            else:
                                row["stdout"] = result.stdout[-5000:]
                                errors.append({"case":case,"round":trial,"mode":mode,
                                               "error":"native subprocess failed",
                                               "stderr":row["stderr"]})
                        except (subprocess.TimeoutExpired,ValueError) as exc:
                            errors.append({"case":case,"round":trial,"mode":mode,
                                           "error":repr(exc)})
                        entries.append(row)
                        fh.write(json.dumps(row,sort_keys=True)+"\n")
                        print("RULE_SAMPLE",case,trial,mode,
                              row.get("returncode"),flush=True)
                        if errors:
                            break
                    if not errors:
                        if len(round_samples) != len(MODES):
                            errors.append({"case":case,"round":trial,
                                           "error":"incomplete interleaved triplet"})
                        else:
                            first = round_samples["base"]
                            for mode in MODES[1:]:
                                observed = round_samples[mode]
                                if (any(first[k]!=observed[k] for k in
                                        ("status","stats","input_sha256","final_ps_sha256"))
                                    or first["stage_ledger"]["structural_elim_attempts"]
                                       != observed["stage_ledger"]["structural_elim_attempts"]
                                    or first["errors"] or observed["errors"]
                                    or first["extension_path"] != observed["extension_path"]):
                                    errors.append({"case":case,"round":trial,
                                                   "error":"semantic/schema/binary identity mismatch"})
                                    break
                            if not errors:
                                o=round_samples["other"]["stage_ledger"]["other_rule_timings"]
                                j=round_samples["joint"]["stage_ledger"]["other_rule_timings"]
                                def strip_time(t):
                                    return {key:value for key,value in t.items()
                                            if key!="elapsed_ns"}
                                if [strip_time(x) for x in o]!=[strip_time(x) for x in j]:
                                    errors.append({"case":case,"round":trial,
                                                   "error":"other rule sample order/outcome mismatch"})
                    if errors:
                        break
                if errors:
                    break

    summary = {"schema":"quprs-native-other-rules-attribution-v1",
               "status":"INCOMPLETE","errors":errors,"families":{}}
    for case in CASES:
        folds={trial:{x["mode"]:x["data"] for x in entries if
                      x["case"]==case and x["round"]==trial and "data" in x}
               for trial in range(ROUNDS)}
        valid=[x for x in folds.values() if set(x)==set(MODES)]
        family={"valid_matched_triplets":len(valid)}
        if len(valid)==ROUNDS and not errors:
            ratios={
                "other/base": [v["other"]["ffi_wrapper_ns"] / v["base"]["ffi_wrapper_ns"]
                               for v in valid],
                "joint/other":[v["joint"]["ffi_wrapper_ns"] / v["other"]["ffi_wrapper_ns"]
                               for v in valid],
                "joint/base":[v["joint"]["ffi_wrapper_ns"] / v["base"]["ffi_wrapper_ns"]
                              for v in valid],
            }
            family["paired_ffi_ratios"]={
                k:{"median":statistics.median(values),
                   "descriptive_bootstrap_95pct":percentiles(values)}
                for k,values in ratios.items()
            }
            attributed=[rule_attribution(v["joint"]["stage_ledger"]) for v in valid]
            family["joint_rule_timing"]={
                "median_root_reduction_seconds":statistics.median(
                    z["root_reduction_seconds"] for z in attributed),
                "median_root_unattributed_fraction":statistics.median(
                    z["root_unattributed_fraction"] for z in attributed
                    if z["root_unattributed_fraction"] is not None),
                "rule_count_success_from_first_run":
                    {k:{"calls":v["count"],"successes":v["successes"],
                        "within_root":v["inside_root"]}
                     for k,v in attributed[0]["rule_counts_and_duration"].items()},
                "median_fraction_root_by_rule":
                    {k:statistics.median(z["root_fraction_by_rule"][k]
                                         for z in attributed
                                         if z["root_fraction_by_rule"][k] is not None)
                     for k in RULES},
                "individual_runs":attributed,
            }
        summary["families"][case]=family
    if not errors and all(v["valid_matched_triplets"]==ROUNDS
                          for v in summary["families"].values()):
        summary["status"]="PASS_DATA_COLLECTION"
    summary["limitations"]=[
        "Only six fixed circuit families, not prospective independent cost-model validation.",
        "Modes share a single native wheel and GPMC executable on one host; repeated trials are not new circuit designs.",
        "Candidate discovery 'success' means nonempty candidates, not a reduction rule success.",
        "Timers measure perturbed rule bodies with Instant and RAII overhead.",
        "Child rule spans are nested in root Reduction, not additive to it.",
        "Nested Elim time is assumed within root only for this native verification call path.",
        "Residual root time includes loop scheduling/dispatch and clock overhead; it is not a causally identified component.",
        "No claims of automatic scheduler speedup, performance neutrality, or model generalization.",
    ]
    write_json(OUT/"summary.json",summary)
    md=["# Same-host real-circuit rule-level attribution","",
        f"**Collection result:** {summary['status']}","",
        "| Circuit | Valid triplets | Other/base FFI ratio | Joint/other FFI ratio | Root residual fraction |",
        "|---|---:|---:|---:|---:|"]
    for case,f in summary["families"].items():
        r=f.get("paired_ffi_ratios",{})
        ratio=lambda k:f"{r[k]['median']:.4f}" if k in r else "NA"
        resid=f.get("joint_rule_timing",{}).get("median_root_unattributed_fraction")
        md.append(f"| {case} | {f['valid_matched_triplets']} | {ratio('other/base')} | "
                  f"{ratio('joint/other')} | {resid:.3%} |"
                  if resid is not None else
                  f"| {case} | {f['valid_matched_triplets']} | NA | NA | NA |")
    md += ["","Full per-rule counts, nested shares and paired bootstrap intervals are in summary.json.",
            "Measurements are descriptive/perturbed. No speedup or causal scheduler conclusions."]
    (OUT/"summary.md").write_text("\n".join(md)+"\n")
    print(json.dumps({"status":summary["status"],
                      "valid":{k:v["valid_matched_triplets"]
                               for k,v in summary["families"].items()}},
                     sort_keys=True),flush=True)
    return 0 if summary["status"]=="PASS_DATA_COLLECTION" else 2


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--one",action="store_true")
    parser.add_argument("--case",choices=CASES)
    parser.add_argument("--mode",choices=MODES)
    args=parser.parse_args()
    if args.one:
        data=classify_and_profile(args.case,args.mode)
        print(json.dumps(data,sort_keys=True))
        return 0 if not data["errors"] else 2
    return experiment()


if __name__=="__main__":
    sys.exit(main())
