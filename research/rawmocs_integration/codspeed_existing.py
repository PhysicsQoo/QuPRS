"""Bounded same-CNF solver CPU probes drawn from existing QuPRS CodSpeed cases."""
import argparse
from contextlib import nullcontext
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shlex
import sys
import time
from unittest.mock import patch

from QuPRS import check_equivalence
from QuPRS.utils import solver_process
from benchmarks.codspeed.case_registry import SOLVER_CPU_CASES
from rawmocs_quprs import registered_rawmocs
from release_native_paired import parse

ROOT = Path(".rawmocs-codspeed")
RAW = Path(".rawmocs/crates/rawmocs-cli/target/release/rawmocs").resolve()
GPMC = Path(".gpmc/build/gpmc").resolve()
ARMS = ("gpmc", "rawmocs")
CASES = ("vqe4", "grover4", "qaoa7", "qft16")
POSITIVE = ("equivalent", "equivalent*")


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def save(report):
    (ROOT / "report.json").write_text(json.dumps(report, indent=2) + "\n")


def inspect(arm, stdout, stderr):
    row = parse(stdout, arm)
    if arm == "gpmc":
        assert re.findall(r"^c o precision (\d+)\s*$", stdout, re.M) == ["30"]
    else:
        route, = re.findall(r"^RAWMOCS_COMPLETE route=(\w+) digits=30 bits=100 ", stderr, re.M)
        row["route"] = route
    return row


def same_count(a, b):
    scale = max(Fraction(1), *(abs(Fraction(r[k])) for r in (a,b) for k in ("real","imag")))
    return a["sat"] == b["sat"] and max(abs(Fraction(a[k])-Fraction(b[k])) for k in ("real","imag"))/scale <= Fraction(1,10**24)


def command(arm, cnf):
    return ([str(GPMC), "-mode=1", "-prec=30", str(cnf)] if arm == "gpmc" else
            [str(RAW), "--digits", "30", "--timeout-ms", "300000", str(cnf)])


def prepare():
    ROOT.mkdir(exist_ok=True)
    os.environ["QUPRS_GPMC_PATH"] = str(GPMC)
    report = {"status":"PREPARING", "working_digits":30, "working_bits":100,
              "binary_sha256":{"gpmc":digest(GPMC),"rawmocs":digest(RAW)}, "cases":{}}
    config = ["options:", '  max-time: "5s"', "benchmarks:"]
    original = solver_process.run
    for name in CASES:
        _, filename, strategy, reverse, _, _ = next(c for c in SOLVER_CPU_CASES if c[0] == name+"-gpmc-rust")
        root = Path("benchmarks/MQTBench")
        lhs, rhs = root/filename, root/"h,ry,rz,cx"/filename
        if reverse:
            lhs, rhs = rhs, lhs
        case = {"source":[str(lhs),str(rhs)],"source_sha256":[digest(lhs),digest(rhs)],"strategy":strategy,"native":{},"status":"PENDING"}
        report["cases"][name] = case
        save(report)
        for arm in ARMS:
            row = {}
            case["native"][arm] = row
            def observed(cmd, timeout):
                assert "cnf_sha256" not in row
                cnf = ROOT / f"{name}-{arm}.cnf"
                cnf.write_bytes(Path(cmd[-1]).read_bytes())
                row["cnf_sha256"] = digest(cnf)
                start = time.monotonic()
                try:
                    result = original(["prlimit","--as=3221225472","--",*command(arm,cnf)], timeout=min(timeout,1.0))
                finally:
                    row["solver_wall_s"] = time.monotonic()-start
                (ROOT/f"{name}-{arm}.native.stdout").write_text(result.stdout)
                (ROOT/f"{name}-{arm}.native.stderr").write_text(result.stderr)
                assert result.returncode == 0, f"solver exit {result.returncode}"
                row.update(inspect(arm,result.stdout,result.stderr))
                return result
            ctx = registered_rawmocs(RAW,digits=30,timeout_ms=300000,address_space_bytes=None) if arm=="rawmocs" else nullcontext()
            try:
                with ctx, patch.object(solver_process,"run",observed):
                    result = check_equivalence(str(lhs),str(rhs),method="hybrid",strategy=strategy,
                                               backend="python",tool_name=arm,timeout=30)
                row["verdict"] = str(result.equivalent)
                row["invoked"] = bool(result.wmc_solver_invoked)
                row["status"] = ("PASS" if row["verdict"] in POSITIVE and row["invoked"] and
                                 row.get("solver_wall_s",2)<=1 and "real" in row else
                                 "CENSORED" if row["verdict"] in ("Timeout","MemoryOut") else
                                 "NOT_ADMITTED")
            except Exception as exc:
                row.update(status="ERROR",error=f"{type(exc).__name__}: {str(exc)[:500]}")
            save(report)
        g,r = (case["native"][a] for a in ARMS)
        if not (g["status"]==r["status"]=="PASS"):
            case["status"]="NOT_ADMITTED"
            continue
        if not (g["cnf_sha256"]==r["cnf_sha256"] and g["verdict"]==r["verdict"] and same_count(g,r)):
            case["status"]="NUMERIC_OR_SOURCE_MISMATCH"
            continue
        cnf=ROOT/f"{name}-gpmc.cnf"
        for arm in ARMS:
            wrapper=ROOT/f"{name}-{arm}.sh"
            stdout=ROOT/f"{name}-{arm}.simulation.stdout"
            stderr=ROOT/f"{name}-{arm}.simulation.stderr"
            wrapper.write_text("#!/bin/sh\nexec "+shlex.join(command(arm,cnf))+" >"+shlex.quote(str(stdout))+" 2>"+shlex.quote(str(stderr))+"\n")
            wrapper.chmod(0o755)
            config.extend([f'  - name: "quprs_existing/{name}/{arm}_mpfr100"',f'    exec: "./{wrapper}"'])
        case["status"]="ADMITTED"
        save(report)
    report["status"]="PREFLIGHT_COMPLETE"
    save(report)
    assert any(c["status"]=="ADMITTED" for c in report["cases"].values()), "No matched short solver cohort admitted"
    assert all(c["status"]!="NUMERIC_OR_SOURCE_MISMATCH" for c in report["cases"].values()), "Source or count parity failed"
    Path("codspeed-rawmocs.generated.yml").write_text("\n".join(config)+"\n")
    print("RAWMOCS_CODSPEED_PREFLIGHT",json.dumps(report),flush=True)


def verify():
    report=json.loads((ROOT/"report.json").read_text())
    assert report["status"]=="PREFLIGHT_COMPLETE"
    assert report["binary_sha256"]=={"gpmc":digest(GPMC),"rawmocs":digest(RAW)}
    report["status"]="SIMULATION_INCONCLUSIVE"
    try:
        for name,case in report["cases"].items():
            if case["status"]!="ADMITTED":
                continue
            assert digest(ROOT/f"{name}-gpmc.cnf")==case["native"]["gpmc"]["cnf_sha256"]
            case["simulation"]={}
            for arm in ARMS:
                row=inspect(arm,(ROOT/f"{name}-{arm}.simulation.stdout").read_text(),
                            (ROOT/f"{name}-{arm}.simulation.stderr").read_text())
                case["simulation"][arm]=row
                assert all(row[k]==case["native"][arm][k] for k in row)
            case["status"]="SIMULATION_PARITY_PASS"
        report["status"]="SIMULATION_PARITY_PASS"
    finally:
        save(report)
        print("RAWMOCS_CODSPEED_FINAL",json.dumps(report),flush=True)


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("stage",choices=("prepare","verify"))
    (prepare if ap.parse_args().stage=="prepare" else verify)()
