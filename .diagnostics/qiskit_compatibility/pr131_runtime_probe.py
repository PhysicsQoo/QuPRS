#!/usr/bin/env python3
"""Source-pinned QuPRS PR131 Qiskit 1.4.2 / 2.6.1 API compatibility probe.

This is NOT an installation-support claim for Qiskit2: pyproject still pins <2.
No WMC solvers, transpiler performance claims, or production source edits.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import traceback


def test_probe(qiskit_version):
    from qiskit import QuantumCircuit, QuantumRegister, qasm2, qasm3
    from qiskit.circuit import Parameter
    from QuPRS import check_equivalence
    from QuPRS.interface.load_qiskit import load_circuit, get_gates, build_circuit
    from QuPRS.pathsum.core import PathSum
    from QuPRS.utils.util import div_pi

    details = {}
    failures = []

    def run(label, f, *, required=True):
        try:
            value = f()
            details[label] = {"status": "PASS", "value": value}
        except BaseException as exc:
            details[label] = {"status": "FAIL", "type":type(exc).__name__,
                              "message":str(exc), "traceback":traceback.format_exc()[-2200:]}
            if required:
                failures.append(label)

    def check_rr(backend, representation):
        a = QuantumCircuit(1)
        b = QuantumCircuit(1)
        b.h(0)
        b.h(0)
        if representation == "objects":
            left, right = a, b
        elif representation == "qasm2":
            left, right = qasm2.dumps(a), qasm2.dumps(b)
        else:
            left, right = qasm3.dumps(a), qasm3.dumps(b)
        # The native Rust parser deliberately accepts only OpenQASM 2.
        # Rejecting a QASM3 literal is a pre-existing fail-closed contract,
        # not a version-2 Qiskit compatibility regression.
        if backend=="rust" and representation=="qasm3":
            try:
                check_equivalence(left, right, backend=backend,
                                  method="reduction_rules",
                                  strategy="Naive",timeout=30,rr_tolerance=0.0)
            except ValueError as exc:
                if "only OPENQASM 2.0 is supported" not in str(exc):
                    raise
                return {"qasm3_native_status":"EXPECTED_UNSUPPORTED_FAIL_CLOSED"}
            raise AssertionError("Rust silently accepted unsupported QASM3 input")
        res = check_equivalence(left, right, backend=backend,
                                method="reduction_rules",
                                strategy="Naive",timeout=30,
                                rr_tolerance=0.0)
        if res.equivalent != "equivalent":
            raise AssertionError(f"HH RR expected equivalent; got {res.equivalent}")
        if res.tool_time is not None:
            raise AssertionError("A reduction-only identity must not invoke solver")
        return {"verdict":res.equivalent,"solver_invoked":False}

    def partition_test():
        a = QuantumRegister(2,"alpha")
        b = QuantumRegister(1,"beta")
        qc = QuantumCircuit(a,b)
        qc.h(a[0]);qc.cx(a[0],b[0]);qc.rz(0.1,a[1])
        result = load_circuit(qasm2.dumps(qc))
        original = [(x.name,x.size) for x in qc.qregs]
        loaded = [(x.name,x.size) for x in result.qregs]
        if original != loaded:
            raise AssertionError("Register partition changed")
        ops=get_gates(result)
        if len(ops)!=3 or ops[1][1]!=(0,2):
            raise AssertionError("CircuitInstruction qubit mapping changed")
        ps=build_circuit(result)
        if ps.num_qubits != 3:
            raise AssertionError("QuPRS pathsum register dimensions changed")
        return {"original":original,"loaded":loaded,"gate_qubits":[list(x[1]) for x in ops]}

    def phase_guard():
        a,b=QuantumCircuit(1),QuantumCircuit(1)
        a.global_phase=0.1
        try:
            check_equivalence(a,b,backend="rust",method="reduction_rules",
                              strategy="Naive",timeout=30,rr_tolerance=0.0)
        except ValueError as exc:
            if "global_phase" not in str(exc):
                raise
            return {"unequal_phase_rejected":True}
        raise AssertionError("Unequal explicit global phase silently discarded")

    def pathsum_file_parser():
        from tempfile import TemporaryDirectory
        c=QuantumCircuit(2)
        c.h(0)
        c.cx(0,1)
        with TemporaryDirectory() as temp:
            path=Path(temp)/"bell.qasm"
            path.write_text(qasm2.dumps(c))
            result=PathSum.load_from_qasm_file(str(path))
        if result.num_qubits!=2:
            raise AssertionError("Parsed PathSum width mismatch")
        return {"num_qubits":result.num_qubits}

    def qasm3_roundtrip():
        c=QuantumCircuit(2)
        c.h(0);c.cx(0,1)
        loaded=load_circuit(qasm3.dumps(c))
        if loaded.num_qubits!=2 or loaded.count_ops().get("cx",0)!=1:
            raise AssertionError("QASM3 gate parsing mismatch")
        return {"qregs":[(x.name,x.size) for x in loaded.qregs],
                "counts":dict(loaded.count_ops())}

    def div_pi_parameter():
        x=div_pi(Parameter("theta"))
        return {"expr":str(x),"type":type(x).__name__}

    def auxiliary_imports():
        from QuPRS.utils import Qiskit_Circuit_Utils as utils
        return {"loaded_module":utils.__name__,
                "functions":["pqc_generator","random_circuit",
                             "random_clifford_T_circuit","add_random_rotation_gates"]
               }

    def pqc_generator():
        from QuPRS.utils.Qiskit_Circuit_Utils import pqc_generator
        a,b,name=pqc_generator(qubit_num=2,reps=1,function_name="NLocal")
        if a.num_qubits!=2 or b.num_qubits!=2:
            raise AssertionError("PQC width mismatch")
        return {"name":name,"num_qubits":a.num_qubits,"basis2":dict(b.count_ops())}

    def random_circuit():
        from QuPRS.utils.Qiskit_Circuit_Utils import random_circuit
        a=random_circuit(num_qubits=2,num_gates=6,gates="Clifford",seed=42)
        if a.num_qubits!=2:
            raise AssertionError("Wrong circuit width")
        return {"n":len(a.data),"gate_types":dict(a.count_ops())}

    def phase_serialization_observation():
        c=QuantumCircuit(1)
        c.h(0)
        c.global_phase=0.125
        return {"inmemory":float(c.global_phase),
                "qasm2_loaded":float(qasm2.loads(qasm2.dumps(c)).global_phase),
                "qasm3_loaded":float(qasm3.loads(qasm3.dumps(c)).global_phase),
                "not_a_formal_equivalence_assertion":True}

    run("load_qasm2_register_partitions",partition_test)
    run("qasm2_to_pathsum",pathsum_file_parser)
    run("qasm3_loader",qasm3_roundtrip)
    for backend in ("python","rust"):
        for representation in ("objects","qasm2","qasm3"):
            run(f"RR_{backend}_{representation}",
                lambda b=backend,v=representation: check_rr(b,v))
    run("rust_global_phase_guard",phase_guard)
    run("parameter_pi_check",div_pi_parameter)
    run("Qiskit_Circuit_Utils_import",auxiliary_imports)
    run("pqc_generator_NLocal",pqc_generator)
    run("random_clifford_generator",random_circuit)
    run("QASM_global_phase_serialization_observation",
        phase_serialization_observation,required=False)
    return details, failures


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--qiskit",required=True,choices=["1.4.2","2.6.1"])
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    import qiskit
    if qiskit.__version__!=args.qiskit:
        raise RuntimeError("Wrong Qiskit runtime")
    details, failures = test_probe(args.qiskit)
    pip=subprocess.run(["python","-m","pip","check"],
                       capture_output=True,text=True,check=False)
    result={
        "schema":"quprs-pr131-qiskit2-compat-v2",
        "qiskit_actual":args.qiskit,
        "numpy_actual":importlib.metadata.version("numpy"),
        "expected_numpy":"2.2.6" if args.qiskit=="2.6.1" else "1.26.4",
        "quprs_source_sha":os.getenv("GITHUB_SHA"),
        "ci_run_id":os.getenv("GITHUB_RUN_ID"),
        "quprs_dependency_qiskit":"qiskit>=1.0.0,<2.0",
        "qiskit2_metadata_requirement_intentionally_violated":args.qiskit=="2.6.1",
        "pip_check_exit":pip.returncode,
        "pip_check_stdout":pip.stdout,
        "pip_check_stderr":pip.stderr,
        "qiskit_qasm3_import":importlib.metadata.version("qiskit-qasm3-import"),
        "diagnostics":details,
        "blocking_failures":failures,
        "solver_tests_executed":False,
        "performance_measured":False,
    }
    if result["numpy_actual"]!=result["expected_numpy"]:
        failures.append("numpy_runtime_pin")
    if args.qiskit=="1.4.2" and pip.returncode!=0:
        failures.append("baseline_dependency_installation")
    if args.qiskit=="2.6.1" and pip.returncode==0:
        failures.append("2x_study_did_not_expose_known_metadata_mismatch")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print("QU_PRS_QISKIT2_RUNTIME",json.dumps({
        "qiskit":args.qiskit,"cases":len(details),
        "passed":sum(x["status"]=="PASS" for x in details.values()),
        "failed":failures,"metadata_pip_check_exit":pip.returncode
    }),flush=True)
    return 0 if not failures else 1


if __name__=="__main__":
    raise SystemExit(main())
