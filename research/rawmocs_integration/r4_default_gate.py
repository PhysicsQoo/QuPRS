"""R4 staged omitted-backend compatibility gate; retain explicit Python."""
import inspect,json,sys
from pathlib import Path
from qiskit import QuantumCircuit,qasm2
from QuPRS import check_equivalence
out=Path(sys.argv[1]);rows=[];issues=[]
assert inspect.signature(check_equivalence).parameters["backend"].default=="rust"
assert inspect.signature(check_equivalence).parameters["tool_name"].default=="gpmc"
def result(a,b,kwargs):
    try:
        r=check_equivalence(a,b,**kwargs)
        return {"status":"returned","verdict":r.equivalent,"invoked":r.wmc_solver_invoked,"tool":r.tool_name,"rr_approximate":r.rr_approximate}
    except Exception as e:
        return {"status":"raised","type":type(e).__name__,"message":str(e)}
def compare(label,a,b,expected,method="hybrid",safe=False,solver="gpmc"):
    kw=dict(method=method,strategy="Naive",timeout=10,safe_mode=safe,tool_name=solver)
    prior=result(a,b,dict(kw,backend="python")) if solver=="gpmc" else None
    explicit=result(a,b,dict(kw,backend="rust"))
    omitted=result(a,b,kw)
    row=dict(case=label,method=method,safe=safe,solver=solver,prior_python=prior,explicit_rust=explicit,omitted=omitted,expected=expected)
    rows.append(row)
    if omitted!=explicit:issues.append({"case":label,"reason":"omitted differs from explicit Rust","method":method})
    if omitted.get("verdict")!=expected:issues.append({"case":label,"reason":"expected public verdict not preserved","method":method})
    if prior is not None and (prior.get("status"),prior.get("verdict"))!=(omitted.get("status"),omitted.get("verdict")):
        issues.append({"case":label,"reason":"previous default contract changed","method":method})
    if prior is not None and prior.get("verdict")!=expected:issues.append({"case":label,"reason":"previous default oracle mismatch","method":method})
id=QuantumCircuit(2)
eq=QuantumCircuit(2);eq.h(0);eq.t(0);eq.tdg(0);eq.h(0)
neq=QuantumCircuit(2);neq.x(0)
gp=QuantumCircuit(2)
for g in ("x","z","x","z"):getattr(gp,g)(0)
for label,c,expected in [("eq",eq,"equivalent"),("neq",neq,"not_equivalent"),("gate_global_phase",gp,"equivalent*")]:
    for method in ("hybrid","wmc_only"):
        compare(label,id,c,expected,method)
compare("qasm2",qasm2.dumps(id),qasm2.dumps(eq),"equivalent","reduction_rules")
compare("safe",id,neq,"not_equivalent",safe=True)
compare("native_optin",id,neq,"not_equivalent","wmc_only",solver="rawmocs_rust_native")
# Known explicit scalar compatibility gap; require matching old semantics, not fallback.
phase=QuantumCircuit(2);phase.global_phase=0.125
compare("explicit_qiskit_relative_phase",id,phase,"equivalent*","reduction_rules")
bad='OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\nx q[5];'
r=result(bad,bad,dict(method="reduction_rules",timeout=10))
rows.append(dict(case="invalid_qasm",omitted=r))
if r["status"]!="raised":issues.append({"case":"invalid_qasm","reason":"must fail closed"})
receipt={"status":"HOLD" if issues else "PASS","rows":rows,"issues":issues}
(out/"result.json").write_text(json.dumps(receipt,indent=2)+"\n")
for row in rows:print("R4_CASE",json.dumps(row))
print("R4_GATE",json.dumps({"status":receipt["status"],"issues":issues}))
if issues:raise SystemExit(1)
print("R4_DEFAULT_COMPATIBILITY_PASS")
