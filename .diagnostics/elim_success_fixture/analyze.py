#!/usr/bin/env python3
"""Fail-closed validation and summary of matched Rust Elim fixture raw logs."""
import collections, hashlib, json, os, pathlib, platform, statistics, subprocess, sys

OUT = pathlib.Path("elim-fixture-results")
PREFIX = "ELIM_FIXTURE_JSON "
K, D, DEG, ROUNDS = (1,2,4,8), (8,16,32), (1,2,4), 24

def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

def proc(*cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return {"exit":p.returncode, "stdout":p.stdout[-10000:], "stderr":p.stderr[-10000:]}

def main():
    OUT.mkdir(exist_ok=True)
    logfile = OUT / "rust-test.log"
    lines = logfile.read_text().splitlines()
    rows = [json.loads(line.partition(PREFIX)[2]) for line in lines if PREFIX in line]
    errors = []
    expected = {(r,k,d,degree,s) for r in range(ROUNDS)
                for k in K for d in D for degree in DEG for s in (False,True)}
    count = collections.Counter((r["round"],r["k"],r["d"],r["degree"],r["success"]) for r in rows)
    if count != collections.Counter({k:1 for k in expected}):
        errors.append("MISSING_DUPLICATE_OR_UNKNOWN_RECORDS")
    if "test result: ok." not in "\n".join(lines):
        errors.append("RUST_TEST_SUCCESS_MARKER_MISSING")
    for r in rows:
        if not (r["v"]==64 and r["l"]==r["d"]*r["degree"]
                and r["w_est"]==(r["k"]-1)*r["l"]
                and r["removed"]==int(r["success"])
                and type(r["elapsed_ns"]) is int and r["elapsed_ns"]>=0):
            errors.append("INVALID_SAMPLE")
            break
    designs = []
    for k in K:
        for d in D:
            for degree in DEG:
                pair = {s: {r["round"]:r["elapsed_ns"] for r in rows
                            if (r["k"],r["d"],r["degree"],r["success"])
                            == (k,d,degree,s)} for s in (False,True)}
                if set(pair[False]) != set(range(ROUNDS)) or set(pair[True]) != set(range(ROUNDS)):
                    errors.append("INCOMPLETE_PAIRED_DESIGN")
                    continue
                ratios = [pair[True][i]/max(1,pair[False][i]) for i in range(ROUNDS)]
                designs.append({"k":k,"d":d,"degree":degree,"l":d*degree,"v":64,
                                "success_median_ns":statistics.median(pair[True].values()),
                                "failure_median_ns":statistics.median(pair[False].values()),
                                "median_paired_success_failure_ratio":statistics.median(ratios),
                                "rounds":ROUNDS})
    manifest = {"schema":"quprs-elim-matched-success-failure-v1",
                "head":proc("git","rev-parse","HEAD"),
                "rustc":proc("rustc","--version"), "cargo":proc("cargo","--version"),
                "cpu":proc("lscpu"), "python":platform.python_version(),
                "affinity":sorted(os.sched_getaffinity(0)),
                "rust_source_sha256":sha("rust/pathsum/src/diagnostics.rs"),
                "analyzer_sha256":sha(__file__),
                "rust_log_sha256":sha(logfile),
                "factors":{"k":K,"d":D,"degree":DEG,"v":64,"rounds":ROUNDS},
                "scope":"synthetic controlled rule-only Elim with direct candidate slices"}
    write(OUT/"environment.json",manifest)
    (OUT/"observations.jsonl").write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in rows))
    status = "PASS_DATA_COLLECTION" if not errors and len(rows)==1728 and len(designs)==36 else "INCOMPLETE"
    write(OUT/"summary.json",{"schema":manifest["schema"],"status":status,
        "raw_rows":len(rows),"matched_designs":len(designs),"errors":errors,"designs":designs,
        "limits":["Success/failure pairs match K/L/V/D but differ in phase variable identity.",
                  "Rule-only fixtures bypass candidate discovery and do not model authentic circuits.",
                  "Timer includes Instant/RAII overhead, cache effects and clock granularity.",
                  "24 within-process rounds are not 24 independent structures.",
                  "No performance regression threshold or scheduler inference."]})
    table=["# Synthetic controlled Elim cost", "",f"Status: {status}, records {len(rows)}/1728, designs {len(designs)}/36.",
           "","| K | D | Degree | L | Failure median ns | Success median ns | Paired ratio |",
           "|---:|---:|---:|---:|---:|---:|---:|"]
    table += [f"| {x['k']} | {x['d']} | {x['degree']} | {x['l']} | {x['failure_median_ns']:.1f} | {x['success_median_ns']:.1f} | {x['median_paired_success_failure_ratio']:.3f} |" for x in designs]
    (OUT/"summary.md").write_text("\n".join(table)+"\n")
    print(f"ELIM_FIXTURE_RESULT {status} rows={len(rows)} designs={len(designs)}")
    return 0 if status=="PASS_DATA_COLLECTION" else 2

if __name__ == "__main__":
    sys.exit(main())
