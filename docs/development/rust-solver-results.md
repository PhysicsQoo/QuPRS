# Typed Rust WMC solver observation and failures

The selected Ganak/GPMC execution remains independent, using the existing
deadline and process-tree supervisor. The new opt-in
WmcManager::observe_with_deadline returns a typed SolverObservation containing
solver identity, argument array, native complex count, successful exit code,
elapsed seconds and explicit exact_count_certificate=false.
It does not make a mathematical proof from a floating count.

Known malformed output, a missing count after exit 0, nonzero process
status, and unsupported adapter ID now preserve original error strings
while carrying SolverFailureKind categories for downcast/reflection.
Timeout deliberately retains the original SolverTimeout error type,
ensuring existing public check_equivalence Timeout behavior remains intact.
OS-level spawn/cleanup failures remain anyhow/IO errors with original
context; do not infer they are malformed native counts.

The public solve/solve_with_deadline and check_equivalence APIs still return
their original forms. Exact executable SHA/version, platform provenance,
and broad cross-language conformance belong to separate evidence gates.
No global-phase, RR-first Hybrid, weight serialization, reduction, numeric
threshold or solver version policy is changed here.
