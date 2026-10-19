#!/usr/bin/env python3
"""Pinned, same-runner WMC A/B test. Incorrect baseline oracle calls are excluded."""
import argparse, json, os, platform, resource, statistics, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE / "benchmarks" / "MQTBench"
CASES = {
    "qft16": ("qft_nativegates_ibm_qiskit_opt0_16.qasm", "proportional", True),
    "grover4": ("grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", True),
    "qaoa7": ("qaoa_nativegates_ibm_qiskit_opt0_7.qasm", "proportional", False),
}
PREFIX = "QUPRS_SAMPLE="

def one(args):
    if hasattr(os, "sched_getaffinity"):
        cpus = sorted(os.sched_getaffinity(0))[:2]
        os.sched_setaffinity(0, cpus)
    import QuPRS
    from QuPRS import check_equivalence
    from qiskit import QuantumCircuit
    if args.case in ("identity", "x", "z"):
        a = QuantumCircuit(1)
        b = QuantumCircuit(1)
        if args.case != "identity":
            getattr(b, args.case)(0)
        expected = "equivalent" if args.case == "identity" else "not_equivalent"
        kwargs = dict(method="wmc_only", strategy="Difference")
    else:
        name, strategy, switch = CASES[args.case]
        a, b = ROOT / name, ROOT / "h,ry,rz,cx" / name
        if switch:
            a, b = b, a
        if not a.is_file() or not b.is_file():
            raise RuntimeError("Fixture missing: " + str((a, b)))
        expected = "equivalent"
        kwargs = dict(method="hybrid", strategy=strategy)
    t = time.perf_counter_ns()
    result = check_equivalence(a, b, backend=args.backend, tool_name=args.solver, timeout=120, **kwargs)
    elapsed = (time.perf_counter_ns() - t) / 1e9
    status = result.equivalent
    correct = status in ("equivalent", "equivalent*") if expected == "equivalent" else status == expected
    record = dict(case=args.case, backend=args.backend, solver=args.solver, status=status,
                  correct=correct, wall_seconds=elapsed, pathsum_time=result.pathsum_time,
                  cnf_time=result.to_DIMACS_time, solver_time=result.tool_time,
                  wmc_time=result.wmc_time, peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  module=str(Path(QuPRS.__file__).resolve()), python=sys.version.split()[0])
    print(PREFIX + json.dumps(record, default=str, sort_keys=True), flush=True)
    if not correct and not args.allow_invalid_base:
        raise RuntimeError("Incorrect candidate or valid-workload classification: " + str(record))

def subprocess_sample(interpreter, case, backend, solver, bad_baseline=False):
    cmd = [interpreter, str(Path(__file__).resolve()), "--sample", "--case", case, "--backend", backend, "--solver", solver]
    if bad_baseline:
        cmd += ["--allow-invalid-base"]
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    p = subprocess.run(cmd, cwd=os.getenv("RUNNER_TEMP", "/tmp"), env=env,
                       text=True, capture_output=True, timeout=180)
    entries = [v[len(PREFIX):] for v in p.stdout.splitlines() if v.startswith(PREFIX)]
    if p.returncode or len(entries) != 1:
        raise RuntimeError(f"{case}/{backend}/{solver} status {p.returncode}: {p.stdout[-500:]} {p.stderr[-2500:]}")
    return json.loads(entries[0])

def main(args):
    versions = {"A":args.base_python, "B":args.head_python}
    if not all(Path(p).is_file() for p in versions.values()):
        raise RuntimeError("Missing installed Python env")
    results, comparisons, edge = [], [], []
    for solver in ("gpmc", "ganak"):
        for backend in ("python", "rust"):
            for case in ("identity", "x", "z"):
                for label in ("A","B"):
                    item = subprocess_sample(versions[label], case, backend, solver, label=="A")
                    edge.append(dict(variant=label, **item))
                    if label == "B" and not item["correct"]:
                        raise RuntimeError("Candidate correctness failure: "+str(item))
    workloads = [(case,"rust",solver) for case in CASES for solver in ("gpmc","ganak")]
    workloads += [("grover4","python",solver) for solver in ("gpmc","ganak")]
    for case,backend,solver in workloads:
        for label in ("A","B"):
            subprocess_sample(versions[label],case,backend,solver)
        observations = []
        for _ in range(2):
            for label in ("A","B","B","A"):
                item=subprocess_sample(versions[label],case,backend,solver)
                observations.append(dict(variant=label,**item))
                results.append(dict(variant=label,**item))
        a=[o["wall_seconds"] for o in observations if o["variant"]=="A"]
        b=[o["wall_seconds"] for o in observations if o["variant"]=="B"]
        ma,mb=statistics.median(a),statistics.median(b)
        mad=lambda xs: statistics.median(abs(x-statistics.median(xs)) for x in xs)
        uncertainty=mad(a)+mad(b)
        significant=mb>ma*1.05 and mb-ma>max(.01,3*uncertainty)
        row=dict(case=case,backend=backend,solver=solver,base_median_s=ma,head_median_s=mb,
                 ratio=mb/ma,uncertainty_mad_s=uncertainty,significant_regression=significant,
                 base_samples=a,head_samples=b,solver_invoked_a=[o["solver_time"] is not None for o in observations if o["variant"]=="A"],
                 solver_invoked_b=[o["solver_time"] is not None for o in observations if o["variant"]=="B"])
        comparisons.append(row)
        print("COMPARISON: "+json.dumps(row,sort_keys=True),flush=True)
    host=dict(uname=platform.uname()._asdict(),cpu=Path("/proc/cpuinfo").read_text().split("model name")[1].splitlines()[0] if Path("/proc/cpuinfo").exists() else None)
    report=dict(base_sha=args.base_sha,head_sha=args.head_sha,host=host,
                oracle_edges=edge,raw_samples=results,comparisons=comparisons,
                significant_regressions=[r for r in comparisons if r["significant_regression"]],
                note="real wall time inside check_equivalence, paired ABBA on same host with fixed two-core CPU affinity; baseline incorrect results excluded")
    Path(args.output).write_text(json.dumps(report,indent=2,sort_keys=True,default=str))
    if report["significant_regressions"]:
        raise RuntimeError("NO-GO: significant real-wall-time regressions; see report")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--sample",action="store_true")
    p.add_argument("--allow-invalid-base",action="store_true")
    p.add_argument("--case",default="qft16")
    p.add_argument("--solver",default="gpmc")
    p.add_argument("--backend",default="rust")
    p.add_argument("--base-python")
    p.add_argument("--head-python")
    p.add_argument("--base-sha")
    p.add_argument("--head-sha")
    p.add_argument("--output",default="wmc-ab.json")
    a=p.parse_args()
    one(a) if a.sample else main(a)
