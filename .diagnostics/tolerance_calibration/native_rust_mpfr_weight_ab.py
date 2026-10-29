"""Compare *native Rust MPFR* phase weights with Python oracle and real solvers.

This reuses the current Rust QASM2→PathSum→WmcManager CNF. Only source
phase-weight text is replaced; no CNF clause/reduction/binary changes.
Experimental tool, not the production Rust WMC API.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

from mpmath import mp
from native_weight_rr_followup import (
    OUT, LOG, parse_rust_test_log, replace_weights, run_native,
    rational, mp_weights,
)

SOURCE=OUT/"native-rust-mpfr-weights-input.tsv"
RESULT=OUT/"native-rust-mpfr-weights-output.tsv"
EVIDENCE=OUT/"native-rust-mpfr-weight-solver-ab.json"
CRATE=".diagnostics/tolerance_calibration/rust_precision_transport/Cargo.toml"

cases=parse_rust_test_log()
source_rows=[]
for label, data in sorted(cases.items()):
    for var,(c,r) in sorted(data["phases"].items()):
        for bits in (128,256):
            source_rows.append(
                "\t".join((label,str(var),c[0],c[1],r[0],r[1],str(bits)))
            )
SOURCE.write_text("\n".join(source_rows)+"\n")
assert len(source_rows)==16
proc=subprocess.run([
    "cargo","run","--release","--quiet",
    "--manifest-path",CRATE,"--bin","phase_weight_mpfr",
    "--",str(SOURCE),str(RESULT),
],check=True,capture_output=True,text=True,timeout=180)
assert "NATIVE_RUST_MPFR_WEIGHT_PASS 16" in proc.stdout,proc.stdout
source={}
for line in RESULT.read_text().splitlines():
    label,var,bits,real,imag=line.split("\t")
    k=(label,int(bits))
    source.setdefault(k,{})[int(var)]=(real,imag)
assert len(source)==8 and all(len(v)==2 for v in source.values())
records=[]
with mp.workdps(115):
    for label,case in sorted(cases.items()):
        for bits in (128,256):
            rust_weights=source[(label,bits)]
            python_weights=mp_weights(case["phases"],bits)
            diff=[abs(mp.mpc(mp.mpf(rust_weights[v][0]),
                              mp.mpf(rust_weights[v][1]))
                      -mp.mpc(mp.mpf(python_weights[v][0]),
                              mp.mpf(python_weights[v][1])))
                  for v in rust_weights]
            comparison=max(diff)
            # This compares rounded numerical methods at matching precisions,
            # not an interval proof. Conservatively allow a few final ULPs.
            bound=mp.mpf("1e-36") if bits==128 else mp.mpf("1e-73")
            assert comparison<bound,(label,bits,comparison,bound)
            scalar=[r for c,r,mono in case["terms"] if int(r[0])<0]
            assert len(scalar)==1
            theta=-4*rational(scalar[0])
            analytic_trace=2*mp.cos(theta/2)
            for solver,cnf in case["cnfs"].items():
                candidate=replace_weights(cnf,solver,rust_weights)
                actual=run_native(solver,candidate)
                count=mp.mpc(mp.mpf(actual["count_real_decimal"]),
                             mp.mpf(actual["count_imag_decimal"]))
                row={
                    "label":label,"bits":bits,"solver":solver,
                    "rust_mpfr_weight_sha256":hashlib.sha256(
                        "\n".join(f"{v}: {w[0]} {w[1]}"
                            for v,w in sorted(rust_weights.items())).encode()
                    ).hexdigest(),
                    "cnf_sha256":hashlib.sha256(candidate.encode()).hexdigest(),
                    "rust_mpfr_vs_mpmath_max_abs":mp.nstr(comparison,45),
                    "complex_trace_abs_error":mp.nstr(abs(count-analytic_trace),45),
                    "printed_count_re":actual["count_real_decimal"],
                    "printed_count_im":actual["count_imag_decimal"],
                    "print_half_units":[actual["print_half_unit_re"],
                                        actual["print_half_unit_im"]],
                    "uncertainty_scope":"printed-output only; no solver arithmetic certificate",
                }
                records.append(row)
                print("NATIVE_RUST_MPFR_SOLVER "+json.dumps({
                    k:row[k] for k in
                    ("label","solver","bits","complex_trace_abs_error")
                },sort_keys=True),flush=True)
# Rust must preserve a distinct CNF phase input for source literals differing
# at the 1e-30 rad scale; stock Ganak may still round their counts identically.
for bits in (128,256):
    a=sorted(source[("literal_alias_a",bits)].values())
    b=sorted(source[("literal_alias_b",bits)].values())
    assert a!=b,("Exact source alias erased by native MPFR",bits)
assert len(records)==16
EVIDENCE.write_text(json.dumps({
    "scope":"actual Rust MPFR weight computation, native solver A/B",
    "records":records,
    "source_rows":len(source_rows),
    "certificate":False,
    "source_code":"diagnostic-only; production Rust weight generator unchanged",
},indent=2,sort_keys=True)+"\n")
print("NATIVE_RUST_MPFR_TO_SOLVER_PASS",len(records),flush=True)
