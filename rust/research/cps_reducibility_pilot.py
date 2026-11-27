#!/usr/bin/env python3
"""Isolated native paired pilot; reuse existing C3 exact packed GPMC worker."""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

from autoq_c3_pilot import CASES

CAP = 4.0
CASES_PILOT = ("grover03", "mogrover03", "grover04", "mogrover04",
               "grover03-relative", "mogrover03-relative")
ARMS = (("wmc", "0"), ("wmc", "1"), ("hybrid-support", "0"),
        ("hybrid-support", "1"), ("hybrid-direct", "0"),
        ("structural-factor", "0"))

def run(args, folder, env):
    folder.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    p = subprocess.run(["/usr/bin/time", "-f", "%e %M", "-o", str(folder/"resource.txt"),
                        "timeout", "--kill-after=1s", str(CAP), *args],
                       env=env, capture_output=True, text=True)
    elapsed = time.monotonic()-start
    (folder/"stdout").write_text(p.stdout)
    (folder/"stderr").write_text(p.stderr)
    resource = (folder/"resource.txt").read_text().split() if (folder/"resource.txt").exists() else []
    return p, dict(rc=p.returncode, wall_s=elapsed,
                   rss_kib=int(resource[-1]) if resource and resource[-1].isdigit() else None)

def main():
    eq, c3, solver, out = map(lambda p:pathlib.Path(p).resolve(), sys.argv[1:5])
    out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, QUPRS_GPMC_PATH=str(solver))
    rows, errors = [], []
    for variant in ("source", "wrong-output"):
        for mode in ("rr", "wmc", "hybrid"):
            folder = out/f"eq-03-0-{variant}-{mode}"
            p, row = run([str(eq), "--exact", "original_eq_covariance_arm", "--ignored", "--nocapture"],
                         folder, dict(env, CPS_ORBIT_SIZE="03", CPS_ORBIT_GEN="0",
                         CPS_ORBIT_VARIANT=variant, CPS_ORBIT_MODE=mode, CPS_ORBIT_SECONDS="3"))
            row.update(kind="eq", variant=variant, mode=mode)
            lines = [l.split("CPS_ORBIT_RESULT ",1)[1] for l in p.stdout.splitlines()
                     if "CPS_ORBIT_RESULT " in l]
            row["result"] = lines[-1] if lines else None
            row["status"] = ("TIMEOUT" if p.returncode in (124,137) else
                             "ERROR" if p.returncode or not lines else
                             lines[-1].split()[0].split("=",1)[1])
            if row["status"] == "ERROR": errors.append(str(folder))
            rows.append(row)
            print("CPS_REDUCIBILITY_ARM "+json.dumps(row), flush=True)
    worker = pathlib.Path(__file__).resolve().with_name("autoq_c3_pilot.py")
    for period in range(2):
        for case in (CASES_PILOT if period==0 else CASES_PILOT[::-1]):
            for mode, fused in (ARMS if period==0 else ARMS[::-1]):
                folder = out/f"{period}-{case}-{mode}-{fused}"
                p, row = run([sys.executable, str(worker), "--arm", str(c3), str(solver),
                              case, mode, str(folder)], folder, dict(env, AQ_CPS_FUSED=fused))
                row.update(kind="c3", period=period, case=case, mode=mode, fused=fused)
                if p.returncode in (124,137):
                    row["status"] = "TIMEOUT"
                elif p.returncode:
                    row["status"] = "ERROR"
                    errors.append(str(folder))
                else:
                    try:
                        native = json.loads(p.stdout)
                        row["native"] = native
                        row["status"] = native["verdict"]
                        assert row["status"] in ("UNKNOWN", CASES[case])
                    except (ValueError, AssertionError, KeyError):
                        row["status"] = "ERROR"
                        errors.append(str(folder))
                # Partial logs survive hard timeouts. Never interpret missing queries as zero.
                log = folder/"native.log"
                lines = log.read_text().splitlines() if log.exists() else []
                row["residual"] = [l.split("AQ_CPS_RESIDUAL ",1)[1] for l in lines if "AQ_CPS_RESIDUAL " in l]
                row["encoding"] = [l.split("AQ_CPS_ENCODING ",1)[1] for l in lines if "AQ_CPS_ENCODING " in l]
                sl = folder/"solver.jsonl"
                row["solver_records"] = [json.loads(l) for l in sl.read_text().splitlines()
                                         if l.strip().endswith("}")] if sl.exists() else []
                rows.append(row)
                print("CPS_REDUCIBILITY_ARM "+json.dumps({k:v for k,v in row.items() if k!="solver_records"}),flush=True)
    pairs=[]
    for period in range(2):
        for case in CASES_PILOT:
            for mode in ("wmc","hybrid-support"):
                a,b=[next(r for r in rows if r["kind"]=="c3" and r["period"]==period
                          and r["case"]==case and r["mode"]==mode and r["fused"]==f)
                     for f in ("0","1")]
                # Only completed arms with the same exact query sequence are comparable.
                aa,bb=a["solver_records"],b["solver_records"]
                exact=bool(aa) and len(aa)==len(bb) and all(
                    x.get("status")==y.get("status")=="EXACT" for x,y in zip(aa,bb))
                definite=a["status"]==b["status"] and a["status"] in ("PROVED","REFUTED")
                same_residual=bool(a["residual"]) and a["residual"]==b["residual"]
                same_bins=exact and all(x["bins"]==y["bins"] for x,y in zip(aa,bb))
                if definite and exact and (not same_residual or not same_bins):
                    errors.append(f"paired mismatch {period} {case} {mode}")
                pairs.append(dict(period=period,case=case,mode=mode,
                                  statuses=[a["status"],b["status"]],
                                  same_residual_metrics=same_residual, same_bins=same_bins,
                                  comparable=definite and same_residual and same_bins,
                                  wall_s=[a["wall_s"],b["wall_s"]]))
    summary=dict(rows=rows,pairs=pairs,errors=errors,
                 sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (eq,c3,solver)})
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("CPS_REDUCIBILITY_SUMMARY "+json.dumps(dict(arms=len(rows),pairs=len(pairs),
          comparable=sum(p["comparable"] for p in pairs),errors=errors)),flush=True)
    assert not errors, errors

if __name__=="__main__":
    main()
