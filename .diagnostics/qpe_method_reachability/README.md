# QPEexact8 method isolation and legal-gate Elim reachability

Two independent research-only experiments. No production Reduction, solver,
scheduler, accuracy threshold or performance-gate change.

## QPEexact8 method/backend isolation

The unchanged QPEexact8 QASM pair is pinned by SHA256; QPEinexact8 is
an adjacent control. Qiskit dense unitary checks each pair independently
modulo global phase. Both cases run reduction_rules, hybrid and wmc_only;
Naive and Proportional; Rust and Python, with 40 s native and 60 s
child-process deadlines. Total 24 raw child records, all using GPMC.
Retain Rust Stage Ledger, FFI phase timings, final PathSum hash and excerpt,
Rust vs Qiskit parser gate counts, timeouts and errors in original JSON.

A Not Equivalent result contrary to a certified equivalent source is
SCIENCE_BLOCKED, not PASS. Unknown, crash and timeout remain inconclusive.
Workflow fails but always uploads original evidence and SHA256 manifest.

## Real valid-gate Elim reachability

Construct 72 deterministic 2/3-qubit valid QASM gate pairs with six
inverse/decomposition/global-phase patterns, three depths, and two seeds.
Every pair is certified as unitary-equivalent by Qiskit independently.
Each pair executes actual native reduction_rules using Naive,
Proportional and Straightforward (216 native results), with original QASM,
per-rule stats, nested traces and all hash provenance retained.

Positive Elim means an actual native successful Elim from executable
quantum gates, never an artificially inserted PathSum variable.
These are ENGINEERED identities, not 72 natural algorithm families.
No positive hits does NOT prove Elim is mathematically unreachable.
Scientifically contradictory native results cause a failing job.

The two jobs run in parallel, with strict experiment steps and
artifact upload on failure (never continue-on-error). Neither changes
solver scheduling, rule order, performance gates, nor public API.
