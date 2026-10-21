# Source-pinned real-circuit Rust rule attribution

This is an isolated, non-blocking six-family research workflow, applied to
one compiled Rust/Python binary on one Ubuntu runner and one pinned CPU.
It does not modify reductions, priority, solver selection, public APIs,
accuracy thresholds or required CI gates.

Each of six official MQTBench QASM pairs (QAOA7, QFT16, Grover4, VQE4,
Graphstate16, GHZ32) is verified in three fresh child processes per triplet,
using two warm-ups and ten measurement triplets per family.

- Base: Stage Ledger on, no extra per-rule timers.
- Other: Stage Ledger and independently gated candidate-discovery, HH, Omega timers.
- Joint: Stage Ledger and all discovery, HH, Omega and Elim timers.

Fixed per-family verification strategies use one packaged GPMC executable,
a 60-second native timeout, 100-second child hard timeout, pinned CPU affinity,
identical QASM input SHA256 digests, fixed Python packages and a single
compiled Rust binary. Preserve source SHA, dependency and solver hashes,
CPU provenance, per-observation full JSON, append-only JSONL, summary.json,
and SHA256SUMS even on failure.

For each triplet the status, rule counts, final pathsum hash, QASM and native
binary path must agree. Elim structural vectors must agree. Rule outcomes,
candidate counts, inside-root flags and order must agree between Other
and Joint; only elapsed durations may differ. Unexpected/missing opt-in
fields, clock indices, root overlap, closed-time arithmetic or timeouts
produce INCOMPLETE, not successful data.

Each rule span is nested in the root Reduction wall and must never be added
on top of that root. Candidate-discovery success means a nonempty candidate
vector, not actual variable elimination. Elim clocks are assumed inside root
Reduction ONLY along this verified native FFI call path. The unattributed
residual includes loop/dispatch, clock overhead and other bookkeeping;
it is not a separate directly measured rule.

All modes are observer-perturbed. Interleaved base/other/joint FFI ratios and
bootstrap bands are descriptive, not universal overhead measurements.

Full design: six families x three modes x twelve triplets = 216 original
individual runs; 180 are formal measurement records. These repeated trials
are only six independent circuit structures, not 180 separate structures.
This pilot cannot validate an adaptive scheduler or prospective predictive
Reduction Cost Model, especially without new real circuits containing
successful Elim/HH/Omega reductions.
