# P0 — externally shared signed SCC weighted-CNF CodSpeed intervention

**This phase can run only because the independent exact Fraction-complex
source reducer and the original/reduced two-solver science gate succeeded:**
[Actions #41844324296](https://github.com/PhysicsQoo/QuPRS/actions/runs/41844324296),
immutable artifact `13331140565`. Six exact small WMC truth-table oracles
PASS; four original and four reduced weighted CNFs, GPMC38/d4-38 count screens
**16/16 PASS** (count-scale 1e-12, not certified internal arithmetic).

| Original CNF | Vars before→after | Clauses before→after | Source weighted vars→reduced weighted vars |
| --- | ---: | ---: | ---: |
| Grover4 EQ | 372→269 | 698→492 | 256→253 |
| QAOA7 genuine NEQ | 470→317 | 823→517 | 319→312 |
| QPE exact8 EQ | 250→184 | 495→363 | 178→171 |
| QFT16 EQ | 486→384 | 1144→940 | 400→384 |

SCC reduction is external and exact on source finite-decimal *literal weights*;
all weights and signed source mapping are preserved in the science artifact.
Source weight/projection syntax is strict; unexpected metadata causes failure.
For four real circuits, count preservation is observed with nominal 38d
effective digits (GPMC MPFR 127 bits, scratch d4 GMP 128 bits), not a formal
proof of numerical accuracy.

**Official performance:** [bounded workflow](../../.github/workflows/qoo157-signed-scc-codspeed.yml)
will replay archived original and the **identical new reduced CNF** through
pinned unmodified GPMC and pinned scratch preparse-precision d4 using 16
official CodSpeed v5 subprocess-inclusive WallTime benchmarks (four circuits
× two solvers × original/reduced). Both binaries must exactly match the
science-run SHA256; no remeasured science included in the timing workflow.
Only compare within-solver original→reduced ratios on the same runner/SHA;
cross-solver absolute comparison still has different solver implementations
and slightly different actual precision bit counts. Record any CI failure
or censored case before making a speed claim.

**No QuPRS dev/main or solver upstream changes; no default change.** Even
if d4 improves, this is an external *science-first research intervention*,
not approval to add a production preprocessing adapter.

## Binary reproducibility gate refinement

Initial P0 CodSpeed [run #41845296994](https://github.com/PhysicsQoo/QuPRS/actions/runs/41845296994) stopped **before any measurement** at the cross-run bit-for-bit `d4-binary.sha256` gate. The 38d research build was compiled in a different scratch path. This proves **nonidentical binary digests across those runs**, not a solver count or numerical regression.

The revised workflow retains original science artifact and exact source/weight
SHA; it records the *actual* current GPMC/d4 executable SHA and performs
all **16 native complex count screens on current binaries before CodSpeed**.
The timed tests are pinned to the new science report's actual SHA and require
the same exact binary for each original/reduced pair. This intentionally
spends a small bounded solver requalification to avoid silently assuming
bitwise reproducibility under changing runner build paths. The first failed
run has **no performance data** and must not be ranked.


## Completed P0 official CodSpeed observations — original versus shared signed-SCC quotient

**SUCCESS**: [GitHub Actions #41846122379](https://github.com/PhysicsQoo/QuPRS/actions/runs/41846122379) on measured HEAD `f40b45448863c4505eeed265c8570087d5bd6b18`. [Immutable native-count screen, current-binary SHA and official CodSpeed export artifact #13331297625](https://github.com/PhysicsQoo/QuPRS/actions/runs/41846122379/artifacts/13331297625). **16/16** CodSpeed v5 tests PASS and **16/16** freshly compiled current-GPMC/d4-binary original/reduced complex count screens PASS prior to timing. Both measured binaries' SHA256 are stored in the same artifact and each timed test asserts them against the newly requalified science report. Source and reduced CNF SHA verified, original 38-significant-digit source weights pinned. GPMC 127 MPFR bits vs d4 actual 128 GMP bits (same nominal 38 effective decimals, not same bit precision).

Official CodSpeed WallTime `3` rounds, `max-time=12`, **medians in ms**; one CI run, same hosted runner/HEAD, subprocess-inclusive **but only prepared CNF** (does **not** include generating the reduced CNF with Python/Fraction):

| Circuit | Solver | Original prepared CNF (ms) | Identical externally reduced CNF (ms) | Reduced/original walltime | Saved percent |
| --- | --- | ---: | ---: | ---: | ---: |
| Grover4 EQ | **GPMC** | 50.268 | 51.124 | 1.0170 | **−1.70%** (slower) |
| Grover4 EQ | **d4** | 222.167 | 192.690 | 0.8673 | **13.27%** |
| QAOA7 genuine NEQ | **GPMC** | 28.300 | 25.944 | 0.9168 | **8.32%** |
| QAOA7 genuine NEQ | **d4** | 137.648 | 127.768 | 0.9282 | **7.18%** |
| QPE exact8 EQ | **GPMC** | 52.048 | 52.011 | 0.9993 | **0.07% (near-noise)** |
| QPE exact8 EQ | **d4** | 163.097 | 140.633 | 0.8623 | **13.77%** |
| QFT16 EQ | **GPMC** | 1124.023 | 1126.787 | 1.0025 | **−0.25% (near-noise)** |
| QFT16 EQ | **d4** | 1760.231 | 1653.470 | 0.9393 | **6.07%** |

Within the same CI run (descriptive only; **not** a formal between-solver equal-bit performance claim), `d4/GPMC` median elapsed ratios for original→common-reduced inputs: Grover4 **4.42→3.77×**, QAOA7 **4.86→4.92×**, QPEexact8 **3.13→2.70×**, QFT16 **1.57→1.47×**. The ratio slightly worsens on QAOA7 because GPMC itself also benefits from reducing the input; the absolute gap nevertheless narrows.

**Scientific interpretation:** Giving d4 a precomputed *exactly weighted* binary-equivalence quotient consistently reduced its **prepared-CNF subprocess time by ~6.1%–13.8% in these four circuits**; d4 remains substantially slower than GPMC even after both receive the same quotient. This **supports** missing input structure as one contributor but **rules out the external SCC quotient as a complete explanation** for GPMC's observed advantage on these cases. It does NOT isolate the individual contributions of the 7/16 protected **weighted-weighted** merges, ordinary unweighted merges, BiPe startup/processing, branch choice, component/cache, or complex arithmetic. Timing of external quotient preparation is excluded; there is **no production-end-to-end speedup claim**.

**Limits and next gate**: Hosted CodSpeed has only 3 timed rounds per benchmark, not the fixed Macro Runner ABBA/BAAB confirmation; GPMC QFT16 ±~0.25% and QPE ~0.07% are effectively neutral versus observed per-round variations. To turn d4 optimization into a recommendation, add cost of any external reducer, peak RSS, timeout, full QuPRS WMC-only/Hybrid path, and more numerical near-cancellation oracles. Start **P1 pinned BiPe stats + canonical-residual identity** with science-only `verbosity>=3`; stage reports may print `t_total`, but only official CodSpeed can be used to compare performance. No d4/default/CI change is justified by this hosted pilot.

**Rejected run**: [Actions #41845296994](https://github.com/PhysicsQoo/QuPRS/actions/runs/41845296994) failed pre-benchmark on cross-run binary SHA equality; contains **no timing data**. It was correctly replaced with current-run binary SHA plus 16-case requalification, not hidden or counted as a trial.
