"""P4.6 scoped cooperative safety; no hard in-process isolation claim."""
from concurrent.futures import ThreadPoolExecutor
import gc
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from unittest.mock import patch

import psutil
import rawmocs
from QuPRS.interface.ps2wmc import run_wmc
from QuPRS.utils.solver_adapter import get_solver_adapter
from QuPRS.utils.solver_process import SolverTimeout
from native_adapter import registered_native, NativeFailure
from release_transfer import check_count

ROOT=Path(".p4-safety-evidence")
CNF_SHA="6fb69626195bee5b89ed3503ae8b1b4801d9267e7bd5ff3684af152afcd885e1"
WITNESS_SHA="e59e2741a69dbb13b4f6d0b44562ac689541c4bcf7c43da476006ec8f1b87512"

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ROOT.mkdir(exist_ok=True)
    path,=Path(".p4-safety-input").rglob("*-gpmc.cnf")
    witness,=Path(".p4-safety-input").rglob("prejoin-reference.json")
    assert sha(path)==CNF_SHA and sha(witness)==WITNESS_SHA
    ref=json.loads(witness.read_text())
    assert ref["source_sha256"]==CNF_SHA and ref["bits"]==550
    default=get_solver_adapter("gpmc")
    report=dict(status="IN_PROGRESS",cnf_sha256=CNF_SHA,witness_sha256=WITNESS_SHA,controls={},rss=[])
    def save():(ROOT/"safety.json").write_text(json.dumps(report,indent=2)+"\n")
    def solved():
        observations=[]
        original=rawmocs.solve_file
        def observe(*a,**k):
            result=original(*a,**k);observations.append(result);return result
        with registered_native(130),patch.object(rawmocs,"solve_file",observe):
            value=run_wmc(path,"rawmocs_native",timeout=20,preserve_count=True)
        n,=observations
        assert n.digits==130 and n.precision_bits==432
        row=dict(sat=n.sat,real=str(value.real),imag=str(value.imag),route=n.route)
        check_count(row,ref,100)
        return row
    save()
    # Establish the actual long workload before checking natural cancellation.
    expected=solved()
    start=time.monotonic()
    with registered_native(130):
        try:run_wmc(path,"rawmocs_native",timeout=.01,preserve_count=True)
        except SolverTimeout as e:
            assert isinstance(e.__cause__,rawmocs.SolveError) and e.__cause__.kind=="TIMEOUT"
            report["controls"]["internal_timeout"]=dict(kind=e.__cause__.kind,wall_s=time.monotonic()-start)
        else:raise AssertionError("deadline did not stop actual solve")
    assert solved()==expected
    token=rawmocs.CancellationToken();token.cancel()
    with registered_native(130,token=token):
        try:run_wmc(path,"rawmocs_native",timeout=20,preserve_count=True)
        except NativeFailure as e:
            assert e.kind=="CANCELLED" and not hasattr(e,"count")
            report["controls"]["pre_cancelled"]="CANCELLED"
        else:raise AssertionError("pre-cancelled solve completed")
    token=rawmocs.CancellationToken()
    entering=threading.Event()
    original=rawmocs.solve_file
    def entering_native(*a,**k):
        entering.set()
        return original(*a,**k)
    with registered_native(130,token=token),patch.object(rawmocs,"solve_file",entering_native):
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(run_wmc,path,"rawmocs_native",20,preserve_count=True)
            assert entering.wait(5)
            time.sleep(.05)
            assert not future.done(), "natural solve was not pending"
            start=time.monotonic()
            token.cancel()
            try:future.result(timeout=5)
            except NativeFailure as e:
                assert e.kind=="CANCELLED" and not hasattr(e,"count")
                report["controls"]["pending_call_cancel"]=dict(kind=e.kind,observed_after_s=time.monotonic()-start)
            else:raise AssertionError("cancelled call completed")
    assert solved()==expected
    report["controls"]["reentry"]="WITNESS_PASS";save()
    # Same-process retention screening, after two warm-up calls. RSS is not
    # allocated-live bytes; allocator caching can retain pages legitimately.
    process=psutil.Process()
    for i in range(8):
        assert solved()==expected
        gc.collect()
        report["rss"].append(dict(iteration=i,rss_kib=process.memory_info().rss//1024))
        save()
    values=[r["rss_kib"] for r in report["rss"]]
    baseline=max(values[:2]);growth=max(0,max(values[2:])-baseline)
    report["rss_screen"]=dict(warmup_peak_kib=baseline,max_growth_kib=growth,threshold_kib=32768,
                              status="PASS" if growth<=32768 else "REVIEW")
    assert get_solver_adapter("gpmc") is default
    try:get_solver_adapter("rawmocs_native")
    except ValueError:pass
    else:raise AssertionError("scoped adapter leaked")
    report["status"]="SCOPED_RESOURCE_PASS" if growth<=32768 else "RSS_REVIEW"
    save()
    print("P4_SAFETY_FINAL",json.dumps(report),flush=True)
    assert growth<=32768,"RSS retention screen requires review"
if __name__=="__main__":main()
