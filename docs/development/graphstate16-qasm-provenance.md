# Graphstate16 QASM provenance and scientific oracle

This document records what the checked-in artifacts establish, without
asserting an unrecoverable transpilation command.

## P0 — historical source

- QuPRS reference files:
  - `benchmarks/MQTBench/graphstate_nativegates_ibm_qiskit_opt0_16.qasm`,
    Git blob `ab34308febb31ea9a49e9761a988aad7017f3487`;
  - `benchmarks/MQTBench/h,ry,rz,cx/graphstate_nativegates_ibm_qiskit_opt0_16.qasm`,
    Git blob `c2c6f9d04f6a8c2778415572aa247ee93e138c09`.
- Both were present in repository initial commit
  `8bfb9581421d7d9fd3b85ff483e1b8bce3572bd8` (2025-06-11).
- MQT Bench's documented naming convention identifies the first file as
  Graphstate, 16 qubits, IBM native gates, Qiskit optimization level zero.
  This **does not** recover the exact historical Qiskit package version.
- Both artifacts contain the same 16 ordered CNOT edges. They form a
  simple degree-two graph on all 16 qubits (the graph-state generator's
  documented degree). The translated artifact uses `ry/rz/cx` rotations
  with serialized finite-decimal parameters.
- Intended relation: **the same graph-state computation, equivalent up to
  a possible global phase under transpilation/serialization precision**.
- Unknown: exact graph-generation seed, historical MQT Bench and Qiskit
  versions, pass manager, QASM export function/version, whether a direct
  transpile of one committed QASM produced the other, and historical
  `global_phase` before export. A modern regeneration is not proof of
  byte-identical historical provenance.

Reference: https://www.cda.cit.tum.de/mqtbench/description
and https://github.com/munich-quantum-toolkit/bench .

## P1 — independent scientific verification

- `test/test_graphstate16_qiskit_provenance.py` imports both QASM files
  through Qiskit, independent of QuPRS reduction/CNF/WMC.
- Verifies all 65,536 output amplitudes of the **state preparation from
  |0>**, against the graph-state reference
  `CZ(edges) H^16 |0>`, up to global phase.
- Independently compares representative computational-basis columns of
  the two QASM operators and rejects a deliberately corrupted 0.001-rad
  rotation. **Sampled columns are not full-unitary proof.**
- `test/test_graphstate16_source_contract.py` separately validates the
  reported exact Rust PathSum residual for all 16 qubits using rational
  bounds on pi. On a faithful source→PathSum reduction, the QASM literal
  operators are strictly non-equivalent up to global phase but have
  projective Hilbert–Schmidt distance `<2.15e-15`.
- The scientific expectation **remains positive at a declared approximate
  distance threshold** (e.g. `1e-8`) for the Qiskit-transpilation benchmark;
  this does not turn the exact-decimal source witness into exact equality.
- The distance certificate's source-to-reduction soundness, floating solver
  numerical uncertainty, and historical compilation metadata have not
  been established by these tests.

## Acceptance

Keep benchmark intention, literal-source verdict, numeric process-distance,
proof provenance, and observed backend/solver verdict in separate fields.
Never promote numeric WMC `equivalent` into a formal exact certificate.
A failed source pin, a missing distance certificate, or a wrong comparator
must fail closed; an incomplete release baseline must not be published.
