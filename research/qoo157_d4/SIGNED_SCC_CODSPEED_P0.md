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
