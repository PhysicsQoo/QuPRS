#!/usr/bin/env python3
"""MQTBench v2 opt0 37-case EQ/NEQ acceptance (v0.14.0 Python/Rust GPMC).

Science only. Each testcase compares canonical MQTBench source QASM2 with
its original Level0 target (EQ) and with the independently seeded
Random_Rotation mutation (NEQ). All 37 cases, Hybrid and WMC-only, both
modern QuPRS backends; 296 attempted invocations, timeout is censored.
Never uses legacy Level3 QASM or modifies solver/production verifiers.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import traceback
import warnings
from importlib.metadata import PackageNotFoundError, version as pkg_version

ROOT = Path(__file__).resolve().parents[1]
MQT = ROOT / "benchmarks/MQTBench"
CORPUS = MQT / "qiskit-2.6.1-opt0"
POSITIVE = CORPUS / "h,ry,rz,cx"
NEGATIVE = CORPUS / "Random_Rotation"
P_MANIFEST = CORPUS / "manifest.json"
N_MANIFEST = CORPUS / "random-rotation-manifest.json"
REGISTER = CORPUS / "source-register.json"

SCHEMA = "quprs-mqtbench-qiskit261-opt0-37case-1e8-gpmc-acceptance-v1"
MARKER = "QUPRS_MQT_1E8_EVIDENCE "
DISTANCE = 1e-8
RR = 1e-10
PHASE = 1e-8
GPMC_DIGITS = 30
SOLVER = "gpmc"
PROFILES = ("python", "rust")
METHODS = ("hybrid", "wmc_only")
VARIANTS = ("positive", "negative")
EXPECTED_TOTAL = 37 * 2 * len(PROFILES) * len(METHODS)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name+".partial")
    partial.write_text(content, encoding="utf8")
    partial.replace(path)


def encoded_json(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def binary(label: str | None):
    if label in ("equivalent", "equivalent*"):
        return "EQ"
    if label == "not_equivalent":
        return "NEQ"
    return None


def ledger() -> tuple[list[dict], dict]:
    pos = json.loads(P_MANIFEST.read_text(encoding="utf8"))
    neg = json.loads(N_MANIFEST.read_text(encoding="utf8"))
    registry = json.loads(REGISTER.read_text(encoding="utf8"))
    if pos.get("schema") != "quprs-mqtbench-qiskit261-level0-complete-v1":
        raise ValueError("Unexpected QASM Level0 positive corpus")
    if neg.get("schema") != "quprs-mqtbench-random-rotation-qiskit261-opt0-v1":
        raise ValueError("Unexpected QASM Level0 negative corpus")
    if registry.get("schema") != "quprs-mqtbench-transpiler-source-register-v1":
        raise ValueError("Unexpected historical source registry")
    if pos.get("qiskit_version") != "2.6.1" or neg.get("qiskit_version") != "2.6.1":
        raise ValueError("Compiler mismatch")
    if pos.get("source_qasm_count") != 37 or pos.get("generated_qasm_count") != 37:
        raise ValueError("Positive corpus must have 37 complete inputs")
    if neg.get("source_count") != 37 or neg.get("target_count") != 37:
        raise ValueError("Negative corpus must have 37 complete inputs")
    if pos.get("source_register_sha256") != digest(REGISTER):
        raise ValueError("Changed original input registry")
    if neg.get("baseline_manifest_sha256") != digest(P_MANIFEST):
        raise ValueError("Negative corpus generated from a different positive base")
    if registry.get("historical_transpiled_count") != 45:
        raise ValueError("Historical source registry unexpected")
    pos_map = {row["file"]: row for row in pos["files"]}
    neg_map = {row["file"]: row for row in neg["cases"]}
    sources = {row["path"]: row for row in registry["source_qasms"]}
    if len(pos_map)!=37 or len(neg_map)!=37 or len(sources)!=37:
        raise ValueError("Duplicate names in corpus")
    if set(pos_map)!=set(neg_map) or set(pos_map)!=set(sources):
        raise ValueError("EQ/NEQ pairs or original sources missing")
    if {p.name for p in POSITIVE.glob("*.qasm")} != set(pos_map):
        raise ValueError("Positive directory contents changed")
    if {p.name for p in NEGATIVE.glob("*.qasm")} != set(pos_map):
        raise ValueError("Negative directory contents changed")
    if {p.name for p in MQT.glob("*.qasm")} != set(pos_map):
        raise ValueError("Original directory contents changed")
    rows = []
    for name in sorted(pos_map):
        a, b, c = sources[name], pos_map[name], neg_map[name]
        raw = MQT / name
        eq = POSITIVE / name
        neq = NEGATIVE / name
        if raw.name!=name or eq.name!=name or neq.name!=name:
            raise ValueError("Non-flat QASM name")
        oldbytes=raw.read_bytes()
        oldsha=hashlib.sha1(b"blob "+str(len(oldbytes)).encode()+b"\x00"+oldbytes).hexdigest()
        if oldsha != a["git_blob_sha1"]:
            raise ValueError("Modified historical original QASM")
        if digest(eq) != b["generated_sha256"]:
            raise ValueError("Modified generated Level0 EQ QASM")
        if digest(neq) != c["output_sha256"]:
            raise ValueError("Modified generated Level0 NEQ QASM")
        if c["baseline_qasm_sha256"] != b["generated_sha256"]:
            raise ValueError("NEQ baseline SHA disagrees with EQ")
        if c["expected_binary"]!="NEQ":
            raise ValueError("NEQ case has no expected binary label")
        rows.append({
            "file":name,
            "source_relative":str(raw.relative_to(ROOT)),
            "original_git_blob_sha1":oldsha,
            "original_sha256":digest(raw),
            "positive_relative":str(eq.relative_to(ROOT)),
            "positive_sha256":digest(eq),
            "negative_relative":str(neq.relative_to(ROOT)),
            "negative_sha256":digest(neq),
            "injected_gates":c["injected_instruction_count"],
            "seed":c["seed"],
            "negative_float64_operator_witness":c["science_diagnostic"],
        })
    return rows, {
        "positive_manifest_sha256":digest(P_MANIFEST),
        "negative_manifest_sha256":digest(N_MANIFEST),
        "source_registry_sha256":digest(REGISTER),
        "input_case_count":len(rows),
    }


def case_for(filename):
    cases, sources = ledger()
    match=next((row for row in cases if row["file"]==filename),None)
    if match is None:
        raise ValueError("Requested filename not in frozen 37-source registry")
    return match, sources


def normalize_original(case, output: Path):
    from qiskit import qasm2, QuantumCircuit
    src = ROOT / case["source_relative"]
    if digest(src)!=case["original_sha256"]:
        raise ValueError("Original changed")
    circuit=qasm2.loads(src.read_text(encoding="utf8"))
    clean=circuit.remove_final_measurements(inplace=False)
    invalid={"measure","reset","if_else","while_loop","switch_case","initialize"}
    if any(inst.operation.name in invalid for inst in clean.data):
        raise ValueError("Nonunitary instruction remains in original")
    # Barriers are no-op metadata and unsupported in some Rust paths.
    normalized=QuantumCircuit(*clean.qregs, *clean.cregs)
    normalized.global_phase=clean.global_phase
    for inst in clean.data:
        if inst.operation.name == "barrier":
            continue
        normalized.append(inst.operation, inst.qubits, inst.clbits)
    data=qasm2.dumps(normalized)
    dest=output/(case["file"]+".canonical.qasm")
    write(dest, data)
    return dest, {
        "original_qubits":circuit.num_qubits,
        "original_instructions":len(circuit.data),
        "canonical_instructions":len(normalized.data),
        "canonical_sha256":digest(dest),
        "normalizer":"Qiskit2.6.1 remove_final_measurements and remove barrier",
        "normalizer_qiskit":"2.6.1",
        "canonical_relative_file":dest.name,
    }


def observe_worker(args):
    case, registries = case_for(args.file)
    orig=Path(args.canonical)
    target=ROOT / case[args.variant+"_relative"]
    if digest(target)!=case[args.variant+"_sha256"]:
        raise ValueError("Target QASM SHA mismatch")
    if digest(orig)!=args.canonical_sha256:
        raise ValueError("Canonical original SHA mismatch")
    from QuPRS import check_equivalence
    from QuPRS.utils import get_gpmc_path
    from QuPRS.utils import solver_process
    from scripts.tacas26_level0_1e8_ganak import printed_diagnostics

    with get_gpmc_path() as executable:
        solver_hash=digest(Path(executable))
    versions={}
    for package in ("QuPRS","qiskit","numpy"):
        try:versions[package]=pkg_version(package)
        except PackageNotFoundError:versions[package]=None
    record={
        "schema":SCHEMA,
        "status":"NOT_STARTED",
        "filename":case["file"],
        "variant":args.variant,
        "expected_binary":"EQ" if args.variant=="positive" else "NEQ",
        "backend":args.backend,
        "method":args.method,
        "input_sha256":case["original_sha256"],
        "canonical_sha256":args.canonical_sha256,
        "target_sha256":case[args.variant+"_sha256"],
        "source_sha":os.environ.get("GITHUB_SHA"),
        "github_run_id":os.getenv("GITHUB_RUN_ID"),
        "github_job":os.getenv("GITHUB_JOB"),
        "solver_binary_sha256":solver_hash,
        "versions":versions,
        "python_version":platform.python_version(),
        "platform":platform.platform(),
        "options":{
            "method":args.method, "strategy":"proportional", "backend":args.backend,
            "tool_name":SOLVER, "timeout_seconds":args.timeout,
            "rr_tolerance":RR, "wmc_phase_tolerance":PHASE,
            "approximate_distance_tolerance":DISTANCE,
            "gpmc_precision_digits":GPMC_DIGITS,
        },
        "rr":{"entered":args.method=="hybrid",
              "rr_approximate":None, "residual_sha256":None},
        "wmc":{"status":"NOT_INSTRUMENTED","calls":[]},
        "warnings":[],
        "result":None,
        "performance":"NOT_CODSPEED_NO_PERFORMANCE_CLAIM",
        "solver_arithmetic_certified":False,
    }
    existing=solver_process.run
    captured=[]
    if args.backend=="python":
        def intercept(command,*positional,**keywords):
            result=existing(command,*positional,**keywords)
            if "gpmc" in Path(str(command[0])).name.lower():
                cnf=Path(command[-1])
                captured.append({
                    "argv":list(map(str,command[1:])),
                    "returncode":result.returncode,
                    "raw_stdout":result.stdout,
                    "raw_stderr":result.stderr,
                    "cnf_sha256":digest(cnf) if cnf.is_file() else None,
                    "printed_count":None,
                })
            return result
        solver_process.run=intercept
    try:
        with warnings.catch_warnings(record=True) as raised:
            warnings.simplefilter("always")
            res=check_equivalence(
                str(orig),str(target),method=args.method, strategy="proportional",
                backend=args.backend,tool_name="gpmc",timeout=int(args.timeout),
                rr_tolerance=RR,wmc_phase_tolerance=PHASE,
                approximate_distance_tolerance=DISTANCE,
                gpmc_precision_digits=GPMC_DIGITS,
            )
        record["warnings"]=[{
            "class":w.category.__name__,
            "message":str(w.message),
        } for w in raised]
        verdict=str(res.equivalent)
        bool_invoked=getattr(res,"wmc_solver_invoked",None)
        if bool_invoked is None:
            bool_invoked=bool(captured) or getattr(res,"tool_time",None) is not None
        attributes=(
            "wmc_numerical_verdict","wmc_printed_verdict",
            "wmc_precision_reason","wmc_print_resolution_distance",
            "expect","log_wmc","rr_approximate",
        )
        details={attr:getattr(res,attr,None) for attr in attributes}
        for k,v in details.items():
            if isinstance(v,float) and not math.isfinite(v):
                details[k]=str(v)
        record["result"]={
            "verdict":verdict,
            "binary":binary(verdict),
            "expected_binary":record["expected_binary"],
            "matches_expected":(
                binary(verdict)==record["expected_binary"]
                if binary(verdict) is not None else None
            ),
            "wmc_solver_invoked":bool(bool_invoked),
            **details,
        }
        record["status"]=(
            "RETURNED" if binary(verdict) is not None
            else "CENSORED_TIMEOUT" if verdict=="Timeout"
            else "CENSORED_MEMORY" if verdict=="MemoryOut"
            else "NO_BINARY_VERDICT"
        )
        record["rr"]["rr_approximate"]=details["rr_approximate"]
        residual=getattr(res,"final_pathsum",None)
        if residual is not None:
            record["rr"]["residual_sha256"]=hashlib.sha256(str(residual).encode("utf8")).hexdigest()
        if captured:
            for call in captured:
                call["printed_count"]=printed_diagnostics(
                    call["raw_stdout"],details.get("expect"),DISTANCE)
            record["wmc"]={"status":"RAW_SOLVER_OUTPUT_CAPTURED","calls":captured}
        elif bool_invoked:
            record["wmc"]={"status":(
                "RUST_NATIVE_OUTPUT_NOT_EXPOSED" if args.backend=="rust"
                else "PYTHON_OUTPUT_UNAVAILABLE"),"calls":[]}
        else:
            record["wmc"]={"status":"NO_SOLVER_INVOKED","calls":[]}
    except BaseException as exc:
        record["status"]="EXCEPTION"
        record["exception"]={
            "type":type(exc).__name__,
            "message":str(exc),
            "traceback":traceback.format_exc()[-5000:],
        }
    finally:
        solver_process.run=existing
    print(MARKER+encoded_json(record),flush=True)


def run_case(args):
    case, sources = case_for(args.file)
    try:
        import qiskit
        if qiskit.__version__!="2.6.1":
            raise RuntimeError("Acceptance requires qiskit 2.6.1, not "+qiskit.__version__)
    except ImportError as e:
        raise RuntimeError("Acceptance requires pinned Qiskit") from e
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=True)
    canonical, canonical_meta=normalize_original(case,out)
    invocations=[]
    # Pair Python and Rust backends on each input, method, SHA and CI runner.
    for variant in VARIANTS:
        for method in METHODS:
            for backend in PROFILES:
                name=f"{variant}-{method}-{backend}"
                cmd=[
                    sys.executable,str(Path(__file__).resolve()),"worker",
                    "--file",args.file,
                    "--canonical",str(canonical.resolve()),
                    "--canonical-sha256",canonical_meta["canonical_sha256"],
                    "--variant",variant,
                    "--method",method,
                    "--backend",backend,
                    "--timeout",str(args.timeout),
                ]
                proc=subprocess.Popen(
                    cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    text=True,start_new_session=(os.name=="posix"),
                )
                try:
                    stdout,stderr=proc.communicate(timeout=args.watchdog)
                    matches=[line[len(MARKER):] for line in stdout.splitlines()
                             if line.startswith(MARKER)]
                    if len(matches)==1:
                        try: result=json.loads(matches[0])
                        except json.JSONDecodeError: result={"status":"MALFORMED_WORKER_OUTPUT"}
                    else:
                        result={"status":"MISSING_WORKER_OUTPUT",
                                "output_marker_count":len(matches)}
                    result["exit_code"]=proc.returncode
                except subprocess.TimeoutExpired:
                    if os.name=="posix":
                        try:os.killpg(proc.pid,signal.SIGKILL)
                        except ProcessLookupError: pass
                    else:proc.kill()
                    stdout,stderr=proc.communicate()
                    result={"status":"EXTERNAL_WATCHDOG_CENSORED",
                            "result":None,"exit_code":proc.returncode}
                result.setdefault("schema",SCHEMA)
                result.setdefault("filename",args.file)
                result.setdefault("variant",variant)
                result.setdefault("method",method)
                result.setdefault("backend",backend)
                result.setdefault("expected_binary","EQ" if variant=="positive" else "NEQ")
                result.setdefault("canonical_sha256",canonical_meta["canonical_sha256"])
                result.setdefault("target_sha256",case[variant+"_sha256"])
                result["worker_stderr"]=stderr[-12000:]
                result["worker_stderr_sha256"]=hashlib.sha256(stderr.encode("utf8")).hexdigest()
                result["worker_stdout_sha256"]=hashlib.sha256(stdout.encode("utf8")).hexdigest()
                write(out/(name+".stdout"),stdout)
                write(out/(name+".stderr"),stderr)
                write(out/(name+".json"),json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
                invocations.append(result)
                write(out/"observations.jsonl",
                      "".join(encoded_json(r)+"\n" for r in invocations))
                print("MQT_37_ACCEPTANCE",encoded_json({
                    "file":args.file,
                    "variant":variant,
                    "method":method,
                    "backend":backend,
                    "status":result["status"],
                    "verdict":(result.get("result") or {}).get("verdict"),
                    "expected":result["expected_binary"],
                    "print_resolution":(result.get("result") or {}).get("wmc_print_resolution_distance"),
                }),flush=True)
    manifest={
        "schema":SCHEMA+"-per-case",
        "file":case["file"],
        "source_sha":os.getenv("GITHUB_SHA"),
        "run_id":os.getenv("GITHUB_RUN_ID"),
        "source_registry":sources,
        "case_inputs":case,
        "canonical_input":canonical_meta,
        "expected_count":len(VARIANTS) * len(PROFILES) * len(METHODS),
        "observed_count":len(invocations),
        "outcomes":[{
            "variant":r["variant"],"method":r["method"],"backend":r["backend"],
            "status":r["status"],
            "verdict":(r.get("result") or {}).get("verdict"),
            "matches":(r.get("result") or {}).get("matches_expected"),
        } for r in invocations],
        "raw_sha256":{
            str(p.relative_to(out)):digest(p)
            for p in sorted(out.glob("*")) if p.is_file() and p.name!="manifest.json"
        },
        "safety_policy":"Nonreturned/error/timeout is censored, never NEQ",
        "performance":"NO_TIMING_PERFORMANCE_CODSPEED_ONLY",
    }
    write(out/"manifest.json",json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    if len(invocations)!=8:
        raise RuntimeError("Incomplete per-case invocation ledger")


def aggregate(args):
    inputs=Path(args.input)
    dest=Path(args.output)
    dest.mkdir(parents=True,exist_ok=True)
    cases, provenance=ledger()
    all_rows=[]
    missing=[]
    bad_checksums=[]
    for case in cases:
        dirpath=inputs/("mqt37-"+case["file"][:-5])
        index=dirpath/"manifest.json"
        if not index.is_file():
            missing.append(case["file"])
            continue
        data=json.loads(index.read_text(encoding="utf8"))
        for path,expected in data["raw_sha256"].items():
            p=dirpath/path
            if not p.is_file() or digest(p)!=expected:
                bad_checksums.append(str(p))
        f=dirpath/"observations.jsonl"
        if not f.is_file():
            missing.append(case["file"])
            continue
        rows=[json.loads(line) for line in f.read_text(encoding="utf8").splitlines()]
        if len(rows)!=8:
            missing.append(case["file"]+" partial:"+str(len(rows)))
        for row in rows:
            if row["filename"] != case["file"]:
                raise ValueError("Row case mismatch")
            if row["target_sha256"] != case[row["variant"]+"_sha256"]:
                raise ValueError("Row target SHA mismatch")
        all_rows.extend(rows)
    if bad_checksums:
        raise ValueError("Scientific artifact SHA mismatch: "+str(bad_checksums[:3]))
    write(dest/"observations.jsonl","".join(encoded_json(r)+"\n" for r in all_rows))
    with (dest/"classification.csv").open("w",newline="",encoding="utf8") as f:
        w=csv.writer(f,lineterminator="\n")
        w.writerow(("file","variant","method","backend","expected","actual","status",
                    "matches","solver_invoked","wmc_print_resolution_distance",
                    "wmc_stdout_status","canonical_sha256","target_sha256"))
        for r in all_rows:
            res=r.get("result") or {}
            w.writerow((r["filename"],r["variant"],r["method"],r["backend"],
                        r["expected_binary"],res.get("verdict"),r["status"],
                        res.get("matches_expected"),res.get("wmc_solver_invoked"),
                        res.get("wmc_print_resolution_distance"),
                        (r.get("wmc") or {}).get("status"),
                        r["canonical_sha256"],r["target_sha256"]))
    summaries={}
    for method in METHODS:
        for backend in PROFILES:
            for variant in VARIANTS:
                subset=[r for r in all_rows if (r["method"],r["backend"],r["variant"])==
                        (method,backend,variant)]
                key=f"{backend}:{method}:{variant}"
                summaries[key]={
                    "planned":37,
                    "collected":len(subset),
                    "passed":sum((r.get("result") or {}).get("matches_expected") is True for r in subset),
                    "mismatched":sum((r.get("result") or {}).get("matches_expected") is False for r in subset),
                    "censored":sum((r.get("result") or {}).get("binary") is None for r in subset),
                }
    paired=[]
    for case in cases:
        for variant in VARIANTS:
            for method in METHODS:
                match=[r for r in all_rows if (r["filename"],r["variant"],r["method"])==
                       (case["file"],variant,method)]
                by_backend={r["backend"]:r for r in match}
                if not all(b in by_backend for b in PROFILES):
                    status="NOT_COLLECTED"
                else:
                    a=(by_backend["python"].get("result") or {}).get("binary")
                    b=(by_backend["rust"].get("result") or {}).get("binary")
                    status=("AGREE" if a is not None and a==b else
                            "DISAGREE" if a is not None and b is not None else
                            "CENSORED")
                paired.append({
                    "file":case["file"],"variant":variant,
                    "method":method,"backend_binary_status":status,
                })
    manifest={
        "schema":SCHEMA+"-aggregate",
        "run_id":os.getenv("GITHUB_RUN_ID"),
        "source_sha":args.sha,
        "qasm_version":"Qiskit2.6.1_opt0",
        "source_registry":provenance,
        "solver":"gpmc",
        "distance":DISTANCE,
        "rr":RR,
        "phase":PHASE,
        "digits":GPMC_DIGITS,
        "methods":METHODS,
        "backends":PROFILES,
        "variants":VARIANTS,
        "total_expected":EXPECTED_TOTAL,
        "total_collected":len(all_rows),
        "missing":missing,
        "summaries":summaries,
        "paired_verdicts":paired,
        "all_claims_science_not_timing":True,
        "native_rust_gpmc_stdout_caveat":"GPMC internal native stdout inaccessible without production instrumentation",
        "solver_arithmetic_precision_certified":False,
        "output_sha256":{n:digest(dest/n) for n in ("observations.jsonl","classification.csv")},
    }
    write(dest/"manifest.json",json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    completed=all(v["collected"]==37 for v in summaries.values())
    disagreed=[x for x in paired if x["backend_binary_status"]=="DISAGREE"]
    print("MQT_37_ACCEPTANCE_TOTAL",encoded_json({
        "planned":EXPECTED_TOTAL,"collected":len(all_rows),
        "complete":completed,"backend_disagreements":len(disagreed),
        "summaries":summaries,
    }),flush=True)


def main():
    parser=argparse.ArgumentParser()
    sp=parser.add_subparsers(dest="action",required=True)
    sp.add_parser("preflight")
    sp.add_parser("matrix")
    w=sp.add_parser("worker")
    w.add_argument("--file",required=True)
    w.add_argument("--canonical",required=True)
    w.add_argument("--canonical-sha256",required=True)
    w.add_argument("--variant",choices=VARIANTS,required=True)
    w.add_argument("--method",choices=METHODS,required=True)
    w.add_argument("--backend",choices=PROFILES,required=True)
    w.add_argument("--timeout",type=int,default=200)
    r=sp.add_parser("run")
    r.add_argument("--file",required=True)
    r.add_argument("--timeout",type=int,default=200)
    r.add_argument("--watchdog",type=int,default=215)
    r.add_argument("--output",type=Path,required=True)
    a=sp.add_parser("aggregate")
    a.add_argument("--input",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    a.add_argument("--sha",required=True)
    args=parser.parse_args()
    if args.action in ("preflight","matrix"):
        cases,meta=ledger()
        if args.action=="matrix":
            print(json.dumps({"include":[{"file":x["file"],
                       "key":x["file"][:-5]} for x in cases]},separators=(",",":")))
        else:print("MQT_37_INPUT_PREFLIGHT_PASS",len(cases),encoded_json(meta))
    elif args.action=="worker":observe_worker(args)
    elif args.action=="run":run_case(args)
    else:aggregate(args)


if __name__=="__main__":
    main()
