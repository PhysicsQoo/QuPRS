#!/usr/bin/env python3
"""QuPRS Level0 QASM at 1e-8: GPMC vs Ganak, Python vs Rust, science only.

Pinned original and compiled QASM bytes are NOT regenerated or changed.
All raw solver stdout is captured when observable; Rust internal stdout is
unavailable without production instrumentation. No performance comparisons.
"""
from __future__ import annotations
import argparse
import csv
from decimal import Decimal, localcontext
from fractions import Fraction
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
from importlib.metadata import version

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"docs/development/tacas26-qiskit-version-fidelity"
FIXED=ROOT/"docs/development/tacas26-level0-quprs-cross/inputs/41562334781"
DISTANCE=1e-8
RR=1e-10
PHASE=1e-8
DIGITS=30
SOURCE_CI=41562334781
GROUPS={
    "small":("grover4","qnn8","qpeinexact8","qaoa9","qft16"),
    "large":("qft20","qft22","qpeexact20"),
    "vqe":("vqe16",),
}
MARKER="TACAS_LEVEL0_1E8_SOLVER "
SCHEMA="tacas26-qiskit142-opt0-gpmc-ganak-1e8-v1"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path,content):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(content,encoding="utf-8")


def source_pairs():
    data=json.loads((FIXED/"pairs.json").read_text(encoding="utf8"))
    if data.get("schema")!="tacas26-level0-verifier-cross-v1-inputs":
        raise ValueError("Wrong original evidence contract")
    if data.get("source_repository_sha")!="131c95a659b0b89675bba24d913d6114af96f74f":
        raise ValueError("Wrong experiment source SHA")
    cases={}
    for row in data["pairs"]:
        if row["qiskit_version"]!="1.4.2": continue
        case=(row["case"],row["kind"])
        if case in cases:raise ValueError("Duplicate QASM case")
        source=FIXED/row["source_relative"]
        target=(FIXED if row["kind"]!="positive" else ARCHIVE)/row["compiled_relative"]
        for path,expected in ((source,row["source_sha256"]),(target,row["compiled_sha256"])):
            if not path.is_file() or sha(path)!=expected:
                raise ValueError("QASM input missing / changed: "+str(path))
        cases[case]=row
    expected={(case,"positive") for xs in GROUPS.values() for case in xs}
    expected.update({("grover4","negative-rz-0.05"),("qft20","negative-rz-0.05")})
    if set(cases)!=expected:raise ValueError("Unexpected Qiskit1.4.2 Level0 case register")
    return cases


def binary(label):
    if label in ("equivalent","equivalent*"):return "EQ"
    if label=="not_equivalent":return "NEQ"
    return None


def printed_diagnostics(raw,expected,eps):
    from QuPRS.utils.precision_count import parse_printed_solver_output,classify_printed_distance
    result={"raw_stdout_sha256":hashlib.sha256(raw.encode()).hexdigest(),
            "solver_arithmetic_certified":False,
            "solver_arithmetic_error_bound":None}
    try:
        cnt=parse_printed_solver_output(raw)
        result.update({
            "real_printed_exact_fraction":str(cnt.real),
            "imag_printed_exact_fraction":str(cnt.imag),
            "real_print_half_unit":str(cnt.real_print_half_unit),
            "imag_print_half_unit":str(cnt.imag_print_half_unit),
            "printed_format":cnt.format_name,
        })
        if expected is None:
            result["status"]="MISSING_NORMALIZATION"
            return result
        n=float(expected)*2
        if not math.isfinite(n) or abs(n-round(n))>1e-8:
            result["status"]="NONINTEGRAL_NORMALIZATION";return result
        k=int(round(n))
        p=classify_printed_distance(cnt,k,eps)
        result["classification_status"]=p.status
        result["classification_reason"]=p.reason
        result["normalization_twice_log2"]=k
        with localcontext() as ctx:
            ctx.prec=110
            def de(f):return Decimal(f.numerator)/Decimal(f.denominator)
            root=Decimal(1)-(de(cnt.real)**2+de(cnt.imag)**2)/(Decimal(2)**k)
            result["signed_one_minus_normalized_count_square"]=str(root)
            if root>=0:
                result["printed_point_projective_distance"]=str(root.sqrt())
                result["status"]="PRINTED_POINT"
            else:
                result["printed_point_projective_distance"]=None
                result["status"]="NONPHYSICAL_PRINTED_MAGNITUDE"
        return result
    except Exception as e:
        result["status"]="PRINTED_PARSER_ERROR"
        result["error"]=f"{type(e).__name__}: {e}"
        return result


def worker(p,method,backend,solver,timeout):
    src=FIXED/p["source_relative"]
    target=(FIXED if p["kind"]!="positive" else ARCHIVE)/p["compiled_relative"]
    if sha(src)!=p["source_sha256"] or sha(target)!=p["compiled_sha256"]:
        raise ValueError("QASM hash changed between registration and run")
    from QuPRS import check_equivalence
    from QuPRS.utils import get_gpmc_path,get_ganak_path
    import QuPRS
    with (get_gpmc_path() if solver=="gpmc" else get_ganak_path()) as exe:
        exe_sha=sha(exe)
    record={
        "schema":SCHEMA,"source_inputs_ci":SOURCE_CI,
        "pair":p,"method":method,"backend":backend,"solver":solver,
        "quprs_source_commit":os.environ.get("GITHUB_SHA"),
        "quprs_version":getattr(QuPRS,"__version__",None),
        "ci_run_id":os.getenv("GITHUB_RUN_ID"),
        "ci_attempt":os.getenv("GITHUB_RUN_ATTEMPT"),
        "environment":{"python":platform.python_version(),
                       "qiskit":version("qiskit"),"numpy":version("numpy"),
                       "platform":platform.platform()},
        "solver_binary_sha256":exe_sha,
        "solver_mode":"-mode=1" if solver=="gpmc" else "--mode=6",
        "parameters":{"distance":DISTANCE,"rr":RR,"phase":PHASE,
                      "gpmc_digits":DIGITS if solver=="gpmc" else None,
                      "timeout_seconds":timeout,"strategy":"proportional"},
        "rr":{"entered":method=="hybrid","approximate":None,
              "residual_pathsum_sha256":None,"rules":"NOT_INSTRUMENTED"},
        "wmc":{"status":"NOT_INSTRUMENTED","calls":[]},
        "status":"NOT_EXECUTED","result":None,
        "arithmetic_certification":"NOT_CERTIFIED",
        "timing":"NO_PERFORMANCE_MEASUREMENT_USE_CODSPEED",
    }
    import QuPRS.utils.solver_process as proc
    real_run=proc.run
    captures=[]
    if backend=="python":
        def intercept(command,deadline):
            out=real_run(command,deadline)
            path=str(command[0]).lower()
            if solver in Path(path).name:
                cnf=Path(command[-1])
                captures.append({
                    "argv_without_executable":list(map(str,command[1:])),
                    "cnf_sha256":sha(cnf) if cnf.is_file() else None,
                    "returncode":out.returncode,
                    "raw_stdout":out.stdout,
                    "raw_stderr":out.stderr,
                    "raw_stderr_sha256":hashlib.sha256(out.stderr.encode()).hexdigest(),
                })
            return out
        proc.run=intercept
    try:
        result=check_equivalence(
            str(src),str(target),method=method,strategy="proportional",
            tool_name=solver,backend=backend,timeout=timeout,
            rr_tolerance=RR,wmc_phase_tolerance=PHASE,
            approximate_distance_tolerance=DISTANCE,
            gpmc_precision_digits=DIGITS,
        )
        label=str(result.equivalent)
        invoked=getattr(result,"wmc_solver_invoked",None)
        if invoked is None:invoked=bool(captures) or getattr(result,"tool_time",None) is not None
        data={
            "verdict":label,"binary":binary(label),
            "expected_binary":p["expected_binary"],
            "expected_matches_observed":binary(label)==p["expected_binary"] if binary(label) else None,
            "solver_invoked":bool(invoked),
            "wmc_numerical_verdict":getattr(result,"wmc_numerical_verdict",None),
            "wmc_printed_verdict":getattr(result,"wmc_printed_verdict",None),
            "wmc_precision_reason":getattr(result,"wmc_precision_reason",None),
            "wmc_print_resolution_distance":getattr(result,"wmc_print_resolution_distance",None),
            "wmc_normalization_log2":getattr(result,"expect",None),
            "wmc_log_wmc":getattr(result,"log_wmc",None),
            "rr_approximate":getattr(result,"rr_approximate",None),
        }
        for key,val in list(data.items()):
            if isinstance(val,float) and not math.isfinite(val): data[key]=str(val)
        record["result"]=data
        record["status"]="RETURNED" if label not in ("Timeout","MemoryOut") else label.upper()
        record["rr"]["approximate"]=data["rr_approximate"]
        residual=getattr(result,"final_pathsum",None)
        if residual is not None:
            record["rr"]["residual_pathsum_sha256"]=hashlib.sha256(str(residual).encode()).hexdigest()
        if captures:
            for entry in captures:
                entry["printed_count"]=printed_diagnostics(
                    entry["raw_stdout"],data["wmc_normalization_log2"],DISTANCE)
            record["wmc"]={"status":"RAW_STDOUT_CAPTURED","calls":captures}
        else:
            status=("NO_WMC_CALLED" if not invoked else
                    "RUST_NATIVE_STDOUT_NOT_EXPOSED" if backend=="rust" else
                    "SOLVER_STDOUT_NOT_CAPTURED")
            record["wmc"]={"status":status,"calls":[]}
    except BaseException as exc:
        record["status"]="EXCEPTION"
        record["exception"]={"type":type(exc).__name__,"message":str(exc),
                             "traceback":traceback.format_exc()[-3000:]}
    finally:
        proc.run=real_run
    print(MARKER+json.dumps(record,sort_keys=True,default=str,ensure_ascii=False),flush=True)


def run_group(args):
    pairs=source_pairs()
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    collected=[]
    for case in GROUPS[args.group]:
        kinds=["positive"]+(["negative-rz-0.05"] if case in ("grover4","qft20") else [])
        for kind in kinds:
            p=pairs[(case,kind)]
            for method in ("hybrid","wmc_only"):
                name=f"{case}-{kind}-{method}-{args.backend}-{args.solver}"
                cmd=[sys.executable,__file__,"worker",
                     "--case",case,"--kind",kind,"--method",method,
                     "--backend",args.backend,"--solver",args.solver,
                     "--timeout",str(args.timeout)]
                child=subprocess.Popen(cmd,cwd=ROOT,start_new_session=True,
                                       stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                try:
                    stdout,stderr=child.communicate(timeout=args.watchdog)
                    matching=[x[len(MARKER):] for x in stdout.splitlines()
                              if x.startswith(MARKER)]
                    if len(matching)==1:
                        try: data=json.loads(matching[0])
                        except json.JSONDecodeError:
                            data={"status":"INVALID_JSON"}
                    else:data={"status":"MISSING_WORKER_OBSERVATION"}
                    data["process_exit_code"]=child.returncode
                except subprocess.TimeoutExpired:
                    try:os.killpg(child.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    stdout,stderr=child.communicate()
                    data={"status":"EXTERNAL_WATCHDOG_CENSORED",
                          "process_exit_code":child.returncode,
                          "result":None}
                data.setdefault("pair",p)
                data.setdefault("backend",args.backend)
                data.setdefault("solver",args.solver)
                data.setdefault("method",method)
                data["worker_stdout_sha256"]=hashlib.sha256(stdout.encode()).hexdigest()
                data["worker_stderr_sha256"]=hashlib.sha256(stderr.encode()).hexdigest()
                write(output/(name+".stdout"),stdout)
                write(output/(name+".stderr"),stderr)
                write(output/(name+".json"),json.dumps(data,indent=2,sort_keys=True)+"\n")
                collected.append(data)
                write(output/"observations.jsonl","".join(
                    json.dumps(q,sort_keys=True)+"\n" for q in collected))
                print("TACAS_LEVEL0_1E8_OBSERVATION",json.dumps({
                    "id":p["id"],"method":method,"backend":args.backend,
                    "solver":args.solver,"status":data["status"],
                    "verdict":(data.get("result") or {}).get("verdict"),
                    "printed_resolution":(data.get("result") or {}).get(
                        "wmc_print_resolution_distance")},sort_keys=True),flush=True)
    checksum={str(q.relative_to(output)):sha(q) for q in output.rglob("*") if q.is_file()}
    write(output/"manifest.json",json.dumps({
        "schema":SCHEMA+"-shard","group":args.group,
        "backend":args.backend,"solver":args.solver,
        "qiskit_version":"1.4.2","optimization_level":0,
        "source_ci_run":SOURCE_CI,
        "source_sha":os.getenv("GITHUB_SHA"),
        "ci_run_id":os.getenv("GITHUB_RUN_ID"),
        "record_count":len(collected),
        "records_returned":sum(x["status"]=="RETURNED" for x in collected),
        "raw_sha256":checksum,"solver_arithmetic_certified":False,
        "codspeed_performance":"NOT_MEASURED",
    },indent=2,sort_keys=True)+"\n")


def aggregate(args):
    input_dir=Path(args.input)
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    rows=[];missing=[]
    for solver in ("gpmc","ganak"):
        for backend in ("python","rust"):
            for group in GROUPS:
                folder=input_dir/f"level0-{solver}-{backend}-{group}"
                f=folder/"observations.jsonl"
                if not f.is_file():
                    missing.append({"solver":solver,"backend":backend,"group":group})
                    continue
                items=[json.loads(line) for line in f.read_text().splitlines()]
                checks=json.loads((folder/"manifest.json").read_text())["raw_sha256"]
                for file,expected in checks.items():
                    path=folder/file
                    if not path.is_file() or sha(path)!=expected:
                        raise ValueError("Bad shard hash: "+str(path))
                rows.extend(items)
    if len(rows)!=88 and not missing:
        raise RuntimeError("Expected 88 observations across GPMC and Ganak")
    write(output/"observations.jsonl","".join(
        json.dumps(x,sort_keys=True,ensure_ascii=False)+"\n" for x in rows))
    csv_cols=("case","kind","solver","backend","method","verdict","status",
              "expected","correct","print_resolution","wmc_output_status")
    with (output/"classification.csv").open("w",newline="",encoding="utf8") as stream:
        w=csv.writer(stream,lineterminator="\n");w.writerow(csv_cols)
        for d in rows:
            p=d["pair"];r=d.get("result") or {}
            w.writerow((p["case"],p["kind"],d["solver"],d["backend"],d["method"],
                        r.get("verdict"),d["status"],p["expected_binary"],
                        r.get("expected_matches_observed"),
                        r.get("wmc_print_resolution_distance"),
                        (d.get("wmc") or {}).get("status")))
    summary={}
    for solver in ("gpmc","ganak"):
        for backend in ("python","rust"):
            these=[r for r in rows if r["solver"]==solver and r["backend"]==backend]
            summary[solver+":"+backend]={
                "records":len(these),
                "matches":sum((r.get("result") or {}).get("expected_matches_observed") is True for r in these),
                "mismatches":sum((r.get("result") or {}).get("expected_matches_observed") is False for r in these),
                "no_binary":sum((r.get("result") or {}).get("binary") is None for r in these),
            }
    meta={
        "schema":SCHEMA+"-aggregate",
        "science_inputs_ci":SOURCE_CI,"source_sha":args.sha,
        "run_id":os.getenv("GITHUB_RUN_ID"),
        "distance_tolerance":DISTANCE,"phase_tolerance":PHASE,
        "rr_tolerance":RR,"gpmc_precision_digits":DIGITS,
        "solver_arithmetic_certified":False,
        "samples_qiskit_version":"1.4.2",
        "expected_count":88,"observed_count":len(rows),
        "missing_shards":missing,"summary":summary,
        "source_corpus_manifest_sha256":sha(ARCHIVE/"evidence-manifest.json"),
        "output_sha256":{n:sha(output/n) for n in ("observations.jsonl","classification.csv")},
        "native_rust_stdout":"NOT_EXPOSED_WHEN_SOLVER_INVOKED",
        "replay_instructions":"Use precisely QASM SHA256 in original inputs/41562334781 and archive generated-qasm",
        "performance":"SCIENCE_ONLY_NO_CODSPEED_TIMING",
    }
    write(output/"manifest.json",json.dumps(meta,indent=2,sort_keys=True)+"\n")
    print("TACAS_LEVEL0_1E8_SUMMARY",json.dumps(summary,sort_keys=True),flush=True)


def main():
    ap=argparse.ArgumentParser()
    sp=ap.add_subparsers(dest="task",required=True)
    for task in ("preflight","worker","run","aggregate"):
        p=sp.add_parser(task)
        if task in ("worker","run"):
            p.add_argument("--backend",choices=("python","rust"),required=True)
            p.add_argument("--solver",choices=("gpmc","ganak"),required=True)
            p.add_argument("--timeout",type=int,default=200)
        if task=="worker":
            p.add_argument("--case",choices=[x for xs in GROUPS.values() for x in xs],required=True)
            p.add_argument("--kind",choices=("positive","negative-rz-0.05"),required=True)
            p.add_argument("--method",choices=("hybrid","wmc_only"),required=True)
        if task=="run":
            p.add_argument("--group",choices=list(GROUPS),required=True)
            p.add_argument("--watchdog",type=int,default=215)
            p.add_argument("--output",required=True,type=Path)
        if task=="aggregate":
            p.add_argument("--input",required=True,type=Path)
            p.add_argument("--output",required=True,type=Path)
            p.add_argument("--sha",required=True)
    a=ap.parse_args()
    if a.task=="preflight":
        pairs=source_pairs()
        print("TACAS_LEVEL0_1E8_PREFLIGHT",len(pairs))
    elif a.task=="worker":
        pairs=source_pairs()
        worker(pairs[(a.case,a.kind)],a.method,a.backend,a.solver,a.timeout)
    elif a.task=="run":
        run_group(a)
    else:
        aggregate(a)


if __name__=="__main__":
    main()
