"""QOO-157 P2 GPMC native components/cache/TD width/RSS, no timing.

Source-fixed original and independently signed-SCC reduced weighted CNFs.
Use only official CodSpeed from P0 for timing. The /usr/bin/time GNU wrapper
emits only max resident-set KB, not wallclock performance.
"""
from __future__ import annotations
from decimal import Decimal,localcontext
from fractions import Fraction
from hashlib import sha256
import argparse
import json
from pathlib import Path
import re
import subprocess

from gpmc_td_ablation import COMPLEX,COUNT
from gpmc_vs_td_factorial import close_enough

CASES=("grover4_eq","qaoa7_neq","qpeexact8_eq","qft16_eq")
NATIVE_COUNTERS=(
    "conflicts","decisions","propagations",
    "Components","Split","Cache lookup","Cache hit","Cache reduce",
)
NATIVE=re.compile(r"(?m)^c o (.+?)\s+=\s+(\d+)\b")
RSS=re.compile(r"(?m)^QOO157_MAX_RSS_KB=(\d+)\s*$")
TD_HEADER=re.compile(r"(?m)^s td (\d+) (\d+) (\d+)\s*$")
PRIMAL=re.compile(r"Primal graph: nodes\s+(\d+), edges\s+(\d+)")


def inspect(binary,source,td,tdfile):
    if td and tdfile.exists():
        tdfile.unlink()
    cmd=[
        "/usr/bin/time","-f","QOO157_MAX_RSS_KB=%M",
        binary,"-mode=1","-prec=38","-vs=1","-cs=4000",
        "-td" if td else "-no-td",
    ]
    if td:
        tdfile.parent.mkdir(parents=True,exist_ok=True)
        cmd.append("-tdout="+str(tdfile.resolve()))
    cmd.append(str(source))
    cp=subprocess.run(cmd,capture_output=True,text=True,timeout=42)
    if cp.returncode:
        raise RuntimeError(f"GPMC P2 child rc={cp.returncode}: {cp.stderr[:280]}")
    m=COUNT.findall(cp.stdout)
    if len(m)!=1:raise ValueError("exactly one GPMC WMC output required")
    c=COMPLEX.fullmatch(m[0].strip())
    if not c:raise ValueError("invalid GPMC complex count")
    val=tuple(Decimal(v) for v in c.groups())
    if not all(v.is_finite() for v in val):raise ValueError("nonfinite GPMC WMC")
    rss=RSS.findall(cp.stderr)
    if len(rss)!=1:raise ValueError("peak RSS marker missing")
    found={key:int(value) for key,value in NATIVE.findall(cp.stdout)}
    for key in NATIVE_COUNTERS:
        if key not in found:
            raise ValueError(f"GPMC native metric missing: {key}: {sorted(found)}")
    flowed="FlowCutter is running..." in cp.stdout
    skipped="skip td" in cp.stdout
    ignored="ignore td" in cp.stdout
    if not td and flowed:
        raise ValueError("TD off but FlowCutter ran")
    # The paired TD-off run reuses the TD-on file path as a locator.
    # Never mistake that retained TD-on native artifact for a TD-off result.
    if td and tdfile.exists():
        header=TD_HEADER.findall(tdfile.read_text())
        if len(header)!=1:raise ValueError("TD file without correct width header")
        bags,max_bag,nvars=map(int,header[0])
        width={"bags":bags,"bag_size":max_bag,
               "native_td_width":max_bag-1,"nodes":nvars,
               "td_file_sha256":sha256(tdfile.read_bytes()).hexdigest()}
    else:
        width=None
    primal=PRIMAL.search(cp.stdout)
    return {
        "real":str(val[0]),"imag":str(val[1]),
        "native_counts":{k:found[k] for k in NATIVE_COUNTERS},
        "peak_rss_kb_from_gnu_time_maxresident":int(rss[0]),
        "td_requested":td,"FlowCutter_started":flowed,
        "td_skipped":skipped,"td_ignored":ignored,
        "native_td":width,
        "primal_graph":({"nodes":int(primal.group(1)),"edges":int(primal.group(2))}
                        if primal else None),
        "gpmc_stdout_sha256":sha256(cp.stdout.encode()).hexdigest(),
        "is_structural_and_memory_diagnostic_not_speed":True,
    }


def audit(binary,orig,red,source_report,manifest_file,td_dir,out):
    a=json.loads(source_report.read_text())
    manifest=json.loads(manifest_file.read_text())
    if a.get("complete") is not True or manifest.get("status")!=(
        "SOURCE_EXACT_REDUCTION_READY_FOR_SOLVER_COUNT_SCREEN"
    ):
        raise ValueError("original/reduced science not admitted")
    report={
        "status":"INCOMPLETE",
        "pinned_gpmc_gitlink":"a1bda3489e959d3695b6798d327c5a1fc1bed305",
        "gpmc_binary_sha256":sha256(Path(binary).read_bytes()).hexdigest(),
        "precision_digits":38,"mpfr_bits":127,"cache_mb":4000,
        "official_performance_evidence":"41846122379",
        "no_performance_measurements_in_this_run":True,
        "cases":{}
    }
    for case in CASES:
        source=a["cases"][case]
        reference=source["precision_pairs"]["38"]["observations"]["gpmc-38"]
        with localcontext() as ctx:
            ctx.prec=110
            oracle=tuple(Decimal(Fraction(reference[k]).numerator)/
                         Decimal(Fraction(reference[k]).denominator)
                         for k in ("real","imag"))
        row={"variants":{}}
        report["cases"][case]=row
        for mode,directory,field in (
            ("original",orig,"source_sha256"),
            ("reduced",red,"reduced_sha256")
        ):
            file=directory/(case+".cnf")
            digest=sha256(file.read_bytes()).hexdigest()
            if digest!=manifest["cases"][case][field]:
                raise ValueError("source/reduced CNF SHA mismatch")
            for td in (True,False):
                name=f"{mode}_{'td_on' if td else 'td_off'}"
                tdfile=td_dir/f"{case}_{mode}_td.td"
                v=inspect(str(binary),file,td,tdfile)
                ok,delta,bound=close_enough((
                    Decimal(v["real"]),Decimal(v["imag"])),oracle)
                v.update({"cnf_sha256":digest,
                          "count_screen_status":("COUNT_CONCORDANT_UNCERTIFIED" if ok else "FAILED"),
                          "count_screen_delta":delta,"count_screen_bound":bound})
                row["variants"][name]=v
                out.parent.mkdir(parents=True,exist_ok=True)
                out.write_text(json.dumps(report,indent=2)+"\n")
                if not ok:raise ValueError(f"count mismatch {case}/{name}")
    report["status"]="GPMC_NATIVE_COMPONENT_CACHE_TD_RSS_SCIENCE_PASS"
    out.write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for key in ("binary","original","reduced","original_science","manifest","td_dir","out"):
        p.add_argument("--"+key.replace("_","-"),type=Path,required=True)
    a=p.parse_args()
    report=audit(a.binary,a.original,a.reduced,a.original_science,
                 a.manifest,a.td_dir,a.out)
    print(json.dumps({"status":report["status"],
        "counts":{c:{n:{"cache_hits":x["native_counts"]["Cache hit"],
                          "components":x["native_counts"]["Components"],
                          "split":x["native_counts"]["Split"],
                          "RSS_kb":x["peak_rss_kb_from_gnu_time_maxresident"],
                          "TD_width":x["native_td"]["native_td_width"] if x["native_td"] else None}
                     for n,x in row["variants"].items()}
                  for c,row in report["cases"].items()}}))
