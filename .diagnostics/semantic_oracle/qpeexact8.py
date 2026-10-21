#!/usr/bin/env python3
"""Independent dense-operator oracle for the genuine QPEexact8 QASM pair.

No QuPRS native backend is consulted. Not Equivalent is a valid scientific
oracle outcome, not a CI 'success proof' for QuPRS. Global phase is allowed.
"""
import hashlib
import json
from pathlib import Path
import platform
import sys

import numpy as np
import qiskit
from qiskit import qasm2
from qiskit.quantum_info import Operator

ROOT=Path("benchmarks/MQTBench")
NAME="qpeexact_nativegates_ibm_qiskit_opt0_8.qasm"
OUT=Path("qpeexact-oracle-results")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    lhs=ROOT/NAME
    rhs=ROOT/"h,ry,rz,cx"/NAME
    circuits=[qasm2.load(str(path)) for path in (lhs,rhs)]
    if circuits[0].num_qubits != circuits[1].num_qubits:
        raise RuntimeError("Different QASM circuit qubit counts")
    nq=circuits[0].num_qubits
    if nq>10:
        raise RuntimeError("Dense oracle would require excessive memory")
    U=Operator(circuits[0]).data
    V=Operator(circuits[1]).data
    z=np.vdot(V.reshape(-1),U.reshape(-1))
    if abs(z)<=1e-14:
        raise RuntimeError("Cannot infer any global phase for candidate matrices")
    phase=z/abs(z)
    errors=np.abs(U-phase*V)
    max_error=float(errors.max())
    frobenius=float(np.linalg.norm(errors))
    # Absolute and dimensional-normalized residuals are independently checked.
    relative_frobenius=frobenius/max(float(np.linalg.norm(U)),1e-14)
    tol=1e-8
    equivalent=bool(max_error<tol and relative_frobenius<tol)
    report={
        "schema":"quprs-independent-qpeexact8-qasm-oracle-v1",
        "oracle":"qiskit.quantum_info.Operator over the unmodified QASM pair",
        "result":"Equivalent (Up to Global Phase)" if equivalent else "Not Equivalent",
        "qubits":nq,
        "dimensions":[list(U.shape),list(V.shape)],
        "qasm_sha256":[sha(lhs),sha(rhs)],
        "qasm_file_paths":[str(lhs),str(rhs)],
        "gate_counts":[c.size() for c in circuits],
        "global_phase_complex":[float(phase.real),float(phase.imag)],
        "max_entrywise_difference_after_global_phase":max_error,
        "relative_frobenius_difference_after_global_phase":relative_frobenius,
        "tolerance":tol,
        "versions":{"python":platform.python_version(),
                    "qiskit":qiskit.__version__,
                    "numpy":np.__version__},
        "comparison":"Direct dense unitary matrix equality modulo one global phase; no QuPRS solver or scheduler involved",
    }
    (OUT/"oracle.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True))
    return 0

if __name__=="__main__":
    sys.exit(main())
