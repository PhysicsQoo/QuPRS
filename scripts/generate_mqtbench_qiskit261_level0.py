#!/usr/bin/env python3
"""Generate a complete, immutable-source MQTBench Qiskit 2.6.1 Level-0 QASM corpus.

Research-only: generate new targets in their own folder; never edit the
historical h,ry,rz,cx/ targets, original QASM, or the TACAS paper artifacts.
The 37 original QASMs are pinned by v0.9.1 Git blob identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
from importlib.metadata import PackageNotFoundError, version as installed_version

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "benchmarks/MQTBench"
NEW = BASE / "qiskit-2.6.1-opt0"
TARGET = NEW / "h,ry,rz,cx"
REGISTER = NEW / "source-register.json"
EXPECTED_QISKIT = "2.6.1"
BASIS = ("h", "ry", "rz", "cx")
IGNORED_NONUNITARIES = ("measure", "reset", "if_else", "while_loop", "switch_case")
SCHEMA = "quprs-mqtbench-qiskit261-level0-complete-v1"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob_sha1(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def load_register() -> dict:
    registry = json.loads(REGISTER.read_text(encoding="utf8"))
    assert registry["schema"] == "quprs-mqtbench-transpiler-source-register-v1"
    assert registry["source_qasm_count"] == 37
    assert registry["historical_transpiled_count"] == 45
    assert registry["compiler"] == {
        "package": "qiskit",
        "exact_version": EXPECTED_QISKIT,
        "target_basis": list(BASIS),
        "optimization_level": 0,
        "approximation_degree": 1,
        "seed_transpiler": 42,
        "serialized_format": "OPENQASM_2",
        "processing": "remove_final_measurements_only",
    }
    entries = registry["source_qasms"]
    names = [e["path"] for e in entries]
    assert len(entries) == 37 and len(set(names)) == 37
    on_disk = {p.name for p in BASE.glob("*.qasm")}
    if set(names) != on_disk:
        raise ValueError("Original source QASM scope changed; migrate registry explicitly")
    legacy_names = {p.name for p in (BASE / "h,ry,rz,cx").glob("*.qasm")}
    if len(legacy_names) != 45:
        raise ValueError("Historical target QASM scope changed")
    missing_original = sorted(legacy_names - set(names))
    if missing_original != registry["legacy_transpiled_without_source"]:
        raise ValueError("Legacy-only benchmark identities changed")
    for entry in entries:
        p = BASE / entry["path"]
        if p.name != entry["path"] or not p.is_file():
            raise ValueError("Unsafe or missing pinned source QASM name")
        data = p.read_bytes()
        if len(data) != entry["bytes"] or blob_sha1(data) != entry["git_blob_sha1"]:
            raise ValueError("Historical v0.9.1 Git blob changed: " + entry["path"])
    return registry


def qc_source(path, qasm2):
    original = qasm2.loads(path.read_text(encoding="utf8"))
    # Identical to the already-established v1.4.2 vs v2.6.1 fidelity study.
    clean = original.remove_final_measurements(inplace=False)
    remaining = set(clean.count_ops())
    if any(n in remaining for n in IGNORED_NONUNITARIES):
        raise ValueError("Unexpected non-terminal/non-unitary operations: " + str(remaining))
    if clean.num_qubits != original.num_qubits:
        raise ValueError("Removing measurements changed qubits")
    return clean, original


def small_operator_diagnostic(source, target, n):
    import numpy as np
    from qiskit.quantum_info import Operator
    if n > 8:
        return {"status": "NOT_MEASURED_RESOURCE_BOUND",
                "metric": None,
                "metric_name": "float_projective_operator_distance"}
    a = Operator(source).data
    b = Operator(target).data
    inner = complex(np.vdot(a,b)/(2**n))
    phase = inner/abs(inner) if inner else 1
    norm = float(np.linalg.norm(a-b/phase)/(2**(n/2)))
    distance = norm * max(0.0,1.0-norm*norm/4.0)**0.5
    if not np.isfinite(distance):
        raise ValueError("Non-finite small-operator diagnostic")
    # A failure here is a semantic regression in the intended strict
    # opt0 baseline, not something to hide behind a different tolerance.
    if distance > 1e-9:
        raise ValueError(f"Opt0 generated QASM has unexpected operator difference: {distance}")
    return {"status":"FLOAT64_OBSERVATION_NOT_FORMAL_CERTIFICATE",
            "metric":distance,
            "metric_name":"phase_aligned_float_projective_operator_distance"}


def dependency_versions():
    result={}
    for name in ("qiskit","numpy","rustworkx","scipy","sympy"):
        try: result[name]=installed_version(name)
        except PackageNotFoundError: result[name]=None
    return result


def produce():
    import qiskit
    from qiskit import qasm2, transpile
    if qiskit.__version__ != EXPECTED_QISKIT:
        raise RuntimeError("Wrong Qiskit runtime: "+qiskit.__version__)
    registry=load_register()
    TARGET.mkdir(parents=True,exist_ok=True)
    expected={e["path"] for e in registry["source_qasms"]}
    unexpected={p.name for p in TARGET.glob("*.qasm")}-expected
    if unexpected:
        raise ValueError("Refusing to silently retain unregistered generated QASM: "+str(unexpected))
    results=[]
    for entry in registry["source_qasms"]:
        source_path=BASE/entry["path"]
        raw=source_path.read_bytes()
        clean,original=qc_source(source_path,qasm2)
        compiled=transpile(clean,basis_gates=list(BASIS),optimization_level=0,
                           approximation_degree=1.0,seed_transpiler=42)
        if compiled.num_qubits != original.num_qubits:
            raise ValueError("Generated QASM changed qubit count")
        instructions=set(compiled.count_ops())
        if any(x not in BASIS and x != "barrier" for x in instructions):
            raise ValueError("Transpiler emitted unapproved gates: "+str(instructions))
        encoded=qasm2.dumps(compiled)
        decoded=qasm2.loads(encoded)
        if decoded.num_qubits != clean.num_qubits:
            raise ValueError("QASM2 roundtrip changes qubit count")
        if any(x not in BASIS and x != "barrier" for x in decoded.count_ops()):
            raise ValueError("Reparsed QASM2 includes unapproved gates")
        if compiled.num_qubits <= 8:
            checked=small_operator_diagnostic(clean,decoded,compiled.num_qubits)
        else:
            checked={"status":"NOT_MEASURED_RESOURCE_BOUND",
                     "metric":None,"metric_name":"float_projective_operator_distance"}
        outfile=TARGET/entry["path"]
        contents=encoded.encode("utf8")
        outfile.write_bytes(contents)
        row={
            "file":entry["path"],
            "source_path":str(source_path.relative_to(ROOT)),
            "source_git_blob_sha1":entry["git_blob_sha1"],
            "source_sha256":sha256(raw),
            "source_bytes":len(raw),
            "generated_path":str(outfile.relative_to(ROOT)),
            "generated_sha256":sha256(contents),
            "generated_bytes":len(contents),
            "num_qubits":compiled.num_qubits,
            "source_instructions":original.size(),
            "source_final_measurements_removed":original.count_ops().get("measure",0)
               -clean.count_ops().get("measure",0),
            "generated_gates":compiled.size(),
            "generated_depth":compiled.depth(),
            "generated_operation_counts":{str(k):int(v) for k,v in
                                          sorted(compiled.count_ops().items())},
            "global_phase_float":float(compiled.global_phase),
            "science_diagnostic":checked,
        }
        results.append(row)
        print("QASM261_LEVEL0_GENERATED",
              json.dumps({"file":row["file"],"qubits":row["num_qubits"],
                          "output_sha256":row["generated_sha256"],
                          "float_diagnostic":checked["status"]},sort_keys=True),flush=True)
    if len(results)!=37:
        raise RuntimeError("Expected all 37 sources generated")
    manifest={
        "schema":SCHEMA,
        "status":"GENERATED_WITH_BYTE_PROVENANCE_NOT_FULL_OPERATOR_CERTIFIED",
        "new_folder":str(NEW.relative_to(ROOT)),
        "target_folder":str(TARGET.relative_to(ROOT)),
        "generation_source_sha":os.getenv("GITHUB_SHA"),
        "generation_ci_run_id":os.getenv("GITHUB_RUN_ID"),
        "historical_input_tag":"v0.9.1",
        "historical_input_commit":"e928abc47dd15926364ec77905eb0d5dc92ce8cc",
        "source_register_sha256":sha256(REGISTER.read_bytes()),
        "qiskit_version":qiskit.__version__,
        "python_version":platform.python_version(),
        "platform":platform.platform(),
        "dependencies":dependency_versions(),
        "compiler":{
            "basis":list(BASIS),
            "optimization_level":0,
            "approximation_degree":1.0,
            "seed_transpiler":42,
            "input_process":"remove_final_measurements_only",
            "output_format":"OPENQASM_2",
        },
        "source_qasm_count":37,
        "generated_qasm_count":len(results),
        "historical_target_count":45,
        "historical_only_without_source":registry["legacy_transpiled_without_source"],
        "legacy_files_modified":False,
        "full_large_operator_verified":False,
        "quprs_equivalence_verdict_verified":False,
        "performance_measured_with_codspeed":False,
        "files":results,
    }
    (NEW/"manifest.json").write_text(
        json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf8")
    verify()
    print("QASM261_LEVEL0_FULL_CORPUS_READY",len(results),flush=True)


def verify():
    from qiskit import qasm2
    load_register()
    meta=json.loads((NEW/"manifest.json").read_text(encoding="utf8"))
    if meta["schema"]!=SCHEMA or meta["qiskit_version"]!=EXPECTED_QISKIT:
        raise ValueError("Wrong generated corpus manifest identity")
    if meta["source_register_sha256"]!=sha256(REGISTER.read_bytes()):
        raise ValueError("Source registry checksum mismatch")
    if meta["generated_qasm_count"]!=37 or len(meta["files"])!=37:
        raise ValueError("Incomplete generated output manifest")
    manifest_paths={r["file"] for r in meta["files"]}
    actual_paths={p.name for p in TARGET.glob("*.qasm")}
    if len(manifest_paths)!=37 or manifest_paths!=actual_paths:
        raise ValueError("Generated folder has missing or unexpected QASM files")
    for record in meta["files"]:
        fp=TARGET/record["file"]
        if fp.name!=record["file"]:
            raise ValueError("Invalid manifest file name")
        b=fp.read_bytes()
        if sha256(b)!=record["generated_sha256"] or len(b)!=record["generated_bytes"]:
            raise ValueError("Generated target digest or byte length changed: "+str(fp))
        qc=qasm2.loads(b.decode("utf8"))
        if qc.num_qubits!=record["num_qubits"]:
            raise ValueError("Reparsed output qubit count changed")
        if any(x not in BASIS and x!="barrier" for x in qc.count_ops()):
            raise ValueError("Reparsed output contains unexpected gates")
    print("QASM261_LEVEL0_CORPUS_VERIFIED",
          json.dumps({"qasm":len(meta["files"]),"source_register_sha256":
                      meta["source_register_sha256"]}),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("action",choices=("generate","verify"))
    args=p.parse_args()
    produce() if args.action=="generate" else verify()
