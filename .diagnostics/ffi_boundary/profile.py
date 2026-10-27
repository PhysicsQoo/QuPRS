#!/usr/bin/env python3
"""One binary, one host: actual FFI/QASM/solver partition under opt-in clocks.

Same SHA, exact QASM, fresh Python process per trial; no performance gate.
For Graphstate16 measure parse and Stage-Ledger materialization overhead.
For VQE4 separate child solver supervision, native Reduction and wrapper time.
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

ROOT = Path("benchmarks/MQTBench").resolve()
OUT = Path("ffi-boundary-results").resolve()
CASES = {
    "graphstate16": ("graphstate_nativegates_ibm_qiskit_opt0_16.qasm", "Naive", False),
    "vqe4": ("vqe_nativegates_ibm_qiskit_opt0_4.qasm", "Proportional", False),
}
MODES = ("control", "ffi", "rules")
WARMUPS = 3
ROUNDS = 36

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def store(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")

def cmd(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=45)
    return {"exit":result.returncode, "stdout":result.stdout[-16000:],
            "stderr":result.stderr[-16000:]}

def source_pair(case):
    filename, strategy, rev = CASES[case]
    pair = (ROOT / filename, ROOT / "h,ry,rz,cx" / filename)
    if not all(path.is_file() for path in pair):
        raise FileNotFoundError(str(pair))
    return pair[::-1] if rev else pair, strategy

def one(case, mode, input_kind):
    pair, strategy = source_pair(case)
    os.environ["QUPRS_STAGE_LEDGER"] = "1"
    for name, on in (("QUPRS_FFI_PHASE_TIMING", mode != "control"),
                     ("QUPRS_OTHER_RULE_TIMING", mode == "rules")):
        if on: os.environ[name] = "1"
        else: os.environ.pop(name, None)
    os.environ.pop("QUPRS_ELIM_TIMING", None)

    with WMC("gpmc") as binary:
        if binary.resolve() != Path(os.environ["QUPRS_GPMC_PATH"]).resolve():
            raise RuntimeError("GPMC executable differs from source-pinned run")
        prep_start = time.perf_counter_ns()
        if input_kind == "inline":
            inputs = tuple(path.read_text() for path in pair)
        else:
            inputs = tuple(str(path) for path in pair)
        prep_ns = time.perf_counter_ns() - prep_start

        enter = time.perf_counter_ns()
        result = _pathsum_rust.check_equivalence(
            inputs[0], inputs[1], method="hybrid",
            strategy=strategy, tool_name="gpmc", timeout=35
        )
        wrapper_ns = time.perf_counter_ns() - enter

    ledger = result.get("stage_ledger")
    flags = []
    if result["status"] not in ("Equivalent", "Equivalent (Up to Global Phase)"):
        flags.append("status not equivalent")
    if not isinstance(ledger, dict):
        flags.append("Stage Ledger missing")
    else:
        if ledger["has_stage_overlap"] or abs(ledger["closure_error_seconds"]) > 1e-6:
            flags.append("native stage closure/overlap")
        if abs(sum(ledger["exclusive_seconds"].values())
               - ledger["total_native_wall_seconds"]) > 1e-6:
            flags.append("native exclusive partition")
    phases = result.get("ffi_phase_timings")
    if (phases is not None) != (mode != "control"):
        flags.append("FFI phase opt-in mismatch")
    if phases:
        if phases.get("schema") != "quprs-rust-ffi-phase-v1":
            flags.append("FFI phase schema mismatch")
        if phases["python_dict_build_ns"] < phases["stage_ledger_materialize_ns"]:
            flags.append("FFI stage materialization not contained")
        if phases["ffi_elapsed_excluding_phase_metadata_ns"] < (
           phases["qasm_extract_ns"]+phases["native_bridge_ns"]+
           phases["python_dict_build_ns"]):
            flags.append("FFI phase intervals not contained")
        if wrapper_ns + 150_000 < phases["ffi_elapsed_excluding_phase_metadata_ns"]:
            flags.append("Rust internal FFI time exceeds Python external wrapper")
    if (ledger is not None and "other_rule_timings" in ledger) != (mode == "rules"):
        flags.append("rule clock opt-in mismatch")
    return {
        "schema":"quprs-ffi-boundary-observation-v1",
        "case":case,"mode":mode,"input_kind":input_kind,
        "status":result["status"],"stats":result["stats"],
        "final_ps_sha256":hashlib.sha256(result["final_ps"].encode()).hexdigest(),
        "qasm_file_sha256":[sha(path) for path in pair],
        "extension_path":str(Path(_pathsum_rust.__file__).resolve()),
        "python_input_prep_ns":prep_ns,
        "python_ffi_wrapper_ns":wrapper_ns,
        "native_engine_seconds":result["verification_time_sec"],
        "native_pathsum_seconds":result["pathsum_time_sec"],
        "stage_ledger":ledger,
        "ffi_phase_timings":phases,
        "flags":flags
    }

def median(v):
    return statistics.median(v)

def quantile(v, q):
    data = sorted(v)
    index = (len(data)-1)*q
    lower = int(index)
    return data[lower]*(1-index%1)+data[min(len(data)-1,lower+1)]*(index%1)

def run():
    OUT.mkdir(parents=True, exist_ok=True)
    affinity = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0,{affinity[0]})
    os.environ.update(PYTHONHASHSEED="0",OMP_NUM_THREADS="1",
                      OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1")
    os.environ.pop("QUPRS_FFI_PHASE_TIMING",None)
    os.environ.pop("QUPRS_OTHER_RULE_TIMING",None)
    with WMC("gpmc") as binary:
        binary=binary.resolve()
        os.environ["QUPRS_GPMC_PATH"]=str(binary)
        manifest={
            "schema":"quprs-ffi-phase-and-vqe-solver-v1",
            "source_head":cmd(["git","rev-parse","HEAD"]),
            "gpmc_gitlink":cmd(["git","rev-parse","HEAD:GPMC"]),
            "gpmc_sha256":sha(binary),"python":sys.version,
            "packages":cmd([sys.executable,"-m","pip","freeze"]),
            "rustc":cmd(["rustc","--version"]),
            "cpu":cmd(["lscpu"]), "host":platform.platform(),
            "cpu_affinity_original":affinity,"cpu_affinity_used":affinity[0],
            "runner_sha256":sha(Path(__file__).resolve()),
            "inputs":{k:[sha(p) for p in source_pair(k)[0]] for k in CASES},
            "design":{"rounds":ROUNDS,"warmups":WARMUPS,"seed":112070,
                "graphstate16_input_kinds":("path","inline"),
                "vqe4_input_kinds":("path",),"modes":MODES,
                "timeout_native_sec":35,"timeout_process_sec":60},
        }
        store(OUT/"environment.json",manifest)
        records,errors=[],[]
        with (OUT/"samples.jsonl").open("w",buffering=1) as fd:
            for case in CASES:
                for input_kind in (("path","inline") if case=="graphstate16" else ("path",)):
                    for r in range(-WARMUPS,ROUNDS):
                        modes=list(MODES)
                        random.Random(112070+100000*list(CASES).index(case)
                                      +10000*int(input_kind=="inline")+r).shuffle(modes)
                        triplet={}
                        for mode in modes:
                            file=OUT/"individual"/f"{case}_{input_kind}_{r:03d}_{mode}.json"
                            argv=[sys.executable,"-u",str(Path(__file__).resolve()),
                                  "--one","--case",case,"--mode",mode,"--kind",input_kind]
                            row={"case":case,"kind":input_kind,"round":r,
                                 "mode":mode,"warmup":r<0,"file":str(file.relative_to(OUT))}
                            try:
                                p=subprocess.run(argv,capture_output=True,text=True,
                                                 timeout=60,env=os.environ.copy())
                                row["exit"]=p.returncode
                                row["stderr"]=p.stderr[-5000:]
                                if p.returncode==0:
                                    datum=json.loads(p.stdout)
                                    row["data"]=datum
                                    triplet[mode]=datum
                                    store(file,datum)
                                else:
                                    errors.append({"case":case,"kind":input_kind,
                                                   "round":r,"mode":mode,
                                                   "error":row["stderr"]})
                            except (ValueError,subprocess.TimeoutExpired) as exc:
                                errors.append({"case":case,"kind":input_kind,
                                               "round":r,"mode":mode,"error":repr(exc)})
                            records.append(row)
                            fd.write(json.dumps(row,sort_keys=True)+"\n")
                            print("FFI_SAMPLE",case,input_kind,r,mode,
                                  row.get("exit"),flush=True)
                            if errors: break
                        if not errors and len(triplet)==3:
                            a=triplet["control"]
                            for mode in MODES[1:]:
                                b=triplet[mode]
                                if (any(a[k]!=b[k] for k in
                                        ("status","stats","final_ps_sha256",
                                         "qasm_file_sha256","extension_path"))
                                    or a["stage_ledger"]["structural_elim_attempts"]
                                        !=b["stage_ledger"]["structural_elim_attempts"]
                                    or b["flags"] or a["flags"]):
                                    errors.append({"case":case,"kind":input_kind,
                                                   "round":r,"mode":mode,
                                                   "error":"SEMANTIC_OR_INSTRUMENT_IDENTITY_FAILED"})
                                    break
                        if errors: break
                    if errors: break
                if errors: break

    summaries={}
    for case in CASES:
        for kind in (("path","inline") if case=="graphstate16" else ("path",)):
            subset=[x for x in records if x["case"]==case and x["kind"]==kind
                    and not x["warmup"] and "data" in x]
            groups={m:{x["round"]:x["data"] for x in subset if x["mode"]==m}
                    for m in MODES}
            key=f"{case}/{kind}"
            report={"valid_per_mode":{m:len(groups[m]) for m in MODES}}
            if all(set(groups[m])==set(range(ROUNDS)) for m in MODES) and not errors:
                per={m:[groups[m][i] for i in range(ROUNDS)] for m in MODES}
                for m,values in per.items():
                    metrics={
                      "python_qasm_prep_ms":[x["python_input_prep_ns"]/1e6 for x in values],
                      "python_ffi_wrapper_ms":[x["python_ffi_wrapper_ns"]/1e6 for x in values],
                      "rust_native_engine_ms":[x["native_engine_seconds"]*1000 for x in values],
                      "rust_reduction_ms":[x["stage_ledger"]["exclusive_seconds"]["reduction"]*1000 for x in values],
                      "rust_solver_supervision_ms":[x["stage_ledger"]["exclusive_seconds"]["solver_supervision"]*1000 for x in values],
                      "native_to_python_gap_ms":[(x["python_ffi_wrapper_ns"]/1e6
                                      -x["native_engine_seconds"]*1000) for x in values],
                    }
                    if m!="control":
                        for name,field in (
                            ("ffi_qasm_parse_ms","qasm_extract_ns"),
                            ("ffi_native_bridge_ms","native_bridge_ns"),
                            ("ffi_python_dict_ms","python_dict_build_ns"),
                            ("ffi_stage_materialize_ms","stage_ledger_materialize_ns")):
                            metrics[name]=[x["ffi_phase_timings"][field]/1e6 for x in values]
                    report[m]={key:{"median":median(v),"p10":quantile(v,.1),"p90":quantile(v,.9)}
                               for key,v in metrics.items()}
                    report[m]["solver_spawns"]=[x["stage_ledger"]["solver_child_spawns"] for x in values]
                report["paired_ratios"]={}
                for n,d in (("ffi/control",("ffi","control")),
                            ("rules/ffi",("rules","ffi")),
                            ("rules/control",("rules","control"))):
                    vals=[groups[d[0]][i]["python_ffi_wrapper_ns"]/
                          groups[d[1]][i]["python_ffi_wrapper_ns"] for i in range(ROUNDS)]
                    report["paired_ratios"][n]={"median":median(vals),
                      "range_p10_p90":[quantile(vals,.1),quantile(vals,.9)]}
                if case=="vqe4":
                    report["solver_to_native_time_fraction"]=median([
                        x["stage_ledger"]["exclusive_seconds"]["solver_supervision"]/
                        max(1e-10,x["native_engine_seconds"]) for x in per["ffi"]])
            summaries[key]=report
    expected=ROUNDS*len(MODES)*3
    status="PASS_DATA_COLLECTION" if not errors and all(
        all(n==ROUNDS for n in x["valid_per_mode"].values()) for x in summaries.values()
    ) and len([x for x in records if not x["warmup"]])==expected else "INCOMPLETE"
    result={"status":status,"schema":"quprs-ffi-phase-and-vqe-solver-v1",
            "expected_measured":expected,"observed_measured":len([r for r in records if not r["warmup"]]),
            "errors":errors,"case_summaries":summaries,
            "limits":[
                "FFI clocks are opt-in and alter the measurement; control/ffi contrast estimates observer perturbation.",
                "Rust QASM extract includes Rust file read/parse; Python inline preparation is measured separately.",
                "Python FFI wrapper gap includes PyO3 dispatch and metadata; materialization is a subset, not independently additive.",
                "Rust native engine time contains solver supervision; never add it to solver/reduction children.",
                "VQE solver timing is host/process sensitive; random triplet order and p10/p90 diagnose not eliminate confounding.",
                "Results conditional on one runner and fixed circuit pairs; no production scheduler inference.",
            ]}
    store(OUT/"summary.json",result)
    lines=["# FFI phase and solver supervision pilot","",
           "Result: "+status, f"Measured records {result['observed_measured']}/{expected}.", "",
           "| Case/input | Valid / mode | FFI/control ratio | Rules/FFI ratio | FFI stage materialization (ms) | Solver supervision (ms) |",
           "|---|---:|---:|---:|---:|---:|"]
    for key,r in summaries.items():
        if "paired_ratios" not in r:
            lines.append(f"| {key} | INCOMPLETE | NA | NA | NA | NA |")
        else:
            lines.append(f"| {key} | {r['valid_per_mode']['ffi']} | "
                         f"{r['paired_ratios']['ffi/control']['median']:.3f} | "
                         f"{r['paired_ratios']['rules/ffi']['median']:.3f} | "
                         f"{r['rules']['ffi_stage_materialize_ms']['median']:.4f} | "
                         f"{r['ffi']['rust_solver_supervision_ms']['median']:.4f} |")
    lines.extend(["","Phase interval boundaries and full per-mode distribution appear in summary.json.",
                  "Do not interpret FFI timestamp gaps or solver fluctuations as causal speedup."])
    (OUT/"summary.md").write_text("\n".join(lines)+"\n")
    print(json.dumps({"status":status,"measured":result["observed_measured"],
                      "cases":list(summaries)},sort_keys=True),flush=True)
    return 0 if status=="PASS_DATA_COLLECTION" else 2

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--one",action="store_true")
    p.add_argument("--case",choices=CASES)
    p.add_argument("--mode",choices=MODES)
    p.add_argument("--kind",choices=("path","inline"),default="path")
    a=p.parse_args()
    if a.one:
        rec=one(a.case,a.mode,a.kind)
        print(json.dumps(rec,sort_keys=True))
        return 0 if not rec["flags"] else 2
    return run()

if __name__=="__main__":
    sys.exit(main())
