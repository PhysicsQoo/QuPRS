# MQTBench Qiskit 2.6.1 / Optimization Level 0 QASM corpus

This directory is a **separate, complete re-transpilation of the 37
historically archived source QASM files** in the QuPRS MQTBench folder.
The original files and existing `h,ry,rz,cx/` QASM are intentionally
unchanged.

- Generated circuits: `h,ry,rz,cx/*.qasm`, retaining the original
  source filenames
- Historical source identity: QuPRS **v0.9.1** commit
  `e928abc47dd15926364ec77905eb0d5dc92ce8cc`
- Generator: `scripts/generate_mqtbench_qiskit261_level0.py`
- Qiskit **2.6.1**, Python 3.12, NumPy 2.2.6 (CI)
- `optimization_level=0`, `approximation_degree=1.0`,
  `seed_transpiler=42`, target basis `h,ry,rz,cx`
- Read original OpenQASM 2 and remove final measurements before
  transpilation; retain existing barriers
- `source-register.json` pins all 37 original files by Git blob identity
- `manifest.json` records every generated file's SHA256, the original
  Git blob/SHA256, input/target gate counts, Qiskit environment and
  compiler settings

## Corpus completeness

The existing MQTBench directory contains 37 source QASM files and 45
historical transpiled targets. **All 37 source files** have a one-to-one
output in this directory. The eight old target-only QASM files for
QFT21/23, QPE-exact21/22/23 and QPE-inexact21/22/23 have no matching
source QASM in the QuPRS repository; they are not falsely reconstructed.
They remain available under the original historical target folder.
These missing source identities are explicitly recorded in
`source-register.json` and `manifest.json`.

## Random_Rotation negative controls

The matched `Random_Rotation/` folder now contains **37 deterministic
negative-control QASM** files built from this directory's corresponding
Level-0 `h,ry,rz,cx/` QASM, rather than the historical Level-3 circuit.
Each filename matches its positive counterpart.

- Generator: `scripts/generate_mqtbench_qiskit261_random_rotation.py`
- Rule preserved from historical `scripts/generate_error_circuit.py`:
  `int(source_gate_count * 0.01) + 1` random one-qubit `RX`, `RY`, or
  `RZ` insertions; angles uniform from 0 to 2π
- Independent deterministic seed per file, derived from the original
  output SHA256, filename and a fixed experiment seed string
- `random-rotation-manifest.json` records each injection order,
  final instruction position, gate, qubit, angle, seed, QASM hashes,
  source gate counts and numerical witnesses
- Structural verification proves that removing only the recorded
  injected instructions reproduces the identical original operation list
- 15 cases up to 8 qubits pass a float64 full-operator non-equivalence
  diagnostic; the other 22 remain **NOT_FORMALLY_CERTIFIED**, not
  automatically labeled scientifically proven NEQ
- Old `benchmarks/MQTBench/Random_Rotation/` and
  `benchmarks/MQTBench/Random_Pauli/` stay untouched

To regenerate and independently check the injected negative corpus,
using the **same** pinned Qiskit environment:

```bash
python -m scripts.generate_mqtbench_qiskit261_random_rotation generate
python -m scripts.generate_mqtbench_qiskit261_random_rotation verify
```

Science checks and any timing comparisons must be version-aware;
performance comparisons use CodSpeed only.

## Scientific status

A successful transpile and a small numerical difference in an 8-qubit
operator simulation do **not** certify full formal equivalence for
all large circuits. In particular, the strict projective distance at
`1e-8` must be independently evaluated by QuPRS. The corpus does not
claim Ganak has sufficient output precision at that threshold.

The generated QASM is a new benchmark input identity. Never mix its
correctness or CodSpeed performance history with the historical
`h,ry,rz,cx/` circuit merely because the filenames match.

## Reproduction

Run in an isolated Python 3.12 environment with Qiskit 2.6.1 and
NumPy 2.2.6:

```bash
python -m scripts.generate_mqtbench_qiskit261_level0 generate
python -m scripts.generate_mqtbench_qiskit261_level0 verify
```

**experiment branch only**, without changing `dev`, `main`, PR #131
or any historical Git tag. Additional exact numerical equivalence
testing should be reviewed independently before replacing formal
benchmark registrations.
