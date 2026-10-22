#!/usr/bin/env python3
"""Research-only exact-QASM complex interval witness for QPEexact8.

For two unitaries U, V, projective equality U=e^(i phi)V implies every
minor U[a]*V[b]-U[b]*V[a] vanishes. Arb ball exclusion of zero in one minor
is a rigorous non-equivalence certificate. No positive equivalence claims.
"""
import hashlib
import json
import re
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from flint import arb, acb, fmpq, ctx
ctx.prec = 256
I = acb(0, 1)
FILES = (
    "benchmarks/MQTBench/qpeexact_nativegates_ibm_qiskit_opt0_8.qasm",
    "benchmarks/MQTBench/h,ry,rz,cx/qpeexact_nativegates_ibm_qiskit_opt0_8.qasm",
)
HASHES = (
    "8d514d06f7c9e81abda1042796cc34227624c9ed66097bee1ce5e97a87884dda",
    "227ab45a4eb033889aa57bb53e54938e74d757fea30eaa3d276b495048dc6141",
)


def angle(expr):
    expr = expr.strip().replace(" ", "")
    sign = -1 if expr.startswith("-") else 1
    expr = expr.lstrip("+-")
    if not expr or len(expr) > 128:
        raise ValueError("Invalid angle")
    parts = expr.split("/")
    if len(parts) > 2:
        raise ValueError("Unsupported QASM angle expression")
    fraction = Fraction(sign)
    pi_count = 0
    for part in parts[0].split("*"):
        if part == "pi":
            pi_count += 1
        else:
            fraction *= Fraction(Decimal(part))
    if pi_count > 1:
        raise ValueError("Nonlinear pi")
    if len(parts) == 2:
        fraction /= Fraction(Decimal(parts[1]))
    if fraction.numerator.bit_length() > 1024 or fraction.denominator.bit_length() > 1024:
        raise ValueError("QASM angle exceeds exact rational budget")
    result = arb(fmpq(fraction.numerator, fraction.denominator))
    return result * arb.pi() if pi_count else result


def read(path, expected_qubits=8):
    registers, gates, qubits = {}, [], 0
    text = Path(path).read_text()
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("//", 1)[0].strip()
        if not line or line.startswith(("OPENQASM", "include")):
            continue
        declaration = re.fullmatch(r"qreg\s+(\w+)\[(\d+)\];", line)
        if declaration:
            name, size = declaration.groups()
            size = int(size)
            if size < 1 or name in registers:
                raise ValueError("Invalid register")
            registers[name] = qubits, size
            qubits += size
            continue

        def pos(name, index):
            offset, size = registers[name]
            idx = int(index)
            if idx < 0 or idx >= size:
                raise ValueError("Invalid source qubit")
            return offset + idx

        rotation = re.fullmatch(r"(rx|ry|rz)\(([^()]+)\)\s+(\w+)\[(\d+)\];", line)
        if rotation:
            name, param, reg, bit = rotation.groups()
            gates.append((name, pos(reg, bit), angle(param)))
            continue
        flip = re.fullmatch(r"x\s+(\w+)\[(\d+)\];", line)
        if flip:
            reg, bit = flip.groups()
            gates.append(("x", pos(reg, bit), None))
            continue
        controlled = re.fullmatch(r"cx\s+(\w+)\[(\d+)\],\s*(\w+)\[(\d+)\];", line)
        if controlled:
            r1, b1, r2, b2 = controlled.groups()
            ctrl, tgt = pos(r1, b1), pos(r2, b2)
            if ctrl == tgt:
                raise ValueError("Invalid CNOT source")
            gates.append(("cx", ctrl, tgt))
            continue
        raise ValueError(f"Unsupported source at {path}:{number}: {line}")
    if qubits != expected_qubits or len(gates) > 512:
        raise ValueError("Invalid QPEexact8 scope")
    return gates


def prepared(gates):
    ops = []
    for name, bit, theta in gates:
        if name == "cx":
            ops.append((name, bit, theta))
            continue
        if name == "x":
            ops.append((name, bit, (acb(0), acb(1), acb(1), acb(0))))
            continue
        if name == "rz":
            z = I * theta / 2
            matrix = ((-z).exp(), acb(0), acb(0), z.exp())
        else:
            c, s = acb((theta / 2).cos()), acb((theta / 2).sin())
            if name == "rx":
                matrix = (c, -I*s, -I*s, c)
            elif name == "ry":
                matrix = (c, -s, s, c)
            else:
                raise AssertionError(name)
        ops.append((name, bit, matrix))
    return ops


def evolve(ops, basis, dim=256):
    state = [acb(0) for _ in range(dim)]
    state[basis] = acb(1)
    for name, bit, arg in ops:
        if name == "cx":
            cmask, tmask = 1 << bit, 1 << arg
            for j in range(dim):
                if (j & cmask) and not (j & tmask):
                    k = j | tmask
                    state[j], state[k] = state[k], state[j]
            continue
        m00, m01, m10, m11 = arg
        mask = 1 << bit
        for j in range(dim):
            if not j & mask:
                k = j | mask
                u, v = state[j], state[k]
                state[j] = m00*u + m01*v
                state[k] = m10*u + m11*v
    return state


def main():
    hashes = tuple(hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in FILES)
    if hashes != HASHES:
        raise ValueError("Pinned QPE source hashes do not match")
    a, b = prepared(read(FILES[0])), prepared(read(FILES[1]))
    report = {
        "schema": "quprs-qpeexact8-projective-arb-v1",
        "source_files": FILES,
        "source_sha256": hashes,
        "precision_bits": ctx.prec,
        "outcome": "INCONCLUSIVE",
        "basis_inputs_examined": [],
    }
    reference = None
    for basis in (0, 1, 2, 4, 8, 16, 32, 64, 128, 255):
        left, right = evolve(a, basis), evolve(b, basis)
        report["basis_inputs_examined"].append(basis)
        for row in range(256):
            if right[row].contains(0):
                continue
            if reference is None:
                reference = (basis, row, left[row], right[row])
                continue
            prev_basis, prev_row, prev_a, prev_b = reference
            minor = left[row]*prev_b - prev_a*right[row]
            if not minor.contains(0):
                report.update({
                    "outcome": "CERTIFIED_NOT_EQUIVALENT",
                    "basis_output_witness": {
                        "coordinate_a": [prev_row, prev_basis],
                        "coordinate_b": [row, basis],
                        "nonzero_minor_complex_interval": str(minor),
                    },
                })
                break
        if report["outcome"] == "CERTIFIED_NOT_EQUIVALENT":
            break
    output = Path("exact-source-witness-results/qpeexact8.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True), flush=True)
    return 0 if report["outcome"] == "CERTIFIED_NOT_EQUIVALENT" else 2


if __name__ == "__main__":
    raise SystemExit(main())
