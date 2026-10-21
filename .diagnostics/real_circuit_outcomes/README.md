# Genuine existing MQTBench circuit families: successful Elim discovery

The previous six-family pilot recorded **zero successful Elim** attempts.
The synthetic controlled success/failure fixtures in #61 demonstrate that
the actual rule supports both outcomes, but not whether successful Elim is
common in authentic circuit-verification workloads. Do not mix the two.

This study uses eleven MQTBench algorithm families/case sizes different from
the previous pilot's six cases: QNN4, Wstate4, Qwalk3, QPEexact8,
QPEinexact8, QAOA9, QFT20, GHZ64, VQE8, Grover5 and Graphstate32.
Each runs the exact existing original-vs-decomposed QASM pair in fixed
reverse direction where appropriate, with two native reduction strategies
Naive and Proportional. The strategies are correlated samples of the SAME
family and must never appear on different sides of a held-out split.

Use one source-pinned compiled native Rust FFI, one GPMC executable, fixed
CPU affinity, environment, QASM SHA256 and 25s native timeout per pair.
The source circuit files are not rewritten and no synthetic PathSum state
is injected. All native Stage Ledger and Elim/HH/Omega clocks are opt-in.
Collect original JSONs, statuses, parity, individual rule successes and
attempts, stage closure and source hashes. Crashes and scientific parity
failures mark INCOMPLETE. A circuit timeout is INCONCLUSIVE and is not
counted as a successful equivalence test or successful Elim sample.
No fresh successful-Elim family must be reported as
PASS_DISCOVERY_NO_SUCCESSFUL_ELIM, *not* silent SUCCESS coverage.

An exploratory, post-hoc LOFO analysis compares constant vs L-only vs
K+L vs full K/L/V/D for real Elim attempts, and constant vs input
candidate count (+success flag) separately for HH and Omega. Each entire
circuit family is held out; models use family-balanced weighted ridge,
train-fold-only standardization and fixed alpha 0.02. Report success/fail
Elim separately, and withhold the corresponding predictive verdict unless
at least four independent real successful-Elim families and 30 events
exist. Passing this discovery is NOT prospective external validation:
families were chosen after previous studies and repetition is correlated.

The workflow is a scoped research tool. No performance threshold, adaptive
scheduler, solver plugin mixing or equivalence threshold changes are made.
Preserve original SHA256SUMS artifact even on failure.
