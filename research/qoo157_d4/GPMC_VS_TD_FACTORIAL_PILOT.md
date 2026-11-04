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
