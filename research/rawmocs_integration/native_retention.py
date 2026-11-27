"""Linux glibc retention diagnosis; never equate RSS with live allocations."""
from contextlib import nullcontext
import ctypes
from fractions import Fraction
import gc
import hashlib
import json
import os
import statistics
from pathlib import Path
import sys
import time
from unittest.mock import patch

import psutil
import rawmocs
from QuPRS.interface.ps2wmc import run_wmc
from native_adapter import registered_native
from release_transfer import check_count

ROOT=Path(".p4-safety-evidence")
CNF_SHA="6fb69626195bee5b89ed3503ae8b1b4801d9267e7bd5ff3684af152afcd885e1"
REF_SHA="e59e2741a69dbb13b4f6d0b44562ac689541c4bcf7c43da476006ec8f1b87512"
LIMIT=32768

class MallInfo2(ctypes.Structure):
    _fields_=[(k,ctypes.c_size_t) for k in
              ("arena","ordblks","smblks","hblks","hblkhd","usmblks","fsmblks","uordblks","fordblks","keepcost")]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main(arm):
    policy=os.environ.get("P4_ALLOCATOR_POLICY","default")
    assert policy in ("default","fixed-mmap")
    expected_tunable="glibc.malloc.mmap_threshold=131072" if policy=="fixed-mmap" else ""
    assert os.environ.get("GLIBC_TUNABLES", "")==expected_tunable
    assert not any(k in os.environ for k in ("MALLOC_MMAP_THRESHOLD_","MALLOC_TRIM_THRESHOLD_","MALLOC_TOP_PAD_","MALLOC_MMAP_MAX_","MALLOC_ARENA_MAX","LD_PRELOAD"))
    ROOT.mkdir(exist_ok=True)
    path,=Path(".p4-safety-input").rglob("*-gpmc.cnf")
    witness,=Path(".p4-safety-input").rglob("prejoin-reference.json")
    assert sha(path)==CNF_SHA and sha(witness)==REF_SHA
    ref=json.loads(witness.read_text())
    assert ref["source_sha256"]==CNF_SHA and ref["bits"]==550
    libc=ctypes.CDLL("libc.so.6")
    libc.mallinfo2.restype=MallInfo2
    libc.mallinfo2.argtypes=[]
    libc.malloc_trim.argtypes=[ctypes.c_size_t]
    libc.malloc_trim.restype=ctypes.c_int
    proc=psutil.Process()
    def snapshot():
        gc.collect()
        m=libc.mallinfo2()
        p=proc.memory_full_info()
        return dict(rss_kib=p.rss//1024,uss_kib=p.uss//1024,
                    glibc_inuse_kib=m.uordblks//1024,glibc_free_kib=m.fordblks//1024,
                    glibc_mmap_kib=m.hblkhd//1024,glibc_arena_kib=m.arena//1024,
                    glibc_live_proxy_kib=(m.uordblks+m.hblkhd)//1024)
    def solved():
        if arm=="direct":
            result=rawmocs.solve_file(path,digits=130,timeout_ms=20000)
            real,imag=map(Fraction,result.as_decimal())
        else:
            seen=[];old=rawmocs.solve_file
            def observe(*args,**kwargs):
                result=old(*args,**kwargs);seen.append(result);return result
            with registered_native(130),patch.object(rawmocs,"solve_file",observe):
                count=run_wmc(path,"rawmocs_native",timeout=20,preserve_count=True)
            result,=seen;real,imag=count.real,count.imag
        assert result.digits==130 and result.precision_bits==432
        row=dict(sat=result.sat,real=str(real),imag=str(imag),route=result.route)
        check_count(row,ref,100)
        return row
    report=dict(status="IN_PROGRESS",arm=arm,policy=policy,glibc_tunables=expected_tunable,cnf_sha256=CNF_SHA,witness_sha256=REF_SHA,
                initial=snapshot(),rows=[],scope="glibc counters are diagnostic proxies, not allocator-independent live bytes")
    def save():(ROOT/f"retention-{policy}-{arm}.json").write_text(json.dumps(report,indent=2)+"\n")
    save();expected=None
    for i in range(12):
        start=time.monotonic()
        row=solved()
        if expected is None:expected=row
        assert row==expected
        report["rows"].append(dict(iteration=i+1,wall_s=time.monotonic()-start,**snapshot()))
        save()
    report["signature"]=expected
    report["before_trim"]=snapshot()
    report["trim_return"]=libc.malloc_trim(0)
    report["after_trim"]=snapshot()
    # No trim between measured solves. This diagnostic does not change QuPRS.
    report["status"]="COMPLETE";save()

def compare():
    reports={p:{a:json.loads((ROOT/f"retention-{p}-{a}.json").read_text())
                for a in ("direct","adapter")} for p in ("default","fixed-mmap")}
    assert all(r["status"]=="COMPLETE" and len(r["rows"])==12 for group in reports.values() for r in group.values())
    signatures=[r["signature"] for group in reports.values() for r in group.values()]
    assert all(sig==signatures[0] for sig in signatures)
    summary={}
    for policy,group in reports.items():
        summary[policy]={}
        for arm,r in group.items():
            rows=r["rows"]
            def growth(k):
                return max(0,max(x[k] for x in rows[2:])-max(x[k] for x in rows[:2]))
            rss=growth("rss_kib")
            live=growth("glibc_live_proxy_kib")
            post=max(0,r["after_trim"]["rss_kib"]-max(x["rss_kib"] for x in rows[:2]))
            summary[policy][arm]=dict(raw_rss_growth_kib=rss,live_proxy_growth_kib=live,
                post_trim_rss_growth_kib=post,
                max_rss_kib=max(x["rss_kib"] for x in rows),
                median_rss_kib=statistics.median(x["rss_kib"] for x in rows[2:]),
                max_uss_kib=max(x["uss_kib"] for x in rows),
                max_free_arena_kib=max(x["glibc_free_kib"] for x in rows),
                median_wall_s=statistics.median(x["wall_s"] for x in rows[2:]),
                trim_released_rss_kib=r["before_trim"]["rss_kib"]-r["after_trim"]["rss_kib"],
                raw_rss_screen="PASS" if rss<=LIMIT else "REVIEW",
                diagnostic_live_screen="PASS" if live<=LIMIT and post<=LIMIT else "REVIEW")
    for arm,tuned in summary["fixed-mmap"].items():
        baseline=summary["default"][arm]
        tuned["wall_ratio"]=tuned["median_wall_s"]/baseline["median_wall_s"]
        tuned["performance_screen"]="PASS" if tuned["wall_ratio"]<=1.05 else "REVIEW"
        tuned["absolute_rss_screen"]="PASS" if tuned["max_rss_kib"]<=baseline["max_rss_kib"] and tuned["median_rss_kib"]<=baseline["median_rss_kib"] else "REVIEW"
    passed=all(all(t[k]=="PASS" for k in ("raw_rss_screen","diagnostic_live_screen","performance_screen","absolute_rss_screen"))
               for t in summary["fixed-mmap"].values())
    status="ALLOCATOR_POLICY_SCREEN_PASS" if passed else "ALLOCATOR_POLICY_REVIEW"
    out=dict(status=status,threshold_kib=LIMIT,wall_ratio_limit=1.05,summary=summary,
             scope="12 solves per isolated arm/policy; Linux-only diagnostic; no production allocator change or leak-free proof")
    (ROOT/"retention-summary.json").write_text(json.dumps(out,indent=2)+"\n")
    print("P4_ALLOCATOR_POLICY_FINAL",json.dumps(out),flush=True)
    assert passed,"allocator policy requires review; do not admit"

if __name__=="__main__":
    arm=sys.argv[1]
    if arm=="compare":compare()
    else:
        assert arm in ("direct","adapter")
        main(arm)
