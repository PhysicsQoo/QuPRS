#!/usr/bin/env python3
"""Paired same-host current-dev vs exact candidate, plain Release only."""
import argparse, hashlib, json, os, pathlib, platform, statistics, subprocess, time

PAIRS = [("A", "AH", "current-dev-to-hoist")]
CASES = ["qft16", "qaoa7", "ghz32", "graphstate16", "grover4"]
SOLVERS = ["gpmc", "ganak"]
FIELDS = ["strategy_seconds", "engine_total_seconds", "outer_seconds",
          "dimacs_seconds", "solver_seconds", "wmc_seconds",
          "wmc_encoding_and_management_seconds", "process_peak_rss_kib"]

def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()

def stats(v):
    m = statistics.median(v)
    return {"n": len(v), "median": m, "mad": statistics.median(abs(x-m) for x in v), "raw": v}

def call(*cmd):
    p = subprocess.run(cmd, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError((cmd, p.returncode, p.stderr))
    return p.stdout.strip()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--binary-dir", required=True, type=pathlib.Path)
    p.add_argument("--output", required=True, type=pathlib.Path)
    p.add_argument("--case-root", required=True, type=pathlib.Path)
    p.add_argument("--blocks", type=int, default=5)
    p.add_argument("--warmups", type=int, default=1)
    p.add_argument("--timeout", type=int, default=600)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    affinity = sorted(os.sched_getaffinity(0))
    cpu = affinity[0]
    os.sched_setaffinity(0, {cpu})
    env = os.environ.copy()
    env.update(QUPRS_CASE_ROOT=str(args.case_root.resolve()), OMP_NUM_THREADS="1",
               OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    env.pop("QUPRS_TRACE_PATH", None)
    variants = ["A", "AH"]
    binaries = {v: (args.binary_dir / v).resolve() for v in variants}
    solvers = {}
    for solver in SOLVERS:
        path = env.get("QUPRS_" + solver.upper() + "_PATH")
        if not path:
            raise RuntimeError("Missing explicit solver binary path: " + solver)
        solvers[solver] = {"path": path, "sha256": sha(path)}
    manifest = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
                "uname": call("uname", "-a"), "lscpu": call("lscpu"),
                "python": platform.python_version(), "rustc": call("rustc", "-Vv"),
                "cpu_affinity_original": affinity, "cpu_affinity_used": [cpu],
                "pairs": PAIRS, "cases": CASES, "solvers": solvers,
                "binaries": {v: {"sha256": sha(binaries[v]), "path": str(binaries[v])} for v in variants},
                "qasm_sha256": {str(x.relative_to(args.case_root)): sha(x) for x in args.case_root.rglob("*.qasm")},
                "blocks": args.blocks, "warmups_per_process": args.warmups,
                "note": "Engine walltime includes tool-stage. CodSpeed Simulation not measured here."}
    (args.output / "environment.json").write_text(json.dumps(manifest,indent=2)+"\n")
    rows = []
    with (args.output / "samples.jsonl").open("w",buffering=1) as raw, (args.output / "stderr.log").open("w",buffering=1) as err:
        for case in CASES:
            for solver in SOLVERS:
                for base, candidate, label in PAIRS:
                    for block in range(args.blocks):
                        order = [base,candidate,candidate,base] if block%2==0 else [candidate,base,base,candidate]
                        group = []
                        for pos, variant in enumerate(order):
                            cmd = [str(binaries[variant]),case,solver,str(args.warmups)]
                            meta = {"case":case,"solver":solver,"comparison":label,
                                    "base_variant":base,"candidate_variant":candidate,"block":block,
                                    "position":pos,"variant":variant,"order":"ABBA" if block%2==0 else "BAAB",
                                    "utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"command":cmd,
                                    "loadavg":os.getloadavg()}
                            result = subprocess.run(cmd,env=env,text=True,capture_output=True,timeout=args.timeout)
                            err.write(json.dumps(meta)+"\n"+result.stderr+"\n")
                            try:
                                row = json.loads(result.stdout.strip().splitlines()[-1])
                            except (IndexError,ValueError):
                                raw.write(json.dumps({**meta,"stdout":result.stdout,"returncode":result.returncode,"error":"bad output"})+"\n")
                                raise
                            data = {**meta,**row,"returncode":result.returncode}
                            raw.write(json.dumps(data)+"\n")
                            rows.append(data)
                            group.append(data)
                            if result.returncode or row["status"] not in ("equivalent","equivalent*"):
                                raise RuntimeError("Equivalence failure "+str(data))
                        if len({x["status"] for x in group})!=1:
                            raise RuntimeError("A/B status mismatch "+str(group))
                        if label == "current-dev-to-hoist":
                            if len({(x["final_path_vars"],x["final_terms"]) for x in group})!=1:
                                raise RuntimeError("Hoist changed final state "+str(group))
                        print(case,solver,label,block+1,"/",args.blocks,flush=True)
    summary = []
    for case in CASES:
        for solver in SOLVERS:
            for base, candidate, label in PAIRS:
                group = [x for x in rows if (x["case"],x["solver"],x["comparison"])==(case,solver,label)]
                metrics, paired = {}, {}
                for key in FIELDS:
                    aa = [r[key] for r in group if r["variant"]==base and r[key] is not None]
                    bb = [r[key] for r in group if r["variant"]==candidate and r[key] is not None]
                    metrics[key]={"base":stats(aa) if aa else None,"candidate":stats(bb) if bb else None}
                    ratios=[]
                    for block in range(args.blocks):
                        a=[r[key] for r in group if r["variant"]==base and r["block"]==block and r[key] is not None]
                        b=[r[key] for r in group if r["variant"]==candidate and r["block"]==block and r[key] is not None]
                        if a and b and statistics.median(a)>0:
                            ratios.append(statistics.median(b)/statistics.median(a))
                    paired[key]=stats(ratios) if ratios else None
                summary.append({"case":case,"solver":solver,"comparison":label,"base":base,"candidate":candidate,
                                "sample_count":len(group),"metrics":metrics,"paired_block_ratios":paired})
    (args.output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    md=["| Case | Solver | Comparison | Strategy ratio | Engine total ratio |",
        "|---|---|---|---:|---:|"]
    for x in summary:
        strategy=x["paired_block_ratios"]["strategy_seconds"]
        total=x["paired_block_ratios"]["engine_total_seconds"]
        md.append(f'| {x["case"]} | {x["solver"]} | {x["comparison"]} | {strategy["median"]:.4f} ± {strategy["mad"]:.4f} | {total["median"]:.4f} ± {total["mad"]:.4f} |')
    (args.output/"summary.md").write_text("\n".join(md)+"\n")
    print(f"VALIDATED: {len(rows)} samples; {len(summary)} comparisons; 0 verification failures",flush=True)
    print("\n".join(md),flush=True)

if __name__=="__main__":
    main()
