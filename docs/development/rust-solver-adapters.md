# Independent Rust WMC solver adapters — Phase 2A

The Rust solver transport is now selected explicitly before the CNF is
serialized or an external solver is launched. Ganak and GPMC each own
executable discovery, CLI arguments, weight grammar, preflight and
count parsing. The existing process supervisor retains deadline,
subprocess tree termination, output limits and temporary-CNF cleanup.

The public tool_name names remain gpmc and ganak; unknown names fail
closed. Existing numeric solver counts remain observations, not exact
certificates. A third mock adapter exercises the same supervised
execution without changing the core verifier. This PR does not change
Python Reduction-first Hybrid, phase/radian representation, solver binary
versions, WMC acceptance thresholds or default solver selection.

A checked serializer try_to_dimacs_string is added; original
to_dimacs_string is retained for supported names. Unsupported names
are rejected by the checked entrypoint and solver entrypoint.

Deferred: a solver-neutral WmcProblem encoding IR, public typed result
and error model, per-run SHA256/version provenance, and Python/Rust
Ganak/GPMC cross-backend conformance matrices. This is not completion
of the entire Solver Plugin Architecture milestone.
