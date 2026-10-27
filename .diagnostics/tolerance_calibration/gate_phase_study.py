"""Experiment-only sensitivity of gate-phase preservation and numerical solver floor.

No production RR source changes. Temporary monkeypatch only around gate
application; Path-sum reduction.py HH/omega/Elim matching remains unchanged.
"""
import json
import math
import os
from pathlib import Path
import time
from contextlib import contextmanager

import symengine as se
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from QuPRS import config, check_equivalence
from QuPRS.cache_manager import cache_manager
from QuPRS.pathsum.gates import single_qubit, two_qubit
from QuPRS.utils.util import reduce_expression as raw_reduce_expression

OUT = Path("tolerance-calibration-results")
OUT.mkdir(exist_ok=True)
RECORDS = []
FILE = OUT / "gate-phase-observations.jsonl"


def emit(row):
    RECORDS.append(row)
    with FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True, default=str) + "\n")
    print("GATE_PHASE", json.dumps({
        k: row.get(k) for k in ("group", "case", "gate_policy", "rr_tolerance",
                               "method", "solver", "n_h", "verdict", "error")
    }), flush=True)


@contextmanager
def gate_policy(preserve):
    """Skip approximate coefficient deletion only at gate-application sites.

    Important: reduction.py has its own reduce_expression import; its RR
    pattern-matching heuristics continue using the original tolerance.
    """
    before_single = single_qubit.reduce_expression
    before_two = two_qubit.reduce_expression
    if preserve is not None:
        def normalizer(expr, *args, **kwargs):
            # Preserve a complete A/B: legacy deletion vs new source default.
            kwargs["drop_small"] = bool(not preserve)
            return raw_reduce_expression(expr, *args, **kwargs)
        single_qubit.reduce_expression = normalizer
        two_qubit.reduce_expression = normalizer
    try:
        yield
    finally:
        single_qubit.reduce_expression = before_single
        two_qubit.reduce_expression = before_two


def run(left, right, *, label, method, tau, preserve, solver="gpmc",
        group="gate_budget", n_h=None, mag_tau=1e-8):
    row = {
        "group": group, "case": label, "method": method, "solver": solver,
        "gate_policy": ("source_default" if preserve is None else
                        "preserve_nonzero" if preserve else "legacy_gate_snap"),
        "rr_tolerance": tau, "wmc_magnitude_tolerance": mag_tau,
        "n_h": n_h, "GITHUB_SHA": os.environ.get("GITHUB_SHA"),
    }
    old = config.get_tolerance()
    try:
        config.set_tolerance(tau)
        with gate_policy(preserve):
            t0 = time.monotonic()
            result = check_equivalence(
                left, right, backend="python", method=method,
                strategy="Naive", tool_name=solver, timeout=30,
                wmc_magnitude_tolerance=mag_tau,
                wmc_phase_tolerance=1e-8, wmc_policy="legacy",
            )
            row.update({
                "verdict": result.equivalent,
                "walltime_sec": time.monotonic()-t0,
                "log_wmc": result.log_wmc,
                "solver_invoked": result.tool_time is not None,
                "residual_phase": str(result.final_pathsum.P)
                    if hasattr(result.final_pathsum, "P") else None,
                "rr_counts": result.Statistics.get_reduction_counts(),
            })
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        config.set_tolerance(old)
    emit(row)
    return row


def rotation_budget():
    one, repeated, combined = QuantumCircuit(1), QuantumCircuit(1), QuantumCircuit(1)
    for _ in range(200):
        repeated.rz(3e-6, 0)
    combined.rz(0.0006, 0)
    assert Operator(repeated).equiv(Operator(combined), atol=1e-10, rtol=0)
    matrix_distance = abs(math.sin(0.0006/2))
    defect = 2*math.sin(0.0006/4)**2
    assert defect > 1e-8
    ref = {}
    for tau in (1e-6, 1e-10):
        for preserve in (False, True):
            for name, circuit in (("repeated", repeated), ("combined", combined)):
                for method in ("reduction_rules", "hybrid", "wmc_only"):
                    r = run(one, circuit, label=name, method=method, tau=tau,
                            preserve=preserve)
                    ref[(tau,preserve,name,method)] = r
                    r["oracle_projective_distance"] = matrix_distance
                    r["oracle_trace_magnitude_defect"] = defect
    # Existing source reproduces a false equivalence for the long RR/Hybrid
    # at a deliberately loose RR tau. When preserving gate phase, RR may
    # legitimately be unknown, and Hybrid should consult WMC.
    for mode in ("reduction_rules", "hybrid"):
        assert ref[(1e-6,False,"repeated",mode)]["verdict"] == "equivalent"
    assert ref[(1e-6,True,"repeated","reduction_rules")]["verdict"] == "unknown"
    assert ref[(1e-6,True,"repeated","hybrid")]["verdict"] == "not_equivalent"
    assert ref[(1e-6,True,"repeated","hybrid")]["solver_invoked"]
    for preserve in (False,True):
        for tau in (1e-6,1e-10):
            for name in ("repeated","combined"):
                # The deliberate "legacy_gate_snap" A/B arm reproduces the
                # *historical* WMC-only phase-loss bug; it is not an accepted
                # correctness result. The source default is tested separately.
                expected = (
                    "equivalent"
                    if tau == 1e-6 and not preserve and name == "repeated"
                    else "not_equivalent"
                )
                assert ref[(tau,preserve,name,"wmc_only")]["verdict"] == expected, (
                    tau, preserve, name, ref[(tau,preserve,name,"wmc_only")]
                )
    # Compare the normalized weighted count, not just the final status.
    for tau in (1e-6,1e-10):
        assert (ref[(tau,True,"repeated","wmc_only")]["log_wmc"]
                == ref[(tau,True,"combined","wmc_only")]["log_wmc"])



def source_default_gate_contract():
    """Production candidate route, not monkeypatched: provenance matters."""
    left, repeated, combined = QuantumCircuit(1), QuantumCircuit(1), QuantumCircuit(1)
    for _ in range(200):
        repeated.rz(3e-6,0)
    combined.rz(0.0006,0)
    for tau in (1e-6,1e-10):
        for name,right in (("repeated",repeated),("combined",combined)):
            for method in ("reduction_rules","hybrid","wmc_only"):
                row=run(left,right,label=name,method=method,tau=tau,
                        preserve=None,group="source_default_contract")
                expected="unknown" if method=="reduction_rules" else "not_equivalent"
                assert row["verdict"]==expected, (tau,name,method,row)
                if method=="hybrid":
                    assert row["solver_invoked"],(tau,name,method,row)



def reduction_controls():
    def circuit(n, steps):
        q=QuantumCircuit(n)
        for op,qubits in steps:
            getattr(q,op)(*qubits)
        return q
    pairs = {
        "hh_identity": (QuantumCircuit(1), circuit(1,[("h",(0,)),("h",(0,))])),
        "hxh_equals_z": (circuit(1,[("z",(0,))]),
                         circuit(1,[("h",(0,)),("x",(0,)),("h",(0,))])),
        "hzh_equals_x": (circuit(1,[("x",(0,))]),
                         circuit(1,[("h",(0,)),("z",(0,)),("h",(0,))])),
        "t2_equals_s": (circuit(1,[("s",(0,))]),
                         circuit(1,[("t",(0,)),("t",(0,))])),
        "cxhhcx_identity": (QuantumCircuit(2), circuit(2,[
            ("cx",(0,1)),("h",(1,)),("h",(1,)),("cx",(0,1))])),
        "identity_vs_x": (QuantumCircuit(1), circuit(1,[("x",(0,))])),
    }
    for case,(left,right) in pairs.items():
        oracle=Operator(left).equiv(Operator(right),atol=1e-10,rtol=0)
        for preserve in (False,True):
            for method in ("reduction_rules","hybrid"):
                r=run(left,right,label=case,method=method,tau=1e-6,
                      preserve=preserve,group="rules_controls")
                r["matrix_equivalent"] = bool(oracle)
                if oracle:
                    assert r["verdict"] in ("equivalent","equivalent*"), (case,r)
                elif r["verdict"]!="unknown":
                    assert r["verdict"]=="not_equivalent",(case,r)


def solver_floor():
    for n_h in (20,40,60,80):
        a,b=QuantumCircuit(1),QuantumCircuit(1)
        for _ in range(n_h):
            b.h(0)
        for solver in ("gpmc","ganak"):
            r=run(a,b,label="h_identity",method="wmc_only",tau=1e-10,
                  preserve=False,solver=solver,group="solver_floor",n_h=n_h)
            if r.get("log_wmc") is not None:
                expected_log2=1+n_h/2
                delta=(r["log_wmc"]-expected_log2)*math.log(2)
                r["relative_trace_magnitude_defect"]=abs(math.expm1(delta))
            assert r["verdict"]=="equivalent",(n_h,solver,r)

    # Map actual false-negative threshold with a bounded two-depth matrix.
    # Both I and H^N represent exactly the same unitary (N is even).
    for n_h in (60, 80):
        a,b=QuantumCircuit(1),QuantumCircuit(1)
        for _ in range(n_h):
            b.h(0)
        for solver in ("gpmc","ganak"):
            accepted=[]
            for mag_tau in (1e-10, 5e-10, 1e-9, 2e-9, 3e-9, 1e-8):
                r=run(a,b,label="h_identity_threshold",method="wmc_only",
                      tau=1e-10,preserve=False,solver=solver,
                      group="solver_threshold",n_h=n_h,mag_tau=mag_tau)
                accepted.append(r["verdict"]=="equivalent")
                if solver=="gpmc":
                    assert r["verdict"]=="equivalent", (n_h,solver,mag_tau,r)
            assert accepted==sorted(accepted), (n_h,solver,accepted)
            assert accepted[-1], (n_h,solver,accepted)



def cache_probe():
    """Demonstrate whether the low-level cached reducer is tau-dependent."""
    prior=config.get_tolerance()
    x=se.Symbol("tolerance_probe_cycle_x_nonexistent")
    expr=se.Rational(1,2000000)*x
    try:
        cache_manager.clear_all_caches()
        config.set_tolerance(1e-10)
        strict=raw_reduce_expression(expr)
        config.set_tolerance(1e-6)
        stale=raw_reduce_expression(expr)
        cache_manager.clear_all_caches()
        fresh=raw_reduce_expression(expr)
        r={
            "group":"cache_probe","case":"single_symbol_exact_fraction",
            "strict_coeff":str(strict),"stale_coeff":str(stale),
            "fresh_coeff":str(fresh),
            "cache_observed_stale":bool(stale!=fresh),
            "source_tolerance_mutable":True,
        }
        emit(r)
        assert strict!=se.S.Zero and fresh==se.S.Zero
        assert stale==fresh==se.S.Zero and not r["cache_observed_stale"], r
        # Switching back must recover the small but nonzero coefficient.
        config.set_tolerance(1e-10)
        reverse=raw_reduce_expression(expr)
        assert reverse==strict, ("reverse switch retained old tolerance", reverse)
        # Invalid values must not mutate the active configuration.
        for invalid in (True, False, math.nan, math.inf, -math.inf, 0, -1):
            try:
                config.set_tolerance(invalid)
            except ValueError:
                pass
            else:
                raise AssertionError(("invalid tolerance accepted", invalid))
            assert config.get_tolerance()==1e-10
        emit({"group":"cache_probe", "case":"switch_back_and_reject_nonfinite",
              "reverse_coeff":str(reverse),"invalid_candidates_rejected":7,
              "cache_consistent":True})
    finally:
        config.set_tolerance(prior)
        cache_manager.clear_all_caches()


def main():
    rotation_budget()
    source_default_gate_contract()
    reduction_controls()
    solver_floor()
    cache_probe()
    errors=[x for x in RECORDS if x.get("error")]
    summary={
        "source_ref":os.environ.get("GITHUB_SHA"),
        "observations":len(RECORDS),
        "errors":len(errors),
        "groups":{k:sum(x["group"]==k for x in RECORDS)
                  for k in sorted(set(x["group"] for x in RECORDS))},
        "gate_policy_experiment_gate":"PASS" if not errors else "FAIL",
    }
    (OUT/"gate-phase-summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("GATE_PHASE_SUMMARY",json.dumps(summary,sort_keys=True),flush=True)
    assert not errors


if __name__=="__main__":
    main()
