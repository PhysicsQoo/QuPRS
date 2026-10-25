# Small-RZ Source/CNF Evidence Replay

Research-only offline replay of the previous real Python and Rust
RZ(0.0002) CNF artifacts, without invoking GPMC or Ganak again.

Python evidence: run 40160244018, commit
ed72156b860dbafe750bbc0fe2d2e537253609a1, artifact 12586256712.
Rust evidence: run 40161565829, commit
1adbb067793d2bdf6ae7ff24b7cac27a1655c609, artifact 12586057866.

The verifier rechecks SHA256SUMS and raw QASM/CNF hashes, exhaustively
enumerates Boolean assignments, rederives Python source phase activations
and recomputes rational trace enclosures. Rust also replays the archived
PhasePolynomial coefficient TSV and source/represented/printed hull.
Existing recorded verdict booleans are NOT accepted as proofs.

Only the bounded one-qubit source-encoded-CNF model is covered. Neither
general QASM compilation nor internal native solver floating arithmetic
is certified. The executable binary hash is merely an observation since
the binary bytes are not included in the artifact. Do not equate numeric
WMC tolerance with strict mathematical equivalence.

This workflow reads previously sealed artifacts. No production logic,
Hybrid strategy, benchmarks or public WMC policy are modified.

## Source-CNF evidence trust contract

Offline replay now emits typed evidence only after checking the raw source,
emitted weighted CNF and independent rational intervals. The three types are:
`observational_numeric`, `bounded_source_cnf_negative`,
and `inconclusive`. Numeric classifications obtained within a user-defined
tolerance have no strict proof status.

The bounded negative record is restricted to the single audited source
`RZ(0.0002)` and binds the source/QASM SHA256, original commit,
solver-specific actual CNF SHA256, exact rational upper magnitude bound,
and separate selected solver executable hashes recorded as observations.
Each Python/Rust × GPMC/Ganak combination must be present exactly once,
and all four upper endpoints must be strictly below one.

The typed JSON is **NOT self-authenticating**: clients must rerun the raw
archive verification and arithmetic rather than merely parse this envelope.
This does not prove general QASM compiler correctness, native floating
arithmetic, or exact positive equivalence.

## Separate stdlib-only analytic source oracle

The offline replay additionally runs independent_source_oracle.py, which does
NOT import interval_wmc, the phase-bound reference, QuPRS, or any native
solver. It parses the exact raw one-qubit QASM, GPMC/Ganak weighted CNF, and
Rust phase numerator/denominator TSV using only the Python standard library.
It enumerates the raw Boolean assignments independently and requires exactly
one satisfying extension for each input and the correct always-on/bit-on
phase literal activation. The source-only normalized trace bound is derived
from exact rational x=1/10000 and the elementary inequality
0 < cos(x) <= 1 - x^2/2 + x^4/24 < 1.

This is deliberately **not** a second proof of the numerical printed weights
or represented Rust phase coefficients. Those bounds remain separately checked
by the original exact-rational reference implementation. Any mismatch in
source/CNF identity or Boolean activation fails the replay; this independent
source theorem must never be relabeled as a generic solver certificate.
