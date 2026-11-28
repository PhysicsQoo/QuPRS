#!/usr/bin/env python3
"""D9: pinned upstream Wstate generator + existing deterministic rotation ledger.
New generated instances, not historical paper fixtures. No selection by timing.
"""
import ast,importlib.util,json,math,sys,platform
from pathlib import Path
from importlib.metadata import version
import numpy as np
import qiskit
from qiskit import QuantumCircuit,QuantumRegister,qasm2,transpile
from qiskit.quantum_info import Statevector
from eq_dag_d1 import sha,git
ROOT=Path.cwd()
HERE=Path(__file__).resolve().parent
def record(path):
    return dict(path=str(path.relative_to(ROOT)),git_blob_sha1=git("hash-object",str(path)),sha256=sha(path))
def main():
    out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=False)
    assert qiskit.__version__=="2.6.1" and np.__version__=="2.5.5"
    template=json.loads((HERE/"eq_dag_d9_manifest.json").read_text())
    source=HERE/"fixtures/d9_mqt_v240/wstate.py";license=source.with_name("LICENSE")
    assert git("hash-object",str(source))==template["upstream"]["source_blob"]
    assert git("hash-object",str(license))==template["upstream"]["license_blob"]
    # Execute exact upstream function AST; registry decorator is an identity adapter.
    tree=ast.parse(source.read_text());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=="create_circuit")
    ns=dict(np=np,QuantumCircuit=QuantumCircuit,QuantumRegister=QuantumRegister,register_benchmark=lambda *a,**kw:lambda f:f)
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(source),"exec"),ns)
    mutpath=ROOT/"scripts/generate_mqtbench_qiskit261_random_rotation.py"
    assert git("hash-object",str(mutpath))==template["mutation_blob"]
    spec=importlib.util.spec_from_file_location("d9_mutation",mutpath);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    cases=[];receipts=[]
    for n in template["widths"]:
        name=f"wstate_nativegates_ibm_qiskit_opt0_{n}.qasm"
        raw=ns["create_circuit"](n).remove_final_measurements(inplace=False)
        src=out/f"wstate{n}-abstract.qasm";src.write_text(qasm2.dumps(raw))
        target=transpile(raw,basis_gates=["h","ry","rz","cx"],optimization_level=0,approximation_degree=1.,seed_transpiler=42)
        left=out/f"wstate{n}-flat-source.qasm";left.write_text(qasm2.dumps(target))
        base=qasm2.loads(left.read_text())
        assert set(base.count_ops())<={"h","ry","rz","cx","barrier"} and base.num_qubits==n
        negative,seed,insertions=mod.build_modified(base,name,sha(left))
        right=out/f"wstate{n}-rotation.qasm";right.write_text(qasm2.dumps(negative))
        neg=qasm2.loads(right.read_text())
        pos={x["final_instruction_index"] for x in insertions}
        assert len(neg.data)==len(base.data)+len(pos)
        assert [t for i,t in enumerate(mod.op_tokens(neg)) if i not in pos]==mod.op_tokens(base)
        # Independent statevector witnesses, not formal full-operator certificates.
        # A single non-collinear output for the same input refutes projective EQ.
        witnesses=[]
        for k in (0,1,(1<<n)-1):
            a=Statevector.from_int(k,2**n).evolve(base).data
            b=Statevector.from_int(k,2**n).evolve(neg).data
            overlap=abs(np.vdot(a,b))
            d=math.sqrt(max(0.,1.-float(overlap)**2))
            assert math.isfinite(d)
            witnesses.append(dict(input=k,abs_overlap=float(overlap),projective_state_distance=d))
        assert max(w["projective_state_distance"] for w in witnesses)>1e-4
        # Validate intended W-state preparation of the compiled unmutated circuit.
        state=Statevector.from_instruction(base).data
        support=np.array([1<<i for i in range(n)])
        assert abs(float(np.sum(np.abs(state[support])**2))-1.)<1e-10
        assert np.max(np.abs(np.abs(state[support])-1/math.sqrt(n)))<1e-10
        case=dict(id=f"wstate_{n}_new_neq",family="wstate",mode="hybrid",expected="NEQ",strategy="proportional",left=record(left),right=record(right),expectation="Float64 non-collinear state witness, not formal exact certificate")
        cases.append(case);receipts.append(dict(case=case["id"],abstract=record(src),left=case["left"],right=case["right"],seed=seed,insertions=insertions,witnesses=witnesses))
        print("D9_SOURCE",json.dumps(receipts[-1]),flush=True)
    template["cases"]=cases
    template["generation"]=dict(python=platform.python_version(),dependencies={p:version(p) for p in ("qiskit","numpy","scipy","rustworkx")},receipts=receipts,compiler=dict(basis=["h","ry","rz","cx"],optimization_level=0,approximation_degree=1.,seed_transpiler=42),upstream_execution="exact function AST with identity registry decorator")
    (out/"manifest.json").write_text(json.dumps(template,indent=2)+"\n")
    print("D9_SOURCE_LOCK_COMPLETE",len(cases))
if __name__=="__main__":main()
