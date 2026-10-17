#!/usr/bin/env python3
"""Mechanistic sanity checks for hoist counterfactual (no timings extrapolated)."""
import json, os, pathlib
root=pathlib.Path(os.environ["QUPRS_ATTR_ROOT"])/"results"
diag=root/"diagnostics"
data={}
for case in ("qft16","qaoa7","ghz32","graphstate16","grover4"):
    for solver in ("gpmc","ganak"):
        for v in ("A","AH","B10","BH"):
            fp=diag/f"{case}-{solver}-{v}.jsonl"
            lines=fp.read_text().strip().splitlines()
            assert len(lines)==1,(fp,len(lines))
            row=json.loads(lines[0])
            assert row["completed_ket"]>=0 and row["completed_bra"]>=0
            data[(case,solver,v)]=row
        for orig,hoisted in (("A","AH"),("B10","BH")):
            a,b=data[(case,solver,orig)],data[(case,solver,hoisted)]
            # All semantic rule decisions, exact checkpoint positions and sizes are preserved.
            for field in ("attempts","successes","completed_ket","completed_bra","peak","gate_boundary_peak"):
                assert a[field]==b[field],(case,solver,orig,field,a[field],b[field])
            assert len(a["reductions"])==len(b["reductions"])
            for i,(x,y) in enumerate(zip(a["reductions"],b["reductions"])):
                for field in ("position","completed_ket","completed_bra","before","after","attempts_delta","successes_delta"):
                    assert x[field]==y[field],(case,solver,orig,i,field)
            old=a["get_used_vars_in_elim"]["calls"]
            new=b["get_used_vars_in_elim"]["calls"]
            assert new <= old,(case,solver,orig,old,new)
            if case=="qft16":
                assert new < old,(case,solver,orig,old,new)
            print("VERIFIED",case,solver,orig,"→",hoisted,"reductions",len(a["reductions"]),"get_used",old,"→",new,flush=True)
print("ALL 20 matched hoist traces passed; no semantic rule/checkpoint divergence",flush=True)
