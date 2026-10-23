"""Run bounded isolated Python-only verification cases against one checkout."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

CASES = (
    ("identical_empty", ("reduction_rules","hybrid","wmc_only")),
    ("identical_h", ("reduction_rules","hybrid","wmc_only")),
    ("hh_identity", ("reduction_rules","hybrid","wmc_only")),
    ("identity_x", ("reduction_rules","hybrid","wmc_only")),
    ("identity_rz_001", ("reduction_rules","hybrid","wmc_only")),
    ("identity_rz_01", ("reduction_rules","hybrid","wmc_only")),
    ("grover4_transpiled", ("reduction_rules","hybrid")),
)

def git_head(root):
    run = subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                         check=True,capture_output=True,text=True)
    return run.stdout.strip()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--version",choices=("artifact","dev"),required=True)
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--paper-root",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    src=args.source.resolve()
    paper=args.paper_root.resolve()
    out=args.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    expected = ("e928abc47dd15926364ec77905eb0d5dc92ce8cc"
                if args.version=="artifact" else "059aa076670401b733f6a573201f83611107b924")
    head=git_head(src)
    if head!=expected and args.version=="artifact":
        raise RuntimeError("Historical source ref mismatched immutable tag commit")
    if git_head(paper)!="e928abc47dd15926364ec77905eb0d5dc92ce8cc":
        raise RuntimeError("Original benchmark sources not pinned")
    # For dev, this research-only PR can have HEAD above dev; it must not
    # modify current production Python, Rust, or benchmark source.
    if args.version=="dev":
        check=subprocess.run(["git","-C",str(src),"diff","--quiet",expected,"HEAD","--",
                              "src/QuPRS","rust","benchmarks"],
                             capture_output=True)
        if check.returncode!=0:
            raise RuntimeError("Production files changed relative to pinned dev base")
    env=dict(os.environ)
    env["PYTHONPATH"]=str(src/"src")
    env["PYTHONNOUSERSITE"]="1"
    obs=[]
    for case,methods in CASES:
        for method in methods:
            name=case+"-"+method
            filename=out/(name+".json")
            cmd=[sys.executable, str(Path(__file__).with_name("run_case.py").resolve()),
                 "--label",args.version,"--source",str(src),
                 "--paper-root",str(paper),"--case",case,"--method",method,
                 "--output",str(filename)]
            try:
                p=subprocess.run(cmd,env=env,cwd=src,capture_output=True,text=True,timeout=65)
                (out/(name+".stdout")).write_text(p.stdout)
                (out/(name+".stderr")).write_text(p.stderr)
                if filename.is_file():
                    data=json.loads(filename.read_text())
                    if data.get("status")!="RETURNED" or p.returncode!=0:
                        data["collection_outcome"]="OBSERVED_ERROR"
                    else:
                        data["collection_outcome"]="OBSERVED_RETURN"
                    data["subprocess_exit"]=p.returncode
                else:
                    data={"case":case,"method":method,"source_label":args.version,
                          "collection_outcome":"NO_RESULT","exit_code":p.returncode}
            except subprocess.TimeoutExpired as exc:
                data={"case":case,"method":method,"source_label":args.version,
                      "collection_outcome":"EXTERNAL_TIMEOUT","deadline_seconds":65}
            obs.append(data)
            print(json.dumps({"case":case,"method":method,"source":args.version,
                              "outcome":data["collection_outcome"],
                              "verdict":data.get("verdict")}),flush=True)
    summary={
        "version":args.version, "source_sha":head,"historical_reference":git_head(paper),
        "environment":dict(python=sys.version,runner=os.uname().sysname),
        "planned_cases":sum(len(m) for _,m in CASES),
        "returned":sum(x["collection_outcome"]=="OBSERVED_RETURN" for x in obs),
        "errors":sum(x["collection_outcome"]!="OBSERVED_RETURN" for x in obs),
        "results":obs,
        "interpretation":"Observations; errors and timeouts do NOT count as inequivalence.",
    }
    (out/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True,default=str)+"\n")
    return 0 if summary["returned"]==summary["planned_cases"] else 2

if __name__=="__main__":
    raise SystemExit(main())
