# QOO-157 — GPMC variable-selection × tree-decomposition factorial

**Branch-scoped research only**. Eight source-identical GPMC experiments:
QAOA7 genuine NEQ and QFT16 EQ × `-vs=0/1` × `-td/-no-td`.
Each uses the original source SHA-256-verified archived weighted CNF and
pinned GPMC `a1bda3489e959d3695b6798d327c5a1fc1bed305`.
Effective MPFR precision: 38 decimal digits (127 bits).

The experiment checks all eight output counts against the archived GPMC38
complex result and the `vs1_td` baseline, rejects mismatched CNFs and
missing/ignored FlowCutter under TD-on, and preserves native count/search
markers. It does **not** prove solver arithmetic error bounds.

**Important source detail:** GPMC `-vs=0` *also consumes* the TD `exscore`
(by adding it to variable frequency); `-vs=1` orders primarily on that
extra score, with frequency/activity tie-breaking. Therefore the four cells
measure **interaction** of two heuristics with TD, not independent TD use.
The source of this distinction is `GPMC/core/ComponentManager.cc` pinned.

Only official CodSpeed WallTime is performance data. A GitHub-hosted run is
**OBSERVATION_ONLY** until a qualified Macro Runner / repeated matched-order
ABBA design. The measured scope is original prepared weighted CNF through
process startup, parse, preprocessing, TD and search; no QASM/RR/CNF generation.
CodSpeed output min is not interchangeable with three-round median.

Reproduction: [workflow](../../.github/workflows/qoo157-gpmc-vs-td-factorial.yml),
[science preflight](gpmc_vs_td_factorial.py),
[CodSpeed 8-case test](test_codspeed_gpmc_vs_td_factorial.py).
This workflow uses only the already-uploaded QOO-157 artifact 13317939531.

**Next stage (not measured by this workflow):** compare GPMC -pp_ee on/off
against d4 pinned 38d BiPe preprocessing on the original CNF, checking
actually transformed clause/variable counts, weighted-model-count semantics,
initialization cost and the scientific count. Ganak 2.8.0 mode6 is gated
separately by QOO-98 and cannot be claimed 38-digit-equivalent without evidence.


## Measured outcome: scoped official CodSpeed 2×2 at 2026-11-04

**SUCCESS** [GitHub Actions #41836818679](https://github.com/PhysicsQoo/QuPRS/actions/runs/41836818679); artifact [#13325587788](https://github.com/PhysicsQoo/QuPRS/actions/runs/41836818679/artifacts/13325587788); measured source SHA `e316019465368509909071aaf0b919e44b506720`. Pinned GPMC source SHA `a1bda3489e959d3695b6798d327c5a1fc1bed305`; original source CNF source artifact `13317939531`. Scientific preflight **all 8 COUNT_CONCORDANT_UNCERTIFIED** relative to archived rational WMC and TD-on default; TD-on variants emitted actual FlowCutter marker (no skipped/ignored TD); TD-off variants did not. No new/changed solver source. One official hosted CodSpeed v5 WallTime run, **3 measured rounds per cell**, medians below; no qualified Macro Runner ABBA.

| Original source CNF | VS 0 / TD on | VS 0 / no TD | VS 1 / TD on | VS 1 / no TD |
| --- | ---: | ---: | ---: | ---: |
| QAOA7 genuine NEQ (ms) | 22.614249 | 39.552754 | **22.247594** | 39.522233 |
| QFT16 EQ (ms) | 951.633644 | 1076.361321 | **928.043** | 1094.231 |

The source artifact JSON stores exact median nanoseconds; QFT16 VS1 values below must be read from the raw export rather than this rounded editorial table when preparing formal paired reports.

| Same case | VS0: TD time saving | VS1: TD time saving |
| --- | ---: | ---: |
| QAOA7 NEQ | **42.83%** | **43.71%** |
| QFT16 EQ | **11.59%** | **15.19%** |

**Native search mechanism:** on QAOA7, VS0 and VS1 under TD-on both yielded 1,004 decisions / 5,268 propagations, versus 2,648 / 15,247 with TD-off. On QFT16, VS1 with TD-on yielded 66,695 decisions / 1,275,496 propagations; VS0 TD-on yielded 67,585 / 1,324,632; both TD-off yielded 72,169 / 1,510,872. In all eight cases the GPMC output counters reported zero conflicts, SAT calls and backjumps. These source-run counters provide evidence that TD changed *search work*, not just startup/measurement jitter. They do not establish the precise internal time fraction of TD preparation, caching or arithmetic.

**Interpretation:** TD has clear beneficial direction in this small pair for both variable-selection options. VS=1 is fastest with TD-on in both cases, but its advantage over VS=0 is much smaller than the effect of enabling TD. **VS=0 also consumes TD exscore** (frequency+score formulation), therefore the 2×2 comparison captures interactions and does not isolate four independent effects.

**CI incident record:** initial [#41836099660](https://github.com/PhysicsQoo/QuPRS/actions/runs/41836099660) failed the science preflight because archived WMC count strings were exact rationals (`Fraction`) not directly `Decimal`-parseable. Second [#41836489930](https://github.com/PhysicsQoo/QuPRS/actions/runs/41836489930) failed because `"vs0_no_td".endswith("_td")` was true; it was a probe-label logic error. Both were science/preflight code failures with **no timed benchmarks**; no native solver or numerical failure. Commit `e316019` corrected both, and [#41836818679](https://github.com/PhysicsQoo/QuPRS/actions/runs/41836818679) supersedes the failures.

**Remaining performance caveat:** CodSpeed warns about hosted WallTime outside Macro Runners, and a 3-round single job is not sufficient for statistical significance or claiming the full GPMC/d4 gap is explained by TD. The *next* independent workflow is [GPMC EE versus d4 BiPe native preprocessing](ACTUAL_PREPROCESSING_COMPARISON.md); do not infer that its pre/post variable counts will directly measure per-solver runtime.
