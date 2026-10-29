"""Research-only numerical precision follow-up on an exact pinned dev source.

Mode printer: independently check real MPFR binary values against truncated
90-significant-digit stdout; no quantum solver calls.
Mode corpus: resource-bounded *actual* algorithm-family CNF encoding and one
GPMC solve per encountered WMC call; incomplete work is evidence, not a pass.
Mode rust: source-pinned QPEexact8 public Rust/FFI and native stdout capture.

No changes to production RR, GPMC solver, or public classification.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import sys
import tempfile
import time


def emit(out: Path, row: dict):
    line = json.dumps(row, sort_keys=True, default=str)
    with (out / "phase2-observations.jsonl").open("a") as f:
        f.write(line + "\n")
    print("PHASE2_OBSERVATION " + line, flush=True)


def as_fraction_decimal(text: str):
    return Fraction(Decimal(text))


def printer(out: Path, binary: Path):
    proc = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10, check=True)
    (out / "printer-raw-stdout.tsv").write_text(proc.stdout)
    lines = [s.split("\t") for s in proc.stdout.splitlines()]
    head = lines[0]
    if head[:1] != ["PRINTER_PRECISION"]:
        raise AssertionError(head)
    digits, bits = int(head[1]), int(head[2])
    if not (digits == 90 and bits >= 299):
        raise AssertionError((digits, bits))
    assert len(lines[1:]) >= 8
    for item in lines[1:]:
        tag, case, source, printed, mantissa, power = item
        if tag != "PRINTED_VALUE":
            raise AssertionError(item)
        actual_mpfr = Fraction(int(mantissa)) * Fraction(2)**int(power)
        printed_fraction = as_fraction_decimal(printed)
        source_fraction = as_fraction_decimal(source)
        if printed_fraction == 0:
            half = Fraction(0)
        else:
            order = Decimal(printed).adjusted()
            half = Fraction(1, 2) * Fraction(10)**(order-digits+1)
        abs_gap = abs(printed_fraction - actual_mpfr)
        if abs_gap > half:
            raise AssertionError((case, printed, abs_gap, half))
        emit(out, {
            "family": "PINNED_MPFR_PRINTER",
            "case": case, "precision_decimal": digits,
            "precision_bits": bits, "printed_value": printed,
            "printed_vs_exact_binary_mpfr_gap": str(abs_gap),
            "candidate_print_half_unit": str(half),
            "source_decimal_vs_binary_mpfr_gap": str(abs(source_fraction-actual_mpfr)),
            "passes_candidate_enclosure": True,
            "not_solver_arithmetic_certificate": True,
        })
    print("PINNED_PRINTER_EIGHT_CONTROLS_PASS", flush=True)


CASES = {
    "qpeexact8": ("qpeexact_nativegates_ibm_qiskit_opt0_8.qasm", "Proportional"),
    "qft16": ("qft_nativegates_ibm_qiskit_opt0_16.qasm", "Proportional"),
    "graphstate16": ("graphstate_nativegates_ibm_qiskit_opt0_16.qasm", "Naive"),
    "qaoa7": ("qaoa_nativegates_ibm_qiskit_opt0_7.qasm", "Proportional"),
}


def sources(case):
    root=Path.cwd() / "benchmarks" / "MQTBench"
    name,strategy=CASES[case]
    left=root/name
    right=root/"h,ry,rz,cx"/name
    assert left.is_file() and right.is_file(), (left,right)
    hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in (left,right)]
    return left,right,strategy,hashes


def corpus_worker(case, out: Path):
    from QuPRS import check_equivalence
    from QuPRS.interface import ps2wmc
    from QuPRS.utils.gpmc_cnf_metadata import gpmc_cnf_budget_metadata
    from QuPRS.utils.precision_count import classify_printed_distance
    left,right,strategy,hashes = sources(case)
    original_encode=ps2wmc.to_DIMACS
    original_solver=ps2wmc.run_wmc
    state={"calls":0,"cnf":None,"printed":None,"pre_solver_limit":False}
    def capture_encode(*args,**kwargs):
        cnf=original_encode(*args,**kwargs)
        state["cnf"]=cnf
        (out/f"cnf-{case}.cnf").write_text(cnf)
        return cnf
    def capture_solver(*args,**kwargs):
        state["calls"]+=1
        if state["calls"] != 1:
            raise AssertionError("More than one GPMC launch inside WMC stage")
        nvars,_,_ = gpmc_cnf_budget_metadata(state["cnf"])
        # Do not launch an unbounded counting job on thousands of variables.
        if nvars > 250:
            state["pre_solver_limit"]=True
            raise RuntimeError("RESEARCH_RESOURCE_CAP_CNF_VARIABLES_GT_250")
        state["printed"]=original_solver(*args,**kwargs)
        return state["printed"]
    ps2wmc.to_DIMACS=capture_encode
    ps2wmc.run_wmc=capture_solver
    started=time.monotonic()
    try:
        answer=check_equivalence(
            str(left),str(right),backend="python",method="wmc_only",
            strategy=strategy,tool_name="gpmc",timeout=35,
            approximate_distance_tolerance=1e-8,
        )
        verdict=answer.equivalent
        reason=answer.wmc_precision_reason
        model_bound=answer.wmc_numeric_model_bound
        printed_verdict=answer.wmc_printed_verdict
    except Exception as exc:
        verdict="EXPERIMENT_ERROR_OR_LIMIT"
        reason=f"{type(exc).__name__}: {exc}"
        model_bound=None
        printed_verdict=None
    finally:
        ps2wmc.to_DIMACS=original_encode
        ps2wmc.run_wmc=original_solver
    cnf=state["cnf"]
    metadata=(gpmc_cnf_budget_metadata(cnf) if cnf else None)
    status="OBSERVED" if state["printed"] is not None else (
        "CAP_EXCEEDED" if state["pre_solver_limit"] else "NO_COUNT")
    row={
        "family":"ACTUAL_ALGORITHM_CNF",
        "case":case,"qasm_sha256":hashes,
        "method":"wmc_only","backend":"python","selected_solver":"gpmc",
        "epsilon_d":"1e-8",
        "status":status,"verdict":verdict,
        "reason":reason,"printed_verdict":printed_verdict,
        "conditional_model_component_error":model_bound,
        "solver_intercept_calls":state["calls"],
        "cnf_sha256":hashlib.sha256(cnf.encode()).hexdigest() if cnf else None,
        "cnf_variables":metadata[0] if metadata else None,
        "cnf_weight_count":metadata[1] if metadata else None,
        "cnf_weight_max_squared":str(metadata[2]) if metadata else None,
        "elapsed":round(time.monotonic()-started,3),
        "science_note":"not a source-equivalence proof; unknown/error not treated as pass",
    }
    if state["printed"] is not None and metadata is not None:
        cnt=state["printed"]
        row["native_count"]=[str(cnt.real),str(cnt.imag)]
        row["native_print_half_units"]=[str(cnt.real_print_half_unit),str(cnt.imag_print_half_unit)]
        # Compare actual CNF size to the conditional 2^(2n+20-p) heuristic.
        n=metadata[0]
        bits=int(90*math.log2(10))-2
        row["conditional_operation_error_log2"]=2*n+20-bits
    emit(out,row)
    (out/f"corpus-{case}.json").write_text(json.dumps(row,indent=2,sort_keys=True)+"\n")


def bounded_corpus(out: Path, script: Path):
    for case in CASES:
        command=[sys.executable,str(script),"--mode","corpus-worker","--case",case,"--output",str(out)]
        start=time.monotonic()
        proc=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                              text=True,start_new_session=True)
        try:
            stdout,_=proc.communicate(timeout=52)
            exitcode=proc.returncode
            state="completed" if exitcode==0 else "worker_error"
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL)
            stdout,_=proc.communicate()
            exitcode=proc.returncode
            state="resource_timeout"
        (out/f"corpus-{case}.log").write_text(stdout)
        record=out/f"corpus-{case}.json"
        if state=="completed" and not record.exists():
            state="no_structured_evidence"
        emit(out,{"family":"CORPUS_WORKER_GATE","case":case,
                  "worker_status":state,"returncode":exitcode,
                  "elapsed":round(time.monotonic()-start,3)})
    print("ACTUAL_ALGORITHM_CNF_BOUNDED_MATRIX_RECORDED",flush=True)


@contextmanager
def capture_native_gpmc(out: Path, label: str):
    import QuPRS.utils as utils
    original=utils.WMC
    with original("gpmc") as actual_binary:
        with tempfile.TemporaryDirectory() as tmp:
            wrapper=Path(tmp)/"gpmc-count-capture"
            # Preserve the original stdout exactly; one native invocation.
            # The final positional argument to GPMC is its emitted CNF path.
            wrapper.write_text(
                "#!/bin/sh\n"
                "set -eu\n"
                "last=''\nfor item in \"$@\"; do last=\"$item\"; done\n"
                f"cp \"$last\" '{str(out/('rust-'+label+'.cnf'))}'\n"
                f"'{str(actual_binary)}' \"$@\" > '{str(out/('rust-'+label+'.stdout.txt'))}'\n"
                "rc=$?\ncat '"+str(out/("rust-"+label+".stdout.txt"))+"'\nexit \"$rc\"\n"
            )
            wrapper.chmod(0o700)
            @contextmanager
            def injected(tool):
                if tool!="gpmc": raise AssertionError(tool)
                yield wrapper
            utils.WMC=injected
            try:
                yield
            finally:
                utils.WMC=original


def native_rust_qpe(out: Path):
    from QuPRS import check_equivalence
    from QuPRS.utils.gpmc_cnf_metadata import gpmc_cnf_budget_metadata
    from QuPRS.utils.precision_count import (
        parse_printed_solver_output,classify_printed_distance
    )
    left,right,strategy,hashes=sources("qpeexact8")
    for mode,eps in [("reduction_rules",1e-8),("hybrid",1e-8),("hybrid",1e-6)]:
        label=mode.replace("_","-")+"-"+str(eps).replace("-","m")
        started=time.monotonic()
        with capture_native_gpmc(out,label):
            try:
                result=check_equivalence(
                    str(left),str(right),backend="rust",method=mode,
                    tool_name="gpmc",strategy=strategy,timeout=45,
                    approximate_distance_tolerance=eps,
                )
                verdict=result.equivalent
                reason=result.wmc_precision_reason
                printed_verdict=result.wmc_printed_verdict
                solver_invoked=result.wmc_solver_invoked
                result_basis=result.decision_basis
            except Exception as exc:
                verdict="EXPERIMENT_ERROR"
                reason=f"{type(exc).__name__}: {exc}"
                printed_verdict=None
                solver_invoked=None
                result_basis=None
        cnf_file=out/f"rust-{label}.cnf"
        stdout_file=out/f"rust-{label}.stdout.txt"
        row={"family":"RUST_QPE_SOURCE_BOUNDARY",
             "case":"qpeexact8","backend":"rust","method":mode,
             "eps_d":eps,"qasm_sha256":hashes,"verdict":verdict,
             "reason":reason,"printed_verdict":printed_verdict,
             "solver_invoked":solver_invoked,"decision_basis":result_basis,
             "elapsed":round(time.monotonic()-started,3)}
        if cnf_file.exists() and stdout_file.exists():
            text=stdout_file.read_text()
            count=parse_printed_solver_output(text)
            n, weights, max_weight=gpmc_cnf_budget_metadata(cnf_file.read_text())
            # Mirrors lib.rs: input absolute count-component allowance
            # 2^ceil((2q+pathvars)/2) * (weights+1) / 2^49.
            # Extract normalization exponent from the public problem's CNF
            # metadata is impossible in general; use the returned 8-qubit
            # miter normalization only as a *bound* diagnostic here.
            row.update({
                "cnf_sha256":hashlib.sha256(cnf_file.read_bytes()).hexdigest(),
                "cnf_variables":n, "weight_count":weights,
                "max_weight_squared":str(max_weight),
                "count_real":str(count.real),"count_imag":str(count.imag),
                "print_half_real":str(count.real_print_half_unit),
                "print_half_imag":str(count.imag_print_half_unit),
                "raw_count_lines":[v for v in text.splitlines() if v.startswith("c s exact")],
                "nominal_f64_weight_component_relative_2exp_minus49_times_wplus1":
                    str(Fraction(weights+1,2**49)),
                "projective_distance_threshold_defect_approx":
                    str(Fraction(Decimal(str(eps)))**2/2),
            })
        emit(out,row)
        (out/f"rust-{label}.json").write_text(json.dumps(row,sort_keys=True,indent=2)+"\n")
    print("RUST_QPE_FIXED_SOURCE_TRIAD_RECORDED",flush=True)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",choices=("printer","corpus","corpus-worker","rust"),required=True)
    ap.add_argument("--case",choices=tuple(CASES))
    ap.add_argument("--printer-binary")
    ap.add_argument("--output",type=Path,required=True)
    opts=ap.parse_args()
    out=opts.output
    out.mkdir(parents=True,exist_ok=True)
    if opts.mode=="printer":
        printer(out,Path(opts.printer_binary))
    elif opts.mode=="corpus-worker":
        if opts.case is None: raise ValueError("case required")
        resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
        corpus_worker(opts.case,out)
    elif opts.mode=="corpus":
        bounded_corpus(out,Path(__file__).resolve())
    else:
        native_rust_qpe(out)


if __name__=="__main__":
    main()
