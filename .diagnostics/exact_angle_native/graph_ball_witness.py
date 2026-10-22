#!/usr/bin/env python3
"""Rigorous source-exact 16Q projective witness, diagnostic only.

One input basis state, full state-vector with Arb complex-ball enclosures.
Any nonzero projective minor excludes strict global-phase equivalence.
No positive equivalence claims; resource-bounded standalone CI only.
"""
import hashlib
import json
from pathlib import Path

from qpe_ball_witness import read, prepared, evolve, ctx

FILES = (
    "benchmarks/MQTBench/graphstate_nativegates_ibm_qiskit_opt0_16.qasm",
    "benchmarks/MQTBench/h,ry,rz,cx/graphstate_nativegates_ibm_qiskit_opt0_16.qasm",
)
# Exact source corpus used by the successful 256-bit interval witness.
# Never silently replace one operand and claim the prior certificate.
SOURCE_SHA256 = (
    "cf068868f970e553ac9a8fb4998c7c2a6a2e3e6e7a437e3a636f477e34682e36",
    "d2c38d1663dc26757ecb09748918be41c0064cc67bc52d4d7c1c2dfc3fbdd1c9",
)


def main():
    sources = tuple(hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in FILES)
    if sources != SOURCE_SHA256:
        raise ValueError("Graphstate16 source hashes changed; previous proof is invalid")
    left_ops, right_ops = prepared(read(FILES[0],16)), prepared(read(FILES[1],16))
    if (len(left_ops)+len(right_ops))*65536 > 20_000_000:
        raise ValueError("Requested interval proof exceeds explicit bounded budget")
    report = {
        "schema": "quprs-graphstate16-projective-arb-v1",
        "source_files": FILES,
        "source_sha256": sources,
        "precision_bits": ctx.prec,
        "gate_counts": [len(left_ops), len(right_ops)],
        "basis_input": 0,
        "outcome": "INCONCLUSIVE",
    }
    a, b = evolve(left_ops,0,65536), evolve(right_ops,0,65536)
    anchor = None
    for row in range(65536):
        if b[row].contains(0):
            continue
        if anchor is None:
            anchor = (row, a[row], b[row])
            continue
        old_row, old_a, old_b = anchor
        minor = a[row]*old_b - old_a*b[row]
        if not minor.contains(0):
            report["outcome"] = "CERTIFIED_NOT_EQUIVALENT"
            report["witness"] = {
                "coordinate_a": [old_row, 0],
                "coordinate_b": [row, 0],
                "nonzero_minor_complex_interval": str(minor),
            }
            break
    out = Path("exact-source-witness-results/graphstate16.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True), flush=True)
    return 0 if report["outcome"] == "CERTIFIED_NOT_EQUIVALENT" else 2


if __name__ == "__main__":
    raise SystemExit(main())
