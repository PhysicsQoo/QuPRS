#!/usr/bin/env python3
"""Generate deterministic Random_Rotation negatives from Qiskit 2.6.1 opt0 QASM.

Research evidence only. The 37 frozen QASM2 sources remain unchanged.
Faithfully retains the v0.9.1 injection rule (floor(0.01 * gates) + 1,
random RX/RY/RZ, uniform angle in [0, 2pi), random qubit/position) but uses
one per-file deterministic seed and a machine-readable perturbation ledger.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
from importlib.metadata import PackageNotFoundError, version as package_version

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "benchmarks" / "MQTBench" / "qiskit-2.6.1-opt0"
SOURCES = BASE / "h,ry,rz,cx"
OUTPUT = BASE / "Random_Rotation"
SOURCE_MANIFEST = BASE / "manifest.json"
MANIFEST = BASE / "random-rotation-manifest.json"
VERSION = "2.6.1"
BASE_SEED = "QuPRS-MQTBench-Random_Rotation-qiskit261-opt0-v1"
SCHEMA = "quprs-mqtbench-random-rotation-qiskit261-opt0-v1"
EXACT_BASIS = ("h", "ry", "rz", "cx")
MIN_NUMERIC_NEGATIVE_DISTANCE = 1e-4


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf8")


def seed_for(filename: str, source_sha256: str) -> int:
    # A deterministic seed per case, independent of directory enumeration order.
    payload = f"{BASE_SEED}\n{filename}\n{source_sha256}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def pinned_sources():
    base = json.loads(SOURCE_MANIFEST.read_text(encoding="utf8"))
    if base["schema"] != "quprs-mqtbench-qiskit261-level0-complete-v1":
        raise ValueError("Wrong source QASM manifest schema")
    if base["qiskit_version"] != VERSION or base["generated_qasm_count"] != 37:
        raise ValueError("Wrong Qiskit version or incomplete input corpus")
    rows = base["files"]
    expected = {row["file"] for row in rows}
    if len(rows) != 37 or len(expected) != 37:
        raise ValueError("Missing or duplicated source QASM")
    actual = {x.name for x in SOURCES.glob("*.qasm")}
    if expected != actual:
        raise ValueError("Source QASM directory differs from frozen manifest")
    for row in rows:
        name = row["file"]
        if Path(name).name != name:
            raise ValueError("Non-flat QASM filename")
        f = SOURCES / name
        if sha256(f.read_bytes()) != row["generated_sha256"]:
            raise ValueError("Source QASM SHA256 does not match manifest: " + name)
    return base, rows


def op_token(qc, instruction):
    return {
        "gate": instruction.operation.name,
        "params": [str(param) for param in instruction.operation.params],
        "qubits": [qc.find_bit(b).index for b in instruction.qubits],
        "clbits": [qc.find_bit(b).index for b in instruction.clbits],
    }


def op_tokens(qc):
    return [op_token(qc, inst) for inst in qc.data]


def build_modified(source, name, source_hash):
    from qiskit import QuantumCircuit
    from qiskit.circuit import CircuitInstruction
    from qiskit.circuit.library import RXGate, RYGate, RZGate

    if source.num_qubits <= 0:
        raise ValueError("Cannot apply a rotation with no qubits")
    if any(inst.operation.name in ("measure", "reset", "if_else", "while_loop")
           for inst in source.data):
        raise ValueError("Expected fully unitary QASM without measurements")

    before = list(source.data)
    added = int(len(before) * 0.01) + 1
    seed = seed_for(name, source_hash)
    rng = random.Random(seed)
    changed = list(before)
    # Track final indices so we can prove deletion restores every source op.
    insertions = []
    first_measure = next((i for i, inst in enumerate(changed)
                          if inst.operation.name == "measure"), len(changed))
    for i in range(added):
        gate_type = rng.choice([RXGate, RYGate, RZGate])
        angle = rng.uniform(0, 2 * math.pi)
        qi = rng.randrange(source.num_qubits)
        position = rng.randint(0, first_measure)
        # All prior recorded indices at/after position move one place right.
        for event in insertions:
            if event["final_instruction_index"] >= position:
                event["final_instruction_index"] += 1
        inserted = CircuitInstruction(gate_type(angle), (source.qubits[qi],), ())
        changed.insert(position, inserted)
        insertions.append({
            "insertion_order": i,
            "gate": inserted.operation.name,
            "angle_radians_float64_repr": repr(angle),
            "qubit": qi,
            "insertion_index_at_creation": position,
            "final_instruction_index": position,
        })
        first_measure += 1

    result = QuantumCircuit(*source.qregs, *source.cregs, name=source.name)
    result.global_phase = source.global_phase
    if source.metadata:
        result.metadata = source.metadata.copy()
    for inst in changed:
        result.append(inst)

    positions = {x["final_instruction_index"] for x in insertions}
    if len(positions) != len(insertions) or len(positions) != added:
        raise ValueError("Duplicate inserted instruction indexes")
    original_tokens = op_tokens(source)
    modified_tokens = op_tokens(result)
    if [item for i, item in enumerate(modified_tokens) if i not in positions] != original_tokens:
        raise ValueError("Mutation changed any preexisting gate or ordering")
    for entry in insertions:
        token = modified_tokens[entry["final_instruction_index"]]
        if (token["gate"] != entry["gate"] or
            token["qubits"] != [entry["qubit"]] or
            token["params"] != [entry["angle_radians_float64_repr"]]):
            raise ValueError("Inserted rotation event is not recoverable")
    return result, seed, insertions


def numeric_negative_witness(source, negative):
    """A bounded independent full-operator diagnostic, not a formal certificate."""
    import numpy as np
    from qiskit.quantum_info import Operator
    if source.num_qubits > 8:
        return {"status": "NOT_MEASURED_RESOURCE_BOUND", "operator_projective_distance": None}
    a = Operator(source).data
    b = Operator(negative).data
    d = 2 ** source.num_qubits
    overlap = complex(np.vdot(a, b) / d)
    distance = math.sqrt(max(0., 1. - abs(overlap)**2))
    if not math.isfinite(distance):
        raise ValueError("Nonfinite sampled operator result")
    if distance <= MIN_NUMERIC_NEGATIVE_DISTANCE:
        raise ValueError(f"Injected errors do not pass bounded NEQ sanity threshold: {distance}")
    return {
        "status": "FLOAT64_FULL_OPERATOR_NEGATIVE_WITNESS",
        "operator_projective_distance": distance,
        "reference_resolution":"float64",
        "minimum_required_distance":MIN_NUMERIC_NEGATIVE_DISTANCE,
        "note":"Not a machine-certified error interval",
    }


def runtime_versions():
    versions={}
    for package in ("qiskit","numpy","scipy","rustworkx"):
        try:versions[package]=package_version(package)
        except PackageNotFoundError: versions[package]=None
    return versions


def generate():
    import qiskit
    from qiskit import qasm2
    if qiskit.__version__ != VERSION:
        raise ValueError("Qiskit version mismatch: "+qiskit.__version__)
    parent, entries = pinned_sources()
    OUTPUT.mkdir(parents=True,exist_ok=True)
    unexpected={p.name for p in OUTPUT.glob("*.qasm")}-{x["file"] for x in entries}
    if unexpected:
        raise ValueError("Unregistered files in Random_Rotation target directory: "+repr(unexpected))
    all_rows=[]
    for row in entries:
        src=SOURCES/row["file"]
        base_qc=qasm2.loads(src.read_text(encoding="utf8"))
        original_tokens=op_tokens(base_qc)
        result,seed,insertions=build_modified(base_qc,row["file"],row["generated_sha256"])
        rendered=qasm2.dumps(result)
        parsed=qasm2.loads(rendered)
        if parsed.num_qubits != base_qc.num_qubits or parsed.num_clbits != base_qc.num_clbits:
            raise ValueError("Changed circuit width in QASM2 serialization")
        original_size=len(original_tokens)
        if len(parsed.data)!=len(base_qc.data)+len(insertions):
            raise ValueError("Serialized circuit lost a gate")
        positions={entry["final_instruction_index"] for entry in insertions}
        # The QASM2 parser normalizes decimal parameter serialization: use
        # gate/qubit topology to verify preserved old instructions, not float repr.
        for i, (before, after) in enumerate(zip(
            [q for q in original_tokens],
            [t for k,t in enumerate(op_tokens(parsed)) if k not in positions]
        )):
            if before["gate"]!=after["gate"] or before["qubits"]!=after["qubits"]:
                raise ValueError(f"Reparsed circuit changed source topology: {row['file']} #{i}")
            if before["params"]!=after["params"]:
                raise ValueError(f"Reparsed circuit changed source gate parameter: {row['file']} #{i}")
        witness=numeric_negative_witness(base_qc, parsed)
        encoded=rendered.encode("utf8")
        dest=OUTPUT/row["file"]
        dest.write_bytes(encoded)
        all_rows.append({
            "file":row["file"],
            "baseline_relative_path":str(src.relative_to(ROOT)),
            "baseline_qasm_sha256":row["generated_sha256"],
            "baseline_qubit_count":row["num_qubits"],
            "baseline_instruction_count":len(base_qc.data),
            "injected_instruction_count":len(insertions),
            "injection_formula":"int(baseline_gate_count * 0.01) + 1",
            "seed":seed,
            "injected_operations":insertions,
            "output_relative_path":str(dest.relative_to(ROOT)),
            "output_sha256":sha256(encoded),
            "output_size_bytes":len(encoded),
            "output_instruction_count":len(parsed.data),
            "science_diagnostic":witness,
            "expected_binary":"NEQ",
            "expected_verdict_certified":False,
        })
        print("ROTATION_261_GENERATED",json.dumps({
            "file":row["file"],"insertions":len(insertions),"output_sha256":sha256(encoded),
            "witness":witness["status"]
        },sort_keys=True),flush=True)
    if len(all_rows)!=37:
        raise ValueError("Incomplete negative corpus")
    meta={
        "schema":SCHEMA,
        "status":"GENERATED_WITH_INJECTION_PROVENANCE_NOT_FORMALLY_CERTIFIED_ALL_CASES",
        "baseline_manifest_sha256":sha256(SOURCE_MANIFEST.read_bytes()),
        "baseline_source_commit":parent.get("generation_source_sha"),
        "generator_source_sha":os.getenv("GITHUB_SHA"),
        "generation_ci_run_id":os.getenv("GITHUB_RUN_ID"),
        "qiskit_version":qiskit.__version__,
        "python":platform.python_version(),
        "versions":runtime_versions(),
        "random_generator":"python random.Random independent per-file seeded SHA256",
        "base_seed":BASE_SEED,
        "rotation_gate_set":["rx","ry","rz"],
        "angle_radians_distribution":"uniform(0, 2 * pi)",
        "insertion_position_distribution":"uniform among valid instruction boundaries (inclusive)",
        "seed_algorithm":"first 64 bits of sha256(base_seed + LF + filename + LF + source_qasm_sha256)",
        "historical_injection_rule":"floor(0.01 * input_gate_count) + 1; random RX/RY/RZ gate angle qubit and position",
        "historical_random_rotation_modified":False,
        "baseline_qasm_modified":False,
        "source_count":37,
        "target_count":len(all_rows),
        "small_full_operator_witnesses":sum(x["science_diagnostic"]["status"]==
             "FLOAT64_FULL_OPERATOR_NEGATIVE_WITNESS" for x in all_rows),
        "large_not_formally_certified":sum(x["science_diagnostic"]["status"]==
             "NOT_MEASURED_RESOURCE_BOUND" for x in all_rows),
        "notes":[
          "Injection is evidence of an intended NEQ construction, not a general formal proof for large circuits.",
          "Full v0.14.0 Python/Rust solver EQ/NEQ classification and Ganak resolution require separate experiments.",
          "No runtime performance measured; use CodSpeed for performance comparisons.",
        ],
        "cases":all_rows,
    }
    write_text(MANIFEST,json.dumps(meta,sort_keys=True,indent=2,ensure_ascii=False)+"\n")
    verify()
    print("ROTATION_261_CORPUS_READY",len(all_rows),flush=True)


def verify():
    from qiskit import qasm2
    parent,baseline=pinned_sources()
    if not MANIFEST.is_file():
        raise ValueError("Negative corpus manifest absent")
    meta=json.loads(MANIFEST.read_text(encoding="utf8"))
    if meta["schema"] != SCHEMA or meta["qiskit_version"] != VERSION:
        raise ValueError("Negative corpus manifest schema mismatch")
    if meta["baseline_manifest_sha256"] != sha256(SOURCE_MANIFEST.read_bytes()):
        raise ValueError("Baseline manifest has changed")
    if meta["target_count"] != 37 or len(meta["cases"])!=37:
        raise ValueError("Manifest count mismatch")
    if {x["file"] for x in meta["cases"]}!={x["file"] for x in baseline}:
        raise ValueError("Negative corpus missing a source case")
    if {p.name for p in OUTPUT.glob("*.qasm")}!={x["file"] for x in baseline}:
        raise ValueError("Disk QASM set changed")
    for case in meta["cases"]:
        src=SOURCES/case["file"]
        dest=OUTPUT/case["file"]
        if sha256(src.read_bytes()) != case["baseline_qasm_sha256"]:
            raise ValueError("Source QASM bytes changed")
        contents=dest.read_bytes()
        if sha256(contents) != case["output_sha256"]:
            raise ValueError("Generated QASM bytes changed")
        original=qasm2.loads(src.read_text(encoding="utf8"))
        altered=qasm2.loads(contents.decode("utf8"))
        if (altered.num_qubits!=original.num_qubits or
            len(altered.data)!=len(original.data)+len(case["injected_operations"])):
            raise ValueError("Width or operation count changed")
        op_before=op_tokens(original);op_after=op_tokens(altered)
        positions={x["final_instruction_index"] for x in case["injected_operations"]}
        if len(positions)!=len(case["injected_operations"]):
            raise ValueError("Duplicated recorded injection positions")
        if [t for i,t in enumerate(op_after) if i not in positions]!=op_before:
            raise ValueError("Removing injected instructions did not restore exact source")
        for event in case["injected_operations"]:
            token=op_after[event["final_instruction_index"]]
            if (token["gate"]!=event["gate"] or token["qubits"]!=[event["qubit"]] or
                token["params"] != [event["angle_radians_float64_repr"]]):
                raise ValueError("Rotation ledger mismatch")
    print("ROTATION_261_CORPUS_VERIFIED",len(meta["cases"]),flush=True)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("task",choices=("generate","verify"))
    a=p.parse_args()
    if a.task=="generate":generate()
    else:verify()


if __name__=="__main__":
    main()
