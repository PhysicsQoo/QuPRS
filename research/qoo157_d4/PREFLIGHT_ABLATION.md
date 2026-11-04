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
