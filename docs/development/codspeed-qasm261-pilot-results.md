# Qiskit 2.6.1 Level-0 CodSpeed versioned pilot — first measured pass

**Result:** 15/15 CodSpeed WallTime benchmark requests completed successfully with determinate verdicts; 0 timeouts. The instrument uploaded measurements. The upstream experimental science oracle already recorded strict `distance=1e-8` source-pinned Python/Rust results, but this first timing pilot uses **one Rust/GPMC sample per case** and does not re-certify all independent methods.

- Source and trial commit: `0b192c3549cbc2580f83b892b72c741c6040f02e`, research branch `experiment/qoo160-qasm261-codspeed-selection`
- Actual [GitHub Actions run](https://github.com/PhysicsQoo/QuPRS/actions/runs/41587178934), [per-case JSON and SHA evidence artifact](https://github.com/PhysicsQoo/QuPRS/actions/runs/41587178934/artifacts/13208287655), artifact archive SHA256 `eb9c109bdc906e66e59acb028effed04ef47f26f1108a9099f86c44f5e0ce514`
- [Machine-readable permanent selection and timing records](../../benchmarks/codspeed/qasm261-pilot-observations.json)
- Tool: **CodSpeed WallTime**, one measured round/case, GitHub-hosted shared runner (NOT Macro). Printed values are initial sample medians with exactly one sample; not reliable per-case trend estimates and **not historical-to-new-QASM comparisons**.
- The verifier subprocess includes Python/Rust loading, startup, RR, WMC when invoked, and I/O. RR-only cases largely measure host/startup overhead; they do **not** provide a fine-grained RR optimization signal.

## Measured samples (not comparative base/HEAD performance)

| Independent versioned URI suffix | Single CodSpeed WallTime (ms) | Observed termination | Verdict | RR approximate |
| --- | ---: | --- | --- | --- |
| `q261_ghz32_positive` | 844.15 | RR | `equivalent` | false |
| `q261_graphstate16_positive` | 869.54 | RR | `equivalent` | false |
| `q261_grover4_positive` | 806.37 | RR | `equivalent*` | false |
| `q261_qaoa7_positive` | 826.04 | RR | `equivalent` | false |
| `q261_qaoa7_negative` | 840.61 | WMC | `not_equivalent` | false |
| `q261_qft16_positive` | 821.21 | RR | `equivalent` | true |
| `q261_qft16_negative` | 1354.24 | WMC | `not_equivalent` | false |
| `q261_qnn4_positive` | 850.29 | RR | `equivalent` | false |
| `q261_qnn4_negative` | 848.68 | WMC | `not_equivalent` | false |
| `q261_vqe4_positive` | 835.85 | RR | `equivalent` | false |
| `q261_vqe4_negative` | 828.66 | WMC | `not_equivalent` | false |
| `q261_qpeexact8_positive` | 812.97 | RR | `equivalent*` | true |
| `q261_wstate4_positive` | 865.87 | RR | `equivalent*` | false |
| `q261_vqe8_positive` | 1110.69 | WMC | `equivalent` | false |
| `q261_qpeinexact20_positive` | 816.52 | RR | `equivalent*` | true |

## Selection findings

- **10 RR-terminated and 5 WMC-invoked**. Specifically QAOA7/QFT16/QNN4/VQE4 *negative* and VQE8 *positive* invoke GPMC (5 cases total). Other ten cases terminate at RR. This is why merely replacing old source QASM under an existing benchmark ID is **scientifically wrong**: the execution stage and cost semantics can change.
- QFT16 positive, QPE-exact8 positive and QPE-inexact20 positive terminated through approximate RR. QPE-inexact20 in particular is a **boundary diagnostic**; don't promote it to a default verifier-speed regression gate at `1e-8` without a separately qualified exact-source and tolerance review.
- At ~0.8–1.4 s for a *complete new verifier process*, the first-run WallTime data is dominated by process setup for multiple short RR cases. A dedicated source-pinned **native Rust RR-only CodSpeed Simulation** URI is needed to measure Bra-CX and PhaseCoeff algorithm cost without that overhead, while preserving the separate full-request WallTime category.
- The five actual WMC cases (four negative + VQE8 positive) provide initial solver-inclusive coverage; optimize selection for stable finite Solver work, not any particular expected speed direction. For each future base/HEAD comparison preserve identical QASM hashes, stage, solver, runner cohort and numerical contract. Never subtract this new QASM result from the historical QASM runtime and call the difference a code speedup.
- The 15/15 pytest outcome is a **measurement-completion contract**, not scientific arithmetic certification; the Python/Rust cross-backend and positive/negative source observations must remain separate.
- Keep 32 legacy Simulation IDs, five shards, seven legacy paired WallTime IDs and all original QASM **unchanged**. Future pilot promotion is additive and source-versioned, with reasonable CodSpeed rounds and a distinct maintained baseline.

## Coexistence decision

Keep these new cases on the experiment branch. The source SHA and Git-tracked data are now reproducible; **do not copy the 15-case workflow into the default PR #131 suite** until phase/stage-specific native CodSpeed and representative repeatability plus CI-cost qualification are available. Formal PR #131 source synchronization and its pre-existing independent Performance Analysis gate are distinct and must not be represented as passed by this experimental science result.
