"""Research-only: QPE eighth-cycle vs source-radians A/B and real-circuit negatives.

Reuses the *original* source-identity witness from experimental native Rust
miter test, not numerical nearest-root snapping. Every WMC run counts once
per candidate; there are intentionally multiple distinct research candidates.
No production code, source tolerance, or public API is modified.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mpmath as mp

from real_qpe_qft_source_weights import (
    count_native, get_native_source, magnitude_record,
    positive_weights, source_phases_to_weights, substitute_weights, write
)
from precision_followup_v2 import sources

QPE_SHA = (
    "8d514d06f7c9e81abda1042796cc34227624c9ed66097bee1ce5e97a87884dda",
    "227ab45a4eb033889aa57bb53e54938e74d757fea30eaa3d276b495048dc6141",
)
QFT_SHA = (
    "39b6889497a4e98098b6bb2b4563ace2fb660f4cc3fe8d0763d3f69fc200d865",
    "aa85188d731454bd85b0fe2ae089ab8e6b812501730eee5f1651ac11d7b7fcbc",
)
ROTATION = "0.01"
EPS = 1e-8


def split_native_qpe(out, log):
    from QuPRS.utils import WMC
    phase_map,(nvars,nweights,twice,active) = get_native_source(log)
    orig_cnf = (out/"rust-qpeexact8-source-miter.cnf").read_text()
    original = positive_weights(orig_cnf)
    assert len(original) == nweights == len(phase_map) == 17
    high,quarter,counts=source_phases_to_weights(phase_map)
    eight={}; radians={}; other={}
    for var, (cycle, rad) in phase_map.items():
        mod = cycle % 1
        if rad != 0:
            radians[var]=high[var]
        elif (8*mod).denominator == 1 and (4*mod).denominator != 1:
            eight[var]=high[var]
        elif var not in quarter:
            other[var]=high[var]
    assert counts == {"exact_quarter":10,
                       "exact_eighth_not_quarter":2,
                       "source_radians_nonzero":5,
                       "other_rational_cycles":0}, counts
    assert len(quarter)==10 and len(eight)==2 and len(radians)==5 and not other
    assert len(set(quarter)|set(eight)|set(radians))==17

    candidates = (
        ("baseline", {}),
        ("eighth_only", eight),
        ("radians_only", radians),
        ("eighth_and_radians", {**eight,**radians}),
        ("quarter_only", quarter),
        ("all_source", {**quarter,**eight,**radians}),
    )
    source_hashes=tuple(hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sources("qpeexact8")[:2])
    assert source_hashes == QPE_SHA, source_hashes
    write(out,"QPE_SPLIT_SOURCE_IDENTITY",source_qasm_sha256=source_hashes,
          nvars=nvars,weights=nweights,normalization_twice=twice,
          count_exact_eighth=len(eight),count_nonzero_radians=len(radians),
          count_exact_quarters=len(quarter),source_coefficient_classification=True,
          no_proximity_snap=True)
    results=[]
    with WMC("gpmc") as executable:
        for name, replacements in candidates:
            cnf=substitute_weights(orig_cnf,replacements)
            record=count_native(cnf,f"split-{name}",out,executable)
            distance=magnitude_record(record,twice)
            row=write(out,"QPE_SPLIT_AB",variant=name,
                      weight_replacements=len(replacements),**record,**distance)
            results.append(row)
    # The signs of candidate deltas are observations, not formal monotonic
    # intervals. Do not assume more accurate weights always improve magnitude.
    with mp.workdps(120):
        defects={r["variant"]:mp.mpf(r["normalized_magnitude_defect"])
                 for r in results}
        for name in ("eighth_only","radians_only","eighth_and_radians",
                     "quarter_only","all_source"):
            write(out,"QPE_SPLIT_INTERACTION",variant=name,
                  delta_defect_from_baseline=mp.nstr(
                      defects[name]-defects["baseline"],80),
                  delta_defect_relative_to_all_source=mp.nstr(
                      defects[name]-defects["all_source"],80),
                  nonadditivity_possible=True)
        # Algebraic arithmetic identity for measured change in defect,
        # not a certification of underlying quantum-circuit equivalence.
        interaction=(
            defects["eighth_and_radians"]
            - defects["eighth_only"]
            - defects["radians_only"]
            + defects["baseline"]
        )
        write(out,"QPE_SPLIT_INTERACTION_TOTAL",
              interaction_on_printed_magnitude_defect=mp.nstr(interaction,85))
    print("QPE_SPLIT_SIX_NATIVE_COUNTS_RECORDED",flush=True)


def add_non_global_rz(source: str):
    # Prevent a synthetic 1-qubit counterexample from being mistaken for
    # a change to the actual benchmark circuit.
    assert "OPENQASM 2.0;" in source
    assert "include \"qelib1.inc\";" in source
    body_lines=[line.strip() for line in source.splitlines()
                if line.strip() and not line.lstrip().startswith("//")]
    assert any(line.startswith("qreg ") for line in body_lines)
    assert not any(line.startswith(("measure ","reset ")) for line in body_lines)
    assert any(" q[0];" in line for line in body_lines)
    changed=source.rstrip()+"\nrz("+ROTATION+") q[0];\n"
    assert changed != source and changed.endswith("rz(0.01) q[0];\n")
    return changed


def public_negative(out, family, backend, method, left, right, label,
                    *, proven_self_pair=False):
    from QuPRS import check_equivalence
    t=time.monotonic()
    try:
        result=check_equivalence(left,right,
            backend=backend,method=method,strategy="Proportional",
            tool_name="gpmc",timeout=45,
            approximate_distance_tolerance=EPS)
        row={"status":"observed","verdict":result.equivalent,
             "decision_basis":result.decision_basis,
             "wmc_solver_invoked":result.wmc_solver_invoked,
             "wmc_printed_verdict":result.wmc_printed_verdict,
             "wmc_precision_reason":result.wmc_precision_reason}
    except Exception as exc:
        row={"status":"execution_error",
             "exception":f"{type(exc).__name__}: {exc}"}
    row.update({"case":label,"family_name":family,"backend":backend,
        "method":method,"elapsed_seconds":round(time.monotonic()-t,3),
        "self_pair":proven_self_pair,
        "left_qasm_sha256":hashlib.sha256(left.encode()).hexdigest(),
        "right_qasm_sha256":hashlib.sha256(right.encode()).hexdigest(),
        "distance_epsilon":EPS,
        "original_source_changed":left!=right,
    })
    if proven_self_pair:
        with mp.workdps(90):
            expected=abs(mp.sin(mp.mpf(ROTATION)/2))
            row["independent_analytic_D_proj"]=mp.nstr(expected,70)
            row["analytic_reason"]="unitary conjugation invariant normalized trace: U vs Rz(0.01) U"
            assert expected > mp.mpf(str(EPS))*1000
        # A proved non-equivalent self source pair may be conservatively
        # unknown but may NEVER be labeled equivalent/up-to-global phase.
        if row.get("verdict") in ("equivalent","equivalent*"):
            write(out,"SOURCE_NEGATIVE_FALSE_POSITIVE",**row)
            raise AssertionError(("unsafe false positive",row))
    else:
        row["independent_analytic_D_proj"]=None
        row["analytic_reason"]="original-vs-transpiled baseline not certified; cross-pair is diagnostic"
    write(out,"ACTUAL_CIRCUIT_NEGATIVE",**row)
    return row


def source_circuit_negatives(out):
    # Both source QASMs are real corpus inputs: self-pair has a mathematically
    # known projective distance, while cross-pair can be inconclusive.
    cases=(("qpeexact8","rust","hybrid",QPE_SHA),
           ("qpeexact8","python","wmc_only",QPE_SHA),
           ("qft16","python","wmc_only",QFT_SHA))
    results=[]
    for family,backend,method,expected in cases:
        p_left,p_right,_,hashes=sources(family)
        assert tuple(hashes)==expected, (family,hashes)
        original=p_left.read_text()
        transpiled=p_right.read_text()
        changed_self=add_non_global_rz(original)
        changed_target=add_non_global_rz(transpiled)
        # Save physically modified source, not an artificial scalar/wmc cnf.
        (out/f"negative-{family}-native-source.qasm").write_text(changed_self)
        (out/f"negative-{family}-transpiled-source.qasm").write_text(changed_target)
        result=public_negative(
            out,family,backend,method,original,changed_self,
            "true_source_self_rotation",proven_self_pair=True)
        results.append(result)
        result=public_negative(
            out,family,backend,method,original,changed_target,
            "true_transpiled_target_rotation",proven_self_pair=False)
        results.append(result)
    # Each control must have attempted a true source pair. Non-completion
    # stays explicit, rather than masquerading as a valid semantic verdict.
    assert len(results)==6
    assert all(r["original_source_changed"] for r in results)
    with mp.workdps(90):
        d=abs(mp.sin(mp.mpf(ROTATION)/2))
        assert d>mp.mpf("0.004")
    observed=[r for r in results if r["status"]=="observed"]
    write(out,"NEGATIVE_CONTROL_SUMMARY",
          source_mutation="append physical Rz(0.01) to q[0]",
          cases=len(results),actual_api_results=len(observed),
          source_proven_self_pairs=3,
          unproven_original_vs_transpiled_pairs=3,
          results=[{k:r.get(k) for k in ("family_name","backend","method",
                  "case","status","verdict","wmc_solver_invoked")} for r in results],
          all_self_pair_controls_avoid_false_positive=True)
    print("QPE_QFT_TRUE_SOURCE_NEGATIVES_RECORDED",flush=True)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--rust-native-log",type=Path,required=True)
    o=p.parse_args()
    o.output.mkdir(parents=True,exist_ok=True)
    split_native_qpe(o.output,o.rust_native_log)
    source_circuit_negatives(o.output)
    print("SPLIT_QPE_AND_TRUE_SOURCE_NEGATIVES_COMPLETE",flush=True)


if __name__=="__main__":
    main()
