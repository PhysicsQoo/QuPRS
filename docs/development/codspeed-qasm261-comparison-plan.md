# QASM261: Native RR / multi-round Solver-inclusive CodSpeed acceptance plan

The five original native microbench groups and all 32 historical Simulation
identities remain unchanged. The Qiskit 2.6.1 Level-0 input is a **new**
measurement identity, never a renamed historical QASM fixture.

This research branch adds two independent instruments and checks:

1. `benchmarks/rust_qasm261/benches/native_rr.rs`: five **real** native
   source-QASM equivalence checks, compiled QASM2 from the pinned 2.6.1
   corpus, parsed through Rust `qasm::parse_qasm_str` before
   `divan::main()`. Each run constructs and reduces a new native
   PathSum with `VerificationMethod::ReductionRules`; asserts EQ/EQ*
   and zero Solver invocation. Source/target angles are never substituted
   by handcrafted 1-qubit synthetic examples. Included: GHZ32,
   Graphstate16, QFT16 (Bra-CX), QPE-exact8 and VQE4. Original Rust
   PhaseCoeff/HH microbench continue separately.
2. `benchmarks/codspeed/test_qasm261_solver_pair.py`: five source-pinned
   GPMC-invoked verifier workloads selected from actual pilot verdicts:
   QAOA7, QFT16, QNN4, VQE4 negative Random_Rotation and VQE8 positive.
   Each uses `dev@2dd451e` and `PR#131@07d5c8d` installed separately,
   with identical Qiskit261 fixture bytes from the experimental commit.
   Same-host A1/B1/B2/A2 sequence, up to five official CodSpeed WallTime
   measured rounds **per position**, and no custom stopwatch. Capture
   true Solver-invoked and verdict on every observed verifier invocation.
   The reporter rejects missing/duplicate URIs, invalid rounds and mixed
   QASM hashes. Verdict, stage, tolerances, and printed precision remain
   independent of timing.

Scientific/measurement provenance must not be conflated. CI green = pipeline
completed and data valid; it does not imply statistically significant speedup,
certified GPMC arithmetic or a new release gate. Hosted runner A/A drift,
CV, case-level execution-stage changes, and job-level CI cost determine any
promotion. Do not use historical QASM timings as a numerator/denominator
against modern inputs.

Acceptance for a *routine* PR benchmark requires (a) comparable exact
source/target QASM and a versioned ID, (b) both revisions reaching the
intended RR-only or WMC stage, (c) consistent EQ/NEQ, (d) repeated
CodSpeed WallTime or native CPU metrics with reasonable hosted-runner
variance, (e) acceptable measured CI cost. Existing PR testing is already
solver inclusive; heavy/hard QFT and tolerance edge cases may remain opt-in.

The [first 15-case pilot](codspeed-qasm261-pilot-results.md) found
10 RR-only and 5 genuine WMC cases. The numeric comparison and final
selection will be recorded after actual experiment CI observation; **do
not infer it from static source registration**.
