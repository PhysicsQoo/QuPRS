# CodSpeed QASM identity review: TACAS sources vs Qiskit 2.6.1 Level-0

Status: **versioned experimental candidate, not a default/legacy benchmark substitution**.

Review baseline: PR #131 `07d5c8d` merged with `dev@2dd451e`. The historical 32 CodSpeed Simulation identities and five shards, seven solver-inclusive WallTime identities and 25 native Rust microbenchmark IDs remain unchanged. Historical runtime observations do **not** transfer to a new QASM pair.

## Machine-readable scope

- [Full source and outcome audit](../../benchmarks/codspeed/qasm_variant_audit.json): all 37 MQTBench source files (including 17 not currently selected for CodSpeed), the **20 distinct QASM filenames referenced across CodSpeed registries** and all 4 original Feynman QASM inputs. Historical source and counterpart Git blobs, Qiskit 2.6.1 target/negative SHA256 and selection lanes are recorded.
- The source-pinned [strict `1e-8` GPMC experiment](https://github.com/PhysicsQoo/QuPRS/tree/experiment/tacas26-paper-reproduction/docs/development/mqtbench-qiskit261-level0-acceptance/runs/41573879894) recorded **244 matching determinate** and **52 censored/missing** observations out of 296, with no returned binary EQ/NEQ contradiction. Its science and numerical provenance are *not* a CodSpeed CPU/WallTime measurement or a solver-arithmetic proof.
- Existing main benchmark IDs and original QASM byte inputs remain frozen; adding Qiskit 2.6.1 means a **new URI/new measured baseline** and a fixed compiler/source SHA, even if its visible filename matches.

## Currently selected CodSpeed source QASM (20 distinct MQT circuits)

| Circuit | Existing lanes | Qiskit 2.6.1 science (returned / 8) | Recommended scope |
|---|---|---:|---|
| `ghz32` | legacy-simulation-32, cross-method-opt-in | 8/8 | KEEP_LEGACY_AND_ADD_VERSIONED_V2_URI |
| `ghz64` | pilot-eight-opt-in, curated-v2-proposed | 8/8 | OPT_IN_V2_CANDIDATE |
| `graphstate16` | legacy-simulation-32, cross-method-opt-in | 8/8 | KEEP_LEGACY_AND_ADD_VERSIONED_V2_URI |
| `graphstate32` | pilot-eight-opt-in, curated-v2-proposed | 8/8 | OPT_IN_V2_CANDIDATE |
| `graphstate64` | paper-gap-seven-opt-in | 8/8 | OPT_IN_V2_CANDIDATE |
| `grover-noancilla4` | legacy-simulation-32, solver-walltime-7, solver-cpu-opt-in, cross-method-opt-in | 8/8 | KEEP_LEGACY_AND_ADD_VERSIONED_V2_URI |
| `qaoa11` | paper-gap-seven-opt-in | 8/8 | OPT_IN_V2_CANDIDATE |
| `qaoa7` | legacy-simulation-32, solver-walltime-7, solver-cpu-opt-in, cross-method-opt-in | 8/8 | KEEP_LEGACY_AND_ADD_VERSIONED_V2_URI |
| `qft16` | legacy-simulation-32, solver-walltime-7, solver-cpu-opt-in, cross-method-opt-in | 8/8 | KEEP_LEGACY_AND_ADD_VERSIONED_V2_URI |
| `qnn4` | pilot-eight-opt-in | 8/8 | OPT_IN_V2_CANDIDATE |
| `qnn8` | paper-gap-seven-opt-in | 8/8 | OPT_IN_V2_CANDIDATE |
| `qpeexact8` | pilot-eight-opt-in, curated-v2-proposed | 8/8 | OPT_IN_V2_CANDIDATE |
| `qpeinexact16` | curated-v2-proposed | 8/8 | OPT_IN_V2_CANDIDATE |
| `qpeinexact20` | paper-gap-seven-opt-in | 4/8 | OPT_IN_V2_CENSORED_GUARD |
| `qpeinexact8` | pilot-eight-opt-in | 8/8 | OPT_IN_V2_CANDIDATE |
| `qwalk-noancilla3` | pilot-eight-opt-in | 8/8 | OPT_IN_V2_CANDIDATE |
| `qwalk-noancilla4` | paper-gap-seven-opt-in, curated-v2-proposed | 8/8 | OPT_IN_V2_CANDIDATE |
| `vqe4` | legacy-simulation-32, solver-walltime-7, solver-cpu-opt-in, cross-method-opt-in | 8/8 | KEEP_LEGACY_AND_ADD_VERSIONED_V2_URI |
| `vqe8` | pilot-eight-opt-in | 8/8 | OPT_IN_V2_CANDIDATE |
| `wstate4` | pilot-eight-opt-in, curated-v2-proposed | 8/8 | OPT_IN_V2_CANDIDATE |

Feynman identities: `adder_8`, `gf2^4_mult`, `tof_3`, `vbe_adder_3`. There is no matching Qiskit 2.6.1 MQTBench source corpus for these; **retain their byte-identical historical sources and RR-only measurement semantics**.

## Experiment design and decisions

1. **Keep** all 32 original MQTBench/Feynman simulation IDs, 5 shards, and 7 formal solver-inclusive WallTime case names with their legacy fixture hashes. Do not silently substitute Level-0 circuits, or reuse the old baseline for newly compiled QASM. New v2 benchmark URIs must explicitly name the compiler version.
2. **Priority for versioned pilot:** QFT16 (Bra-CX/RR), QAOA7, VQE4, QNN4, GHZ32, Graphstate16 and QPE-exact8/WState4/VQE8 cover separate RR, GPMC, complexity and negative-control paths. The strict GPMC experiment supplies source/verdict screening evidence; CodSpeed is required for actual performance and stage-inclusive timing qualification.
3. **Separate heavy fidelity research:** QFT20/22 and QPE-exact20 Level-0 deserve source/semantic investigation because historic saved transpilation can deviate in the finite two-state fidelity metric. These 9–22-qubit statevector observations are **not full projective operator-distance proofs**. Keep QPE-inexact20 at strict `1e-8` as an opt-in boundary/stage fixture, not a generic fast baseline. Do not wholesale adopt Level-3 Qiskit 2.6.1 outputs.
4. **Do not infer a solver result from a timeout.** The newer Qiskit corpus includes censored Grover5/6 negative, QFT24, QNN12, QPE20/24 WMC-only, VQE16 and WState32 workloads; reserve these for bounded manual stress tests with explicit timeout and provenance.
5. Ganak mode 6 has printed-value resolution limitations at the default `1e-8`; its historical near-equality verdict mismatches are **not** resolved by swapping QASM. First qualify the new GPMC variant, then evaluate Ganak separately with distinct identifiers and numerical warnings.

## Promotion rules

- A case may join default PR CodSpeed only after the exact new source/target SHA256 and unitary/NEQ science, Python/Rust RR-versus-WMC stage, Solver invocation, bounded reproducible CodSpeed measurement and CI cost are independently checked.
- A changed QASM pair, transpiler version/level, input direction, solver/backend, timeout, tolerance or CodSpeed instrument creates a new benchmark identity; do not reinterpret data from the original URI.
- Pre-release PR-only experiments are replaceable, but the 32 identities already present on `main` retain the release compatibility window. The TACAS historical reproduction branch remains isolated and its solver/source evidence is not a substitute for v0.14.0 measurements.

## Evidence links

- [New QASM corpus and reproduction settings](https://github.com/PhysicsQoo/QuPRS/blob/2dd451edeaab4e7c80ea19203e36cc22f3548d85/benchmarks/MQTBench/qiskit-2.6.1-opt0/README.md)
- [Full strict-source science classification](https://github.com/PhysicsQoo/QuPRS/blob/experiment/tacas26-paper-reproduction/docs/development/mqtbench-qiskit261-level0-acceptance/runs/41573879894/classification.csv)
- [Qiskit 1.4.2 vs 2.6.1 fidelity comparison](https://github.com/PhysicsQoo/QuPRS/blob/experiment/tacas26-paper-reproduction/docs/development/tacas26-qiskit-version-fidelity/README.md)
- [Legacy compatibility policy](codspeed-compatibility-policy.md)
