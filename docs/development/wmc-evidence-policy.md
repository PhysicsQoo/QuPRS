# Optional conservative policy for numerical WMC verdicts

QuPRS supports **two** interpretations of weighted-model-counting results.
The choice is per call and does not change the external solver, Path-sum,
reduction strategy, encoded CNF, configured tolerances or solver stdout.

## Motivation

GPMC and Ganak return floating complex counts. A normalized magnitude close
to one is useful **numerical evidence**, but is not a certificate that the
count has mathematical magnitude exactly one. The numerical interpretation
also has no externally verified general solver rounding bound, so counts
outside the default acceptance band are not automatically formally certified
counterexamples either.

For example, the identity and RZ(0.0002) are not equivalent even up to
global phase: their ideal normalized trace magnitude is cos(0.0001),
strictly less than one. The magnitude defect is approximately 5e-9, within
the current default 1e-8 numerical acceptance band. The actual WMC count
may differ because the solver does not supply a certified error enclosure.

Historically, the 1e-6 magnitude tolerance also admits identity versus
RZ(0.001), whose ideal magnitude defect is approximately 1.25e-7. The
current 1e-8 default does **not** admit this ideal trace. Specify
`wmc_magnitude_tolerance=1e-6` explicitly to recreate the old numerical
acceptance band; neither threshold establishes mathematical equality.

## API

```python
from qiskit import QuantumCircuit
from QuPRS import check_equivalence

identity = QuantumCircuit(1)
near = QuantumCircuit(1)
near.rz(0.0002, 0)

legacy = check_equivalence(
    identity, near, method="wmc_only", backend="python", tool_name="gpmc",
)
reviewed = check_equivalence(
    identity, near, method="wmc_only", backend="python",
    tool_name="gpmc", wmc_policy="conservative",
)

print(legacy.equivalent)               # Historical numerical classification.
print(reviewed.equivalent)             # "unknown" (not a proof of equality).
print(reviewed.wmc_numerical_verdict)  # Original numerical classification.
```

The `wmc_policy` keyword accepts `"legacy"` (default) or
`"conservative"`. Unsupported values raise `ValueError` before execution.

| Path | Legacy | Conservative |
| --- | --- | --- |
| WMC-only numeric verdict | original verdict | `unknown` and original in `wmc_numerical_verdict` |
| Hybrid with WMC fallback | original verdict | `unknown` and original in `wmc_numerical_verdict` |
| Hybrid without WMC / Reduction-only | unchanged RR result | unchanged RR result |
| Timeout, memory exhaustion, solver error | unchanged handling | unchanged handling |
| Different qubit counts | `not_equivalent` | `not_equivalent` |

Supported for **both Python and Rust at the public QuPRS entrypoint**,
without modifying Rust native internals. GPMC and Ganak continue running
independently. The numerical classification remains accessible for
diagnostic analysis without asserting a mathematically certified verdict.

**Important limitations:** This policy governs uncertified *external WMC
numeric* results only. It does **not** make the entire API a theorem prover:
Reduction can rely on symbolic numeric tolerances, Qiskit circuit objects
may already contain binary64-quantized angles, and exact source-decimal
propagation through Rust still reaches floating complex weights at the WMC
boundary. No general certified error bounds currently cover arbitrary
circuit encodings and external solver arithmetic.
`unknown` means insufficient evidence, **not** inequivalence.

The option remains non-default for compatibility while scientific
verification and numerical-proof contracts are developed. The separate
genuine near-identity scientific RED is deliberately unchanged.
