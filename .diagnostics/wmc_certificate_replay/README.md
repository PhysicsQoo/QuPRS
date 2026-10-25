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
