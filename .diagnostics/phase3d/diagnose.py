#!/usr/bin/env python3
"""Isolated diagnostic builds (not timed as Release A/B)."""
import os, subprocess, pathlib
root=pathlib.Path(os.environ["QUPRS_ATTR_ROOT"])
out=root/"results/diagnostics"
out.mkdir(parents=True,exist_ok=True)
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
for case in ("qft16","qaoa7","ghz32","graphstate16","grover4"):
    for solver in ("gpmc","ganak"):
        for variant in ("A","AH"):
            stem=f"{case}-{solver}-{variant}"
            env=os.environ.copy()
            env["QUPRS_TRACE_PATH"]=str(out/(stem+".jsonl"))
            cmd=["/usr/bin/time","-v","-o",str(out/(stem+".time.txt")),str(root/"results/bin"/("diag-"+variant)),case,solver,"0"]
            result=subprocess.run(cmd,env=env,text=True,capture_output=True,timeout=600)
            (out/(stem+".stdout")).write_text(result.stdout)
            (out/(stem+".stderr")).write_text(result.stderr)
            if result.returncode:raise RuntimeError((stem,result.returncode,result.stderr))
            print("TRACE",stem,flush=True)
