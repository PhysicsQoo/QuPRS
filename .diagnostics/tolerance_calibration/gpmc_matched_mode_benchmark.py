"""Fixed-runner paired GPMC default vs --ddnnf output (research only).

Reuse source-pinned identical CNFs from prior immutable artifact. This is
NOT production double-solve. Randomized run order is forbidden: predeclared
alternating order, same runner, same binary, three replicates per mode.
Measure time(1) real seconds and MaxRSS kB. Check count text exactly.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import statistics
sys.path.insert(0,str(Path(__file__).resolve().parent))
from QuPRS.utils import WMC
from QuPRS.utils.precision_count import parse_printed_solver_output

CASES=("qpeexact8-baseline","qpeexact8-self_negative",
       "qft16-baseline","qft16-self_negative")
ORDER=(("default","ddnnf"),("ddnnf","default"),("default","ddnnf"))

def main(source,out):
    out.mkdir(parents=True,exist_ok=True)
    lines=[];summaries=[]
    with WMC("gpmc") as exe:
        for case in CASES:
            path=source/(case+".cnf")
            assert path.is_file(),path
            original_hash=hashlib.sha256(path.read_bytes()).hexdigest()
            results={}
            for rep,order in enumerate(ORDER):
                for mode in order:
                    tag=f"{case}-{mode}-rep{rep}"
                    nnf=out/(tag+".nnf")
                    args=[str(exe),"-mode=1","-prec=90"]
                    if mode=="ddnnf":args+=["-ddnnf",f"-nnfout={nnf}"]
                    args.append(str(path))
                    command=["/usr/bin/time","-f","METRIC real=%e rss_kb=%M"]+args
                    proc=subprocess.run(command,capture_output=True,text=True,
                                        timeout=65,check=False)
                    (out/(tag+".stdout")).write_text(proc.stdout)
                    (out/(tag+".stderr")).write_text(proc.stderr)
                    if proc.returncode:raise AssertionError((tag,proc.returncode,proc.stderr[-300:]))
                    sample=re.search(r"METRIC real=([0-9.]+) rss_kb=(\d+)",proc.stderr)
                    if not sample:raise AssertionError(("time metrics missing",tag))
                    count=parse_printed_solver_output(proc.stdout)
                    count_key=(count.real,count.imag)
                    results.setdefault(mode,[]).append(count_key)
                    row={
                        "case":case,"mode":mode,"replicate":rep,
                        "cnf_sha256":original_hash,
                        "native_elapsed_seconds":float(sample.group(1)),
                        "peak_rss_kb":int(sample.group(2)),
                        "nnf_size_bytes":nnf.stat().st_size if nnf.exists() else None,
                        "native_stdout_sha256":hashlib.sha256(proc.stdout.encode()).hexdigest(),
                        "printed_complex_pair":[str(count.real),str(count.imag)],
                    }
                    lines.append(row)
                    print("PAIRED_GPMC_SAMPLE "+json.dumps(row,sort_keys=True),flush=True)
            if len(set(results["default"]+results["ddnnf"]))!=1:
                raise AssertionError(("GPMC modes printed different counts",case))
            default_rows=[r for r in lines if r["case"]==case and r["mode"]=="default"]
            nnf_rows=[r for r in lines if r["case"]==case and r["mode"]=="ddnnf"]
            t0=statistics.median(x["native_elapsed_seconds"] for x in default_rows)
            t1=statistics.median(x["native_elapsed_seconds"] for x in nnf_rows)
            m0=statistics.median(x["peak_rss_kb"] for x in default_rows)
            m1=statistics.median(x["peak_rss_kb"] for x in nnf_rows)
            summ={
                "case":case,"samples_per_mode":3,
                "median_default_seconds":t0,
                "median_ddnnf_seconds":t1,
                "median_time_ratio_ddnnf_over_default":(t1/t0 if t0>0 else None),
                "median_default_peak_rss_kb":m0,
                "median_ddnnf_peak_rss_kb":m1,
                "median_memory_ratio_ddnnf_over_default":(m1/m0 if m0>0 else None),
                "dnnf_bytes_median":statistics.median(x["nnf_size_bytes"] for x in nnf_rows),
                "all_six_solver_outputs_identical_as_exact_decimal":True,
                "same_host_one_run_only":True,
                "independent_fixed_environment_repeatability_outside_run_not_proven":True,
            }
            summaries.append(summ)
            print("PAIRED_GPMC_SUMMARY "+json.dumps(summ,sort_keys=True),flush=True)
    (out/"paired-gpmc-mode-comparison.json").write_text(
        json.dumps({"source_artifact_pinned":True,"results":summaries,
                    "samples":lines,"production_solver_replays":0,
                    "study_only_extra_solvers":True},sort_keys=True,indent=2)+"\n")
    assert len(lines)==24
    print("PAIRED_GPMC_ALL_24_NATIVE_COUNTS_CONSISTENT",flush=True)

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--artifact-folder",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    opts=a.parse_args();main(opts.artifact_folder,opts.output)
