# QOO-157 d4 binary SHA preflight ablation (scientific pilot)

Source branch: experiment/qoo157-d4-codspeed-choice-pilot, measured CodSpeed run
6aeb0f25e2759d7342f6ae61. The prepared-CNF WallTime measurements showed
d4 (patched 426-bit GMP) was slower than GPMC30 in all four real circuits,
with observed slowdown of ~1.70x to ~3.73x on a hosted runner.

**Fairness confound:** the research d4 Python adapter computes SHA256 over the
entire external executable on **every solver call**, unlike incumbent GPMC.
This could overestimate the extra cost of d4 itself. The primary benchmark
correctly describes user-visible research adapter overhead, but cannot
attribute that total cost to the model counting algorithm.

This ablation runs the SAME source SHAs/CNF SHA/external binary/GMP
precision/native solver subprocess/output parser, with three modes:

1. GPMC30: existing QuPRS Python adapter, default binary checks.
2. d4-426 SHA each call: original research adapter.
3. d4-426 prechecked: SHA verified once during module fixture setup
   *outside* CodSpeed timed operation. Each timed call still checks that
   the path is unchanged and delegates to the standard QuPRS supervisor.

**This is NOT a production authorization to omit integrity checks.**
External executable contents can change; a once-checked immutable scratch
file is only acceptable for measuring isolated startup/count cost. A release
design needs trustworthy installation and file-invalidation semantics,
not merely checking a path string.

The experiment reuses the original four source-CNF scientific preflight,
no fake timeout value, and official CodSpeed v5 WallTime. Hosted VM measurements
remain OBSERVATION_ONLY; no qualified Macro Runner or true blocked ABBA
variance evidence. The ablation isolates *per-call binary hashing overhead*
and does not measure complete QASM parsing, RR, CNF build or full verification.

No modifications to QuPRS dev/main or default GPMC/Ganak behavior.

## Completed first-party CodSpeed results

Same-run GitHub Actions
[#41818147183](https://github.com/PhysicsQoo/QuPRS/actions/runs/41818147183),
official [CodSpeed run 6aeb12490d3ce3c3cf708acb](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6aeb12490d3ce3c3cf708acb),
code SHA `784e8c316b59ebd04ccaa8a880ed4976d9bb865b`. All 12
measurements completed, science preflight admitted all 4 paper-family CNFs.
Medians from the archived official CodSpeed WallTime export, 3 rounds each:

| Case | GPMC30 ms | d4 SHA every call ms | d4 SHA once ms | prechecked d4 / GPMC30 |
| --- | ---: | ---: | ---: | ---: |
| Grover4 EQ | 61.344 | 229.003 | 222.413 | 3.63x |
| QAOA7 true NEQ | 41.205 | 148.439 | 141.821 | 3.44x |
| QPEexact8 EQ | 61.307 | 188.695 | 182.007 | 2.97x |
| QFT16 EQ | 1107.968 | 1939.083 | 1912.063 | 1.73x |

The preverification method reduces observed d4 WallTime by around 6.6 ms
on the three smaller cases, but does **not** reverse the ranking on any
tested workload. The larger QFT16 observed difference is ~27 ms; do not
ascribe that whole difference to SHA alone without a controlled Macro Runner,
given variability and 3 rounds. No source, Solver, or tolerance changes.

**Decision:** per-call SHA overhead is a real research adapter artifact but
is **not sufficient to explain away the 4/4 GPMC advantage**. Do not
recommend d4 instead of GPMC in the general QuPRS documentation or switch
the default. Keep this as a source-pinned research-only negative result.
CodSpeed warns of WallTime outside Macro Runner; the figures are
observations, **not a certified performance threshold**.
