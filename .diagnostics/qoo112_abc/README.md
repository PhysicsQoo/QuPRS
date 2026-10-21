# QOO-112: source-pinned A/B/C structural diagnostic overhead

This is a one-shot scientific experiment, not a mandatory correctness gate.
The standalone workflow operates only on GitHub-hosted Linux and does NOT
modify the production scheduler or packaged QuPRS implementation.

A = e84f909b before PR #57, with Rust stage diagnostics disabled.
B = 8ce78bd after PR #57, with diagnostics disabled.
C = the exact same B binary, with QUPRS_STAGE_LEDGER=1 enabled.

Each run uses one Ubuntu host and a single pinned GPMC executable. Both
source revisions are built as release wheels in separate isolated virtual
environments with identical inherited dependencies. QAOA7 and QFT16 inputs
are the exact MQTBench pair QASM files, Hybrid/Proportional/GPMC/Rust.

Each circuit has two excluded warmup rounds and 30 shuffled, serial matched
rounds of A, B, C when the 1080-second per-circuit safety budget allows.
Each measurement is the Python wall clock around the native FFI call,
excluding interpreter startup; native wall, PathSum inclusive wall,
full opt-in stage ledger and structure vectors are saved per invocation.
A process hard timeout of 95s and native timeout of 75s apply.

Manifest: pinned Git SHAs, GPMC gitlink, solver and wheel SHA256,
same-host CPU/platform metadata, pip-freeze and QASM SHA256. Output:
samples.jsonl, environment.json, summary.json, summary.md, SHA256SUMS.
Each row includes classification, arm, round, status, and actual wall samples.
INCOMPLETE is mandatory for any timeout or fewer than 30 valid samples
per arm/circuit.

B/A measures default-off regression; C/B estimates actual opt-in overhead.
The summary reports paired median ratios and exploratory bootstrap intervals.
The CI runner may be noisy; these do NOT prove zero overhead or causal savings.
The structural probes record no per-Elim timing, and only two fixed circuit
types cannot support a credible predictive cost model. No scheduler changes
or significant-performance claims follow directly from these results.
