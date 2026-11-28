#!/usr/bin/env python3
"""D7e2: distinguish Python RR residual semantics from verdict policy."""
import json,os,sys,subprocess,math
from pathlib import Path
from eq_dag_d1 import git,sha

def arm(c,tol):
    import sympy as sp
    import symengine as se
    import numpy as np
    from qiskit import qasm2
    from qiskit.quantum_info import Operator
    from QuPRS import check_equivalence
    from QuPRS.utils.verification_tolerances import DEFAULT_RR_TOLERANCE
    a,b=(c[k]["path"] for k in ("left","right"))
    r=check_equivalence(a,b,method="reduction_rules",strategy="Proportional",backend="python",timeout=8,rr_tolerance=tol)
    row=dict(case=c["id"],tolerance=tol,effective_default=DEFAULT_RR_TOLERANCE,verdict=r.equivalent,rr_approximate=r.rr_approximate,solver_invoked=r.wmc_solver_invoked,progress=r.progress)
    ps=r.final_pathsum
    if not hasattr(ps,"P"):
        print("D7E2_ARM "+json.dumps(row),flush=True);return
    P=sp.sympify(ps.P).expand()
    bits=[sp.Symbol(str(s)) for s in ps.bits]
    paths=sorted(map(lambda x:sp.Symbol(str(x)),ps.pathvar),key=str)
    outputs=[sp.sympify(ps.f[i]) for i in range(ps.num_qubits)]
    n=len(bits);h=len(paths)
    row.update(n=n,h=h,phase=str(P),output=list(map(str,outputs)),pathvars=list(map(str,paths)),counts=ps.get_reduction_counts())
    assert not set(bits)&set(paths)
    free=P.free_symbols.union(*(f.free_symbols for f in outputs))
    assert free<=set(bits+paths),(free,set(bits+paths))
    if h+n<=14:
        N=2**n;M=np.zeros((N,N),dtype=complex)
        for x in range(N):
            for y in range(2**h):
                vals={s:(x>>i)&1 for i,s in enumerate(bits)}
                vals.update({s:(y>>i)&1 for i,s in enumerate(paths)})
                o=0
                for i,f in enumerate(outputs):
                    v=f.subs({s:bool(k) for s,k in vals.items()})
                    assert v in (sp.true,sp.false,0,1),str(v)
                    o|=(1 if v in (sp.true,1) else 0)<<i
                cycles=float(P.subs(vals).evalf(40))
                M[o,x]+=np.exp(2j*np.pi*cycles)*2**(-h/2)
        def dist(A,B):
            ov=np.vdot(A,B);phase=ov/abs(ov) if abs(ov)>0 else 1
            return float(np.linalg.norm(B-phase*A)/np.sqrt(N))
        U,V=[Operator(qasm2.load(z,custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)).data for z in (a,b)]
        row.update(residual_projective_identity=dist(np.eye(N),M),source_projective_distance=dist(U,V),residual_unitarity_error=float(np.linalg.norm(M.conj().T@M-np.eye(N))),source_miter_projective_distances={k:dist(A,M) for k,A in {"VdagU":V.conj().T@U,"UVdag":U@V.conj().T,"UdagV":U.conj().T@V,"VUdag":V@U.conj().T}.items()})
    # Numerical coefficient census only, not rigorous acceptance bound.
    if h==0 and all(f==s for f,s in zip(outputs,bits)):
        poly=sp.Poly(P,*bits)
        rows=[]
        for mono,coeff in poly.terms():
            if any(mono):
                val=coeff.evalf(50);nearest=sp.floor(val+sp.Rational(1,2))
                rows.append(dict(monomial=list(mono),coefficient=str(coeff),wrapped_abs=str(abs(val-nearest))))
        row["non_global_coefficients"]=rows
        row["numeric_wrapped_l1_cycles"]=str(sum(sp.Float(x["wrapped_abs"],50) for x in rows))
    print("D7E2_ARM "+json.dumps(row),flush=True)

def main():
    mp=Path(__file__).with_name("eq_dag_d7e_manifest.json");m=json.loads(mp.read_text())
    out=Path(sys.argv[1]);out.mkdir()
    cases=[c for c in m["cases"] if c["id"] in {"qwalk-noancilla_3","qwalk-noancilla_negative_3","tof_3"}]
    assert len(cases)==3
    for c in cases:
        for k in ("left","right"):
            z=c[k];assert git("hash-object",z["path"])==z["git_blob_sha1"]
            if "sha256" in z:assert sha(z["path"])==z["sha256"]
    rows=[];issues=[]
    for c in cases:
        for tol in (None,0.0):
            # Fresh processes, fixed hash seed, no WMC; exact RR may be inconclusive.
            cmd=["prlimit","--as=4294967296","--","timeout","--kill-after=2s","12",sys.executable,str(Path(__file__).resolve()),"--arm",json.dumps(c),json.dumps(tol)]
            p=subprocess.run(cmd,capture_output=True,text=True,errors="replace")
            stem=c["id"]+("-default" if tol is None else "-exact")
            (out/(stem+".stdout")).write_text(p.stdout);(out/(stem+".stderr")).write_text(p.stderr)
            hits=[s[len("D7E2_ARM "):] for s in p.stdout.splitlines() if s.startswith("D7E2_ARM ")]
            row=json.loads(hits[0]) if len(hits)==1 else dict(case=c["id"],tolerance=tol,status="OUTER_TIMEOUT" if p.returncode in (124,137) else "ERROR")
            row["returncode"]=p.returncode;rows.append(row)
            print("D7E2_RESULT",json.dumps(row),flush=True)
            if p.returncode not in (0,124,137) or (p.returncode==0 and len(hits)!=1):issues.append(stem)
            if row.get("solver_invoked") is True:issues.append(stem+" solver invoked")
    (out/"summary.json").write_text(json.dumps(dict(rows=rows,issues=issues,scope="diagnosis only; original D7e failure retained"),indent=2)+"\n")
    assert not issues,issues
    print("D7E2_DIAGNOSTIC_COMPLETE")
if __name__=="__main__":
    if sys.argv[1]=="--arm":arm(json.loads(sys.argv[2]),json.loads(sys.argv[3]))
    else:main()
