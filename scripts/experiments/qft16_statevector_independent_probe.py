"""Independent QFT16 statevector witness and compilation-flow QCEC check.

Eight basis/vector inputs are evidence against mismatch, NOT proof of global
operator equivalence or a certified Hilbert-Schmidt projective distance.
"""
import json
import warnings
from pathlib import Path
from time import perf_counter

import numpy as np
from qiskit import qasm2
from qiskit.quantum_info import Statevector
from mqt import qcec


def load(path):
    text="\n".join(line for line in path.read_text().splitlines()
        if not line.strip().startswith(("barrier ", "measure ", "reset ", "creg ")))+"\n"
    return qasm2.loads(text)


def main():
    path=Path(__file__).resolve().parents[2]/"benchmarks/MQTBench"
    filename="qft_nativegates_ibm_qiskit_opt0_16.qasm"
    orig=load(path/filename)
    comp=load(path/"h,ry,rz,cx"/filename)
    assert orig.num_qubits==comp.num_qubits==16
    t=perf_counter()
    with warnings.catch_warnings(record=True) as warnings_out:
        warnings.simplefilter("always")
        check=qcec.verify_compilation(orig,comp,optimization_level=0)
    print("EXPERIMENT_QFT16_QCEC_COMPILATION result={} elapsed_s={:.4f} warnings={}".format(
        check.equivalence,perf_counter()-t,len(warnings_out)),flush=True)
    rng=np.random.default_rng(20261030)
    n=1<<16
    basis=[0,1,2,3,0x1234,0x5555,0xffff]
    inputs=[(f"basis_{j}", Statevector.from_int(j,n)) for j in basis]
    for idx in range(4):
        state=rng.standard_normal(n)+1j*rng.standard_normal(n)
        state=state/np.linalg.norm(state)
        inputs.append((f"random_{idx}",Statevector(state)))
    base_phase=None
    worst=0.0
    per_vector=[]
    for name,initial in inputs:
        a=initial.evolve(orig).data
        b=initial.evolve(comp).data
        overlap=np.vdot(a,b)
        phase=overlap/abs(overlap)
        if base_phase is None:base_phase=phase
        residual=float(np.linalg.norm(b-base_phase*a))
        isolated=float(np.linalg.norm(b-phase*a))
        worst=max(worst,residual)
        per_vector.append({"input":name,"residual_fixed_global_phase":residual,
                           "residual_per_state_phase":isolated})
        print(f"EXPERIMENT_QFT16_STATEVECTOR input={name} residual_global={residual:.8e} residual_bestphase={isolated:.8e}",flush=True)
    assert worst < 1e-8, f"independent QFT16 statevector crosscheck not consistent: {worst}"
    result={"check":"QFT16 statevector witness, not a full unitary certificate",
        "qcec_compilation":str(check.equivalence),
        "inputs":len(inputs),"worst_residual":worst,"basis":basis,
        "per_vector":per_vector,
        "numeric_threshold":1e-8}
    out=Path(__file__).resolve().parents[2]
    evidence=Path("/tmp/quprs-qft16-independent-statevectors.json")
    evidence.write_text(json.dumps(result,indent=2)+"\n")
    print(f"EXPERIMENT_QFT16_STATEVECTOR_SUMMARY inputs={len(inputs)} max_residual={worst:.9e} evidence={evidence}",flush=True)


if __name__=="__main__":
    main()
