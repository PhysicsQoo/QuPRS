#!/usr/bin/env python3
"""TACAS26: frozen Qiskit opt0 QASMs -> original and modern QuPRS.

Research-only. All science inputs byte-hashed; NO performance timing and no
approximate verdict is treated as a proof. Every record is written immediately.
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
from importlib.metadata import version as package_version

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "docs/development/tacas26-qiskit-version-fidelity"
LEGACY_SHA = "e928abc47dd15926364ec77905eb0d5dc92ce8cc"
CASES = ("grover4", "qnn8", "qpeinexact8", "qaoa9", "qft16", "vqe16",
         "qft20", "qft22", "qpeexact20")
VERSIONS = ("1.4.2", "2.6.1")
METHODS = ("hybrid", "wmc_only")
PROFILES = ("v091", "python", "rust")
NEG_CONTROLS = ("grover4", "qft20")
DISTANCE = 2e-5
RR = 1e-10
PHASE = 1e-8
DIGITS = 30
MARKER = "QUPRS_LEVEL0_SCIENCE "
SOURCE = "tacas26-level0-verifier-cross-v1"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def write_json(path, obj):
    atomic_write(path, json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n")


def qualified(root, original, expected):
    p = root / original
    if not p.is_file() or digest(p) != expected:
        raise ValueError("QASM byte mismatch: " + original)
    return p


def preflight(output):
    """Save a canonical unitary source file from each archived original QASM."""
    from qiskit import qasm2, QuantumCircuit, __version__ as qiskit_version
    if qiskit_version != "1.4.2":
        raise RuntimeError("Unitary input preparation requires Qiskit 1.4.2")
    raw = json.loads((ARCHIVE/"transpiled-inputs.jsonl").read_text().splitlines()[0])
    if raw["compiler"]["version"] != "1.4.2":
        raise RuntimeError("Unexpected source archive")
    entries = {}
    for line in (ARCHIVE/"transpiled-inputs.jsonl").read_text().splitlines():
        row = json.loads(line)
        if row["compiler"]["optimization_level"] != 0:
            continue
        key = (row["case"], row["compiler"]["version"])
        if key in entries: raise ValueError("Duplicate archived key")
        entries[key] = row
    if set(entries) != {(case,ver) for case in CASES for ver in VERSIONS}:
        raise RuntimeError("Missing opt0 cases in source-pinned Qiskit archive")
    pairs = []
    source_hashes = {}
    for case in CASES:
        row = entries[(case, "1.4.2")]
        src = row["original_qasm"]
        p = qualified(ROOT, src["path_in_repository"], src["sha256"])
        circuit = qasm2.load(str(p)).remove_final_measurements(inplace=False)
        if any(instruction.operation.name in ("measure", "reset")
               for instruction in circuit.data):
            raise ValueError("Non-unitary source not supported: " + case)
        # The same canonical QASM2 is supplied to all three QuPRS profiles.
        clean = QuantumCircuit(*circuit.qregs, *circuit.cregs)
        clean.global_phase = circuit.global_phase
        for instruction in circuit.data:
            if instruction.operation.name == "barrier":
                continue
            clean.append(instruction.operation, instruction.qubits,
                         instruction.clbits)
        relative = "canonical-source/" + case + ".qasm"
        atomic_write(output/relative, qasm2.dumps(clean))
        source_hashes[case] = digest(output/relative)
        for version in VERSIONS:
            item = entries[(case,version)]
            if item["original_qasm"]["sha256"] != src["sha256"]:
                raise ValueError("Original source QASM differs across Qiskit versions")
            compiler = item["compiled_qasm"]
            qualified(ARCHIVE, compiler["path_in_evidence_archive"], compiler["sha256"])
            pair = {
                "id": case + ":" + version + ":opt0:positive",
                "case":case, "qiskit_version": version, "level":0,
                "kind":"positive", "expected_binary":"EQ",
                "source_relative":relative,
                "source_sha256":source_hashes[case],
                "compiled_relative":compiler["path_in_evidence_archive"],
                "compiled_sha256":compiler["sha256"],
                "raw_original_path":src["path_in_repository"],
                "raw_original_sha256":src["sha256"],
                "numerical_source":item["fidelity"]["metric_kind"],
                "numerical_input_sample":item["fidelity"]["serialized_qasm2_vs_original"]["metric"],
            }
            pairs.append(pair)
            if case in NEG_CONTROLS:
                # A final 0.05-radian Rz changes the intended operator, unlike
                # a near-identity rounding perturbation. The exact bytes are frozen.
                changed = qasm2.load(str(ARCHIVE/compiler["path_in_evidence_archive"]))
                changed.rz(0.05, changed.qubits[0])
                control_path = "negative-control/" + case + "-" + version + ".qasm"
                atomic_write(output/control_path, qasm2.dumps(changed))
                pairs.append({
                    **pair,
                    "id":case + ":" + version + ":opt0:negative-rz-0.05",
                    "kind":"negative-rz-0.05", "expected_binary":"NEQ",
                    "compiled_relative":control_path,
                    "compiled_sha256":digest(output/control_path),
                    "control_construction":"append Rz(0.05) to the same transpiled circuit's first qubit",
                    "numerical_input_sample":None,
                })
    if len(pairs)!=22:
        raise RuntimeError("Expected 18 positive and 4 negative pairs")
    result={"schema":SOURCE+"-inputs","qiskit_prepare_version":qiskit_version,
            "source_repository_sha":os.environ.get("GITHUB_SHA"),
            "original_v091_sha":LEGACY_SHA,
            "source_archive_manifest_sha256":digest(ARCHIVE/"evidence-manifest.json"),
            "pairs":pairs}
    write_json(output/"pairs.json",result)
    checksum={str(p.relative_to(output)):digest(p) for p in output.rglob("*")
              if p.is_file() and p.name!="SHA256SUMS"}
    atomic_write(output/"SHA256SUMS","".join(
        f"{value}  {key}\n" for key,value in sorted(checksum.items())))
    print("LEVEL0_SOURCE_PREFLIGHT",len(pairs),flush=True)


def json_safe(o):
    if o is None or isinstance(o,(bool,int,str)): return o
    if isinstance(o,float):return o if math.isfinite(o) else repr(o)
    if isinstance(o,(tuple,list)):return [json_safe(x) for x in o]
    if isinstance(o,dict):return {str(k):json_safe(v) for k,v in o.items()}
    return str(o)


def binary(verdict):
    if verdict in ("equivalent","equivalent*"):return "EQ"
    if verdict=="not_equivalent":return "NEQ"
    return None


def worker(args):
    pair=json.loads(Path(args.pair).read_text(encoding="utf8"))
    p=pair["pair"]
    source=qualified(Path(args.prepare),p["source_relative"],p["source_sha256"])
    counterpart_root = Path(args.prepare) if p["kind"]!="positive" else ARCHIVE
    transformed=qualified(counterpart_root,p["compiled_relative"],p["compiled_sha256"])
    if args.profile not in PROFILES or args.method not in METHODS:
        raise ValueError("Unregistered verifier method/profile")
    environment={
        "ci_source_sha":os.getenv("GITHUB_SHA"),
        "ci_run":os.getenv("GITHUB_RUN_ID"),
        "ci_attempt":os.getenv("GITHUB_RUN_ATTEMPT"),
        "ci_job":os.getenv("GITHUB_JOB"),
        "platform":platform.platform(),
        "python":platform.python_version(),
        "numpy":package_version("numpy"),
        "qiskit":package_version("qiskit"),
    }
    record={
        "schema":SOURCE+"-observed",
        "pair":p,
        "profile":args.profile,
        "method":args.method,
        "strategy":"Proportional" if args.profile=="v091" else "proportional",
        "solver":"gpmc",
        "source_sha": LEGACY_SHA if args.profile=="v091" else os.getenv("GITHUB_SHA"),
        "quprs_package":package_version("QuPRS"),
        "environment":environment,
        "parameters":{
            "legacy_config_tolerance":1e-10 if args.profile=="v091" else None,
            "rr_tolerance":None if args.profile=="v091" else RR,
            "phase_tolerance":None if args.profile=="v091" else PHASE,
            "distance_tolerance":None if args.profile=="v091" else DISTANCE,
            "gpmc_digits":None if args.profile=="v091" else DIGITS,
            "timeout_s":int(args.timeout),
            "verification_mode":"binary classification, science only, NOT CodSpeed"
        },
        "wmc_observation":{"status":"NOT_INSTRUMENTED","raw_calls":[]},
        "rr_observation":{"entered":args.method=="hybrid","finished_before_wmc":None,
                          "approximation_used":None,"residual_sha256":None,
                          "residual_text":None,"rules":"NOT_INSTRUMENTED"},
        "result":None,
        "status":"NOT_EXECUTED",
    }
    captured=[]
    from QuPRS import check_equivalence
    from QuPRS.utils import get_gpmc_path
    with get_gpmc_path() as path:
        record["solver_binary_sha256"]=digest(path)

    if args.profile=="v091":
        from QuPRS.interface import ps2wmc
        existing_run=ps2wmc.subprocess.run
        existing_wmc=ps2wmc.run_wmc

        def old_run(command,*a,**kw):
            result=existing_run(command,*a,**kw)
            argv=command if isinstance(command,(list,tuple)) else [str(command)]
            if any("gpmc" in str(v).lower() for v in argv):
                cnf=str(argv[-1])
                captured.append({
                    "argv":json_safe(argv),
                    "returncode":result.returncode,
                    "raw_stdout":json_safe(result.stdout),
                    "raw_stderr":json_safe(result.stderr),
                    "cnf_sha256":digest(cnf) if Path(cnf).is_file() else None,
                })
            return result

        def old_wmc(*a,**kw):
            value=existing_wmc(*a,**kw)
            record["wmc_parsed_float64"]=json_safe(value)
            return value
        ps2wmc.subprocess.run=old_run
        ps2wmc.run_wmc=old_wmc
    else:
        from QuPRS.utils import solver_process
        existing_run=solver_process.run
        if args.profile=="python":
            def modern_run(command, timeout):
                result=existing_run(command,timeout)
                if "gpmc" in str(command[0]).lower():
                    cnf=Path(command[-1])
                    captured.append({
                        "argv":json_safe(command),"returncode":result.returncode,
                        "raw_stdout":result.stdout,"raw_stderr":result.stderr,
                        "cnf_sha256":digest(cnf) if cnf.is_file() else None,
                        "cnf_status":"HASH_CAPTURED" if cnf.is_file() else "NOT_CAPTURED",
                    })
                return result
            solver_process.run=modern_run

    try:
        opts={"method":args.method,
              "strategy":record["strategy"],"timeout":int(args.timeout)}
        if args.profile!="v091":
            opts.update(backend=args.profile,tool_name="gpmc",
                        rr_tolerance=RR,wmc_phase_tolerance=PHASE,
                        approximate_distance_tolerance=DISTANCE,
                        gpmc_precision_digits=DIGITS)
        result=check_equivalence(str(source),str(transformed),**opts)
        inv=getattr(result,"wmc_solver_invoked",None)
        if inv is None:
            inv=bool(captured) or getattr(result,"to_DIMACS_time",None) is not None
        verdict=str(result.equivalent)
        record["status"]="RETURNED"
        record["api_native_timing_diagnostic_only_not_codspeed"]={
            name:json_safe(getattr(result,name,None))
            for name in ("verification_time","pathsum_time","to_DIMACS_time",
                         "tool_time","gpmc_time","wmc_time")
        }
        record["result"]={
            "verdict":verdict,
            "binary":binary(verdict),
            "matches_input_expected":binary(verdict)==p["expected_binary"],
            "wmc_solver_invoked":bool(inv),
            "wmc_expected_log2":json_safe(getattr(result,"expect",None)),
            "wmc_log2":json_safe(getattr(result,"log_wmc",None)),
            "wmc_numerical_verdict":json_safe(getattr(result,"wmc_numerical_verdict",None)),
            "wmc_printed_verdict":json_safe(getattr(result,"wmc_printed_verdict",None)),
            "wmc_precision_reason":json_safe(getattr(result,"wmc_precision_reason",None)),
            "wmc_print_resolution_distance":json_safe(getattr(result,"wmc_print_resolution_distance",None)),
            "rr_approximate":json_safe(getattr(result,"rr_approximate",None)),
        }
        record["rr_observation"]["finished_before_wmc"]=(
            args.method=="hybrid" and not inv
            if verdict in ("equivalent","equivalent*","not_equivalent") else None)
        record["rr_observation"]["approximation_used"]=json_safe(
            getattr(result,"rr_approximate",None))
        residual=getattr(result,"final_pathsum",None)
        if residual is not None:
            s=str(residual)
            record["rr_observation"]["residual_sha256"]=hashlib.sha256(s.encode()).hexdigest()
            record["rr_observation"]["residual_text"]=s if len(s)<1000000 else None
            if len(s)>=1000000:
                record["rr_observation"]["residual_text_status"]="TOO_LARGE"
        if args.profile=="v091":
            record["rr_observation"]["historical_to_DIMACS_time_present"]=getattr(
                result,"to_DIMACS_time",None) is not None
    except BaseException as exc:
        record["status"]="SOLVER_TIMEOUT" if "Timeout" in type(exc).__name__ else "ERROR"
        record["error"]={"type":type(exc).__name__,"message":str(exc),
                         "traceback":traceback.format_exc()[-3000:]}
    finally:
        if args.profile=="v091":
            ps2wmc.subprocess.run=existing_run
            ps2wmc.run_wmc=existing_wmc
        elif args.profile=="python":
            solver_process.run=existing_run

    if captured:
        record["wmc_observation"]["status"]="SOLVER_RAW_OUTPUT_CAPTURED"
        record["wmc_observation"]["raw_calls"]=captured
        from QuPRS.interface import load_qiskit
        if args.profile!="v091":
            from scripts.tacas26_modern_101_worker import _solver_stdout_details
            expected=record.get("result",{}).get("wmc_expected_log2")
            twice=None
            if isinstance(expected,(int,float)) and math.isfinite(float(expected)):
                norm=float(expected)*2
                if abs(norm-round(norm))<1e-9:twice=int(round(norm))
            for call in captured:
                call["printed_count"]= _solver_stdout_details(
                    str(call["raw_stdout"]),twice,DISTANCE)
        else:
            for call in captured:
                stdout=str(call.get("raw_stdout",""))
                call["solver_printed_lines"]=[line for line in stdout.splitlines()
                     if line.startswith("c s exact")]
                call["stdout_sha256"]=hashlib.sha256(stdout.encode()).hexdigest()
    else:
        if args.profile=="rust" and record.get("result",{}).get("wmc_solver_invoked"):
            record["wmc_observation"]["status"]="RUST_INTERNAL_SOLVER_STDOUT_NOT_EXPOSED"
        elif record.get("result",{}).get("wmc_solver_invoked") is False:
            record["wmc_observation"]["status"]="NO_SOLVER_CALLED"
        else:
            record["wmc_observation"]["status"]="NOT_CAPTURED"
    if args.profile=="rust":
        record["wmc_observation"]["raw_stdout_limitation"]=(
            "Rust FFI does not expose native GPMC stdout; no replacement or fabricated value")
    print(MARKER+json.dumps(record,sort_keys=True,ensure_ascii=False),flush=True)


def execute(args):
    entries=json.loads((Path(args.prepare)/"pairs.json").read_text())["pairs"]
    selected=[p for p in entries if CASES.index(p["case"])%args.shards==args.shard]
    if not selected or args.shards!=9 or args.shard not in range(9):
        raise ValueError("Unexpected science shard")
    output=Path(args.output)
    output.mkdir(parents=True,exist_ok=True)
    rows=[]
    for p in selected:
        for method in METHODS:
            label=p["id"].replace(":","_")+"_"+method
            pairfile=output/(label+".pair.json")
            write_json(pairfile,{"pair":p})
            cmd=[sys.executable,str(Path(__file__).resolve()),"worker",
                 "--pair",str(pairfile),"--prepare",str(Path(args.prepare).resolve()),
                 "--profile",args.profile,"--method",method,
                 "--timeout",str(args.timeout)]
            child=subprocess.Popen(cmd,cwd=ROOT,stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,text=True,
                                   start_new_session=True)
            try:
                stdout,stderr=child.communicate(timeout=args.watchdog)
                markers=[l[len(MARKER):] for l in stdout.splitlines() if l.startswith(MARKER)]
                if len(markers)==1:
                    try: observation=json.loads(markers[0])
                    except ValueError:
                        observation={"status":"MALFORMED_OBSERVATION"}
                else:
                    observation={"status":"MISSING_OBSERVATION","marker_count":len(markers)}
                observation["exit_code"]=child.returncode
            except subprocess.TimeoutExpired:
                try:os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                stdout,stderr=child.communicate()
                observation={"status":"EXTERNAL_WATCHDOG_CENSORED",
                             "exit_code":child.returncode,"result":None}
            observation.setdefault("pair",p)
            observation.setdefault("profile",args.profile)
            observation.setdefault("method",method)
            observation["stdout_file"]=label+".stdout"
            observation["stderr_file"]=label+".stderr"
            atomic_write(output/(label+".stdout"),stdout)
            atomic_write(output/(label+".stderr"),stderr)
            observation["stdout_sha256"]=digest(output/(label+".stdout"))
            observation["stderr_sha256"]=digest(output/(label+".stderr"))
            write_json(output/(label+".json"),observation)
            rows.append(observation)
            write_json(output/"summary.json",{
                "schema":SOURCE+"-shard",
                "profile":args.profile,"shard":args.shard,
                "source_sha":os.getenv("GITHUB_SHA"),
                "ci_run":os.getenv("GITHUB_RUN_ID"),
                "results":[{"id":r["pair"]["id"],"method":r["method"],
                            "status":r["status"],
                            "verdict":(r.get("result") or {}).get("verdict")}
                           for r in rows]})
            print("LEVEL0_QU_PRS",json.dumps({
                "case":p["id"],"profile":args.profile,"method":method,
                "status":observation["status"],
                "verdict":(observation.get("result") or {}).get("verdict")
            }),flush=True)


def aggregate(args):
    root=Path(args.input)
    output=Path(args.output)
    output.mkdir(parents=True,exist_ok=True)
    observations=[]
    sums={}
    for profile in PROFILES:
        for shard in range(9):
            folder=root/("tacas26-level0-"+profile+"-"+str(shard))
            summary=folder/"summary.json"
            if not summary.is_file():
                observations.append({
                    "status":"MISSING_SHARD","profile":profile,"shard":shard})
                continue
            record=json.loads(summary.read_text())
            for s in record["results"]:
                name=s["id"].replace(":","_")+"_"+s["method"]
                p=folder/(name+".json")
                if not p.is_file():
                    raise ValueError("Missing listed per-case record "+str(p))
                row=json.loads(p.read_text())
                if row.get("stdout_sha256") != digest(folder/row["stdout_file"]):
                    raise ValueError("stdout digest mismatch")
                if row.get("stderr_sha256") != digest(folder/row["stderr_file"]):
                    raise ValueError("stderr digest mismatch")
                observations.append(row)
            for p in folder.rglob("*"):
                if p.is_file():
                    sums[str(p.relative_to(root))]=digest(p)
    # Never claim a missing result was equivalent.
    total=len(observations)
    completed=sum(row.get("status")=="RETURNED" for row in observations)
    matches=sum((row.get("result") or {}).get("matches_input_expected") is True
                for row in observations)
    outcomes=[]
    for x in observations:
        outcome=x.get("result") or {}
        pair=x.get("pair") or {}
        outcomes.append({
            "profile":x.get("profile"),"case":pair.get("case"),
            "qiskit":pair.get("qiskit_version"),"kind":pair.get("kind"),
            "method":x.get("method"),"status":x.get("status"),
            "verdict":outcome.get("verdict"),"binary":outcome.get("binary"),
            "expected":pair.get("expected_binary"),
            "matches_expected":outcome.get("matches_input_expected"),
            "wmc_invoked":outcome.get("wmc_solver_invoked"),
            "raw_wmc_status":(x.get("wmc_observation") or {}).get("status"),
            "source_qasm_sha256":pair.get("source_sha256"),
            "compiled_qasm_sha256":pair.get("compiled_sha256"),
        })
    with (output/"science.csv").open("w",newline="",encoding="utf8") as f:
        cols=list(outcomes[0])
        w=csv.DictWriter(f,fieldnames=cols)
        w.writeheader();w.writerows(outcomes)
    jsonl="".join(json.dumps(row,sort_keys=True,ensure_ascii=False)+"\n"
                  for row in observations)
    atomic_write(output/"observations.jsonl",jsonl)
    manifest={
        "schema":SOURCE+"-aggregate",
        "original_quprs_source_sha":LEGACY_SHA,
        "modern_quprs_source_sha":args.sha,
        "ci_run_id":os.getenv("GITHUB_RUN_ID"),
        "expected_total_invocations":132,
        "collected_records":total,
        "returned_records":completed,
        "matched_expected_positive_or_negative":matches,
        "nonreturned_records":total-completed,
        "solver":"GPMC",
        "tolerances_modern":{"rr":RR,"phase":PHASE,"distance":DISTANCE,
                             "gpmc_digits":DIGITS},
        "historical_tolerance":"legacy v0.9.1 native classifier",
        "performance":"NOT_CODSPEED_NOT_MEASURED",
        "source_qiskit_archive_sha256":digest(ARCHIVE/"evidence-manifest.json"),
        "source_checksum_map":sums,
        "output_hashes":{
            "observations.jsonl":digest(output/"observations.jsonl"),
            "science.csv":digest(output/"science.csv")},
        "caveats":[
            "a missing / timed-out case is censored, NOT not_equivalent",
            "the Rust FFI does not expose solver stdout; absence is explicit",
            "no solver arithmetic error bound certified",
            "v0.9.1 and modern native tolerance semantics differ",
            "no runtime performance comparisons outside CodSpeed",
        ],
    }
    write_json(output/"manifest.json",manifest)
    print("LEVEL0_CROSS_AGGREGATE",json.dumps({
        "total":total,"expected":132,"completed":completed,
        "matches_expected":matches,"incomplete":132-completed},sort_keys=True),flush=True)


def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="action",required=True)
    a=sub.add_parser("preflight")
    a.add_argument("--output",type=Path,required=True)
    b=sub.add_parser("worker")
    b.add_argument("--pair",type=Path,required=True)
    b.add_argument("--prepare",type=Path,required=True)
    b.add_argument("--profile",choices=PROFILES,required=True)
    b.add_argument("--method",choices=METHODS,required=True)
    b.add_argument("--timeout",type=int,default=200)
    c=sub.add_parser("run")
    c.add_argument("--prepare",type=Path,required=True)
    c.add_argument("--profile",choices=PROFILES,required=True)
    c.add_argument("--shard",type=int,required=True)
    c.add_argument("--shards",type=int,default=9)
    c.add_argument("--timeout",type=int,default=200)
    c.add_argument("--watchdog",type=int,default=215)
    c.add_argument("--output",type=Path,required=True)
    d=sub.add_parser("aggregate")
    d.add_argument("--input",type=Path,required=True)
    d.add_argument("--output",type=Path,required=True)
    d.add_argument("--sha",required=True)
    ns=ap.parse_args()
    if ns.action=="preflight":preflight(ns.output)
    elif ns.action=="worker":worker(ns)
    elif ns.action=="run":execute(ns)
    else:aggregate(ns)


if __name__=="__main__":
    main()
