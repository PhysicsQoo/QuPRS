# QNN4 and VQE8: independent QASM source-pair matrix qualification

## Source provenance

QuPRS PR #131 benchmark candidate pilot on exact HEAD
`500f8ba66b30e0737de25e928dc3181dd1c2a3b8`, GitHub Actions
[41389522077](https://github.com/PhysicsQoo/QuPRS/actions/runs/41389522077),
CodSpeed service run
[6ae814ed9a84b3bf77ba5e3d](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6ae814ed9a84b3bf77ba5e3d).
Both cases have `wmc_solver_invoked=true` for **GPMC** through Rust Hybrid; this boolean does not establish an exact invocation count.
No timeout occurred (15-second internal solver timeout, 24-second outer
watchdog). The original execution yielded:

| Source-pinned circuit | Pilot verdict | RR approximate | Solver invoked | WMC printed verdict | Precision warning |
|---|---|---|---|---|---|
| QNN4 | `equivalent*` | false | true | equivalent | `printed_count_uncertified_solver_arithmetic` |
| VQE8 | `equivalent` | false | true | equivalent | `printed_count_uncertified_solver_arithmetic` |

Pilot source files in `benchmarks/MQTBench/` and
`benchmarks/MQTBench/h,ry,rz,cx/` were recorded with SHA256
(original then transpiled):

- QNN4: `f76af749135c82f3f4fe8c72fc217e6db63d0421637aecc5ac06b78584c1e0f4`,
  `4d83b6a6aaed9ff67afadb391568410cc381ca1251a423720bb547d48add5f27`
- VQE8: `7a09dfcd231d4ef6932ac988ee7db18895a932428cfbbaa69498e19d2962515b`,
  `b4ed8565f2dae2fbbf1cfa00be1ea40d6d921bdeb9843780278ea62931dccebf`

## Independent scientific check

Compute complete `2^n × 2^n` operators of both original and transpiled
source files; normalize overlap and remove the relative global phase
before evaluating the Frobenius residual. The standalone
`scripts/check_codspeed_source_oracle.py` uses Qiskit `QuantumCircuit`
and `Operator`; it runs **outside** the CodSpeed measurement window
and also checks `U†U ≈ I`. Its existing VQE4 and Grover4 checks
continue to run unchanged.

A separate, self-contained complex128 QASM gate-by-gate numerical
implementation produced these *pre-CI reference values*, independent of
QuPRS, GPMC and the Qiskit script:

| Quantity | QNN4 | VQE8 |
|---|---:|---:|
| Qubits / operator dimension | 4 / 16 | 8 / 256 |
| Original / transpiled gates | 111 / 122 | 134 / 95 |
| Relative phase angle, radians | 2.356194490192345 | ~0 |
| Phase-corrected normalized Frobenius residual | 4.8191e-15 | 2.6207e-15 |
| Maximum entry error after phase adjustment | 3.3839e-15 | 2.3524e-15 |

This supports the *scientific plausibility* of `equivalent*` for
QNN4 and `equivalent` for VQE8 (different global-phase classes).
It is not a rigorous high-precision proof of distance below `1e-8`.

**Numerical trap:** A naive double-precision
`sqrt(1 - |Tr(U†V)|² / 4^n)` can suffer catastrophic cancellation when
the trace magnitude is nearly `2^n`. For VQE8, that unstable formula
yielded approximately `3.49e-7` despite a directly evaluated
phase-aligned matrix residual near `2.6e-15`. Do **not** use this
naive derived value to fail the source-pair comparison or to alter
QuPRS WMC classification thresholds.

**Remaining gates:** A source-matched, independently executed Qiskit
oracle in the existing paired-WallTime CI must pass for QNN4 and VQE8;
a complex128 reference does not certify GPMC printed-count arithmetic
or its error budget. For a permanent PR performance gate, additionally
require repeated CodSpeed same-runner measurements and an explicitly
separate Solver-inclusive scientific status; the first 8-circuit pilot
collected only one round outside Macro Runners.
