# One-qubit Rust Path-sum vs independent matrix oracle

This is an independent **research-only** native Rust gate-semantic
audit. It does not change production Reduction Rules, WMC classification,
QASM transport, solver plugins or the current Qiskit dependency bounds.

## Verification method

For every supported one-qubit gate tested, construct the **unreduced**
native PathSum with automatic reductions disabled. Enumerate its input
bit, each fresh path variable and Boolean output polynomial. For every
assignment evaluate the exact rational-π phase polynomial and sum the
resulting complex amplitudes with the PathSum's own path normalization.

The reconstructed full two-by-two matrix is compared against **independent
closed-form formulas**:

- `U3(θ,φ,λ) = [[cos(θ/2), -exp(iλ) sin(θ/2)],
  [exp(iφ) sin(θ/2), exp(i(φ+λ)) cos(θ/2)]]`.
- `RX(θ) = [[c,-i s],[-i s,c]]`.
- `RY(θ) = [[c,-s],[s,c]]`.
- `RZ(θ) = diag(exp(-iθ/2), exp(iθ/2))`.

These tests include the **full complex unitary and scalar phase**, rather
than only global-phase-invariant overlap. Separate Ket and Bra tests
expect the forward unitary and its Hermitian adjoint, respectively. We
also crosscheck that U and U3 produce identical unreduced phase,
Boolean-map and path-variable structures.

All test angles are **small exact rational multiples of π**, such as
0, π/4, π/2, 3π/4 and -π/4. The source of the angular constants is
the native exact rational `Angle` representation: no QASM decimal-angle
parser or approximate transpiler is invoked. That separation is
deliberate; the tiny source-angle collapse identified elsewhere remains
an independent issue.

The test reconstruction uses ordinary double-precision complex
exponentials as a *numerical crosscheck of an algebraically constrained
path-sum*, with `1e-11` elementwise tolerance. It is **not** a formal
interval certificate for arbitrary input angles or arbitrary circuits.
The crucial distinction from the earlier U2/U3 structural test is that
two equally wrong implementations would **not** automatically pass:
the expected matrix here is independently specified rather than
derived from Rust's `apply_u`.

## Acceptance

The separate opt-in CI runs this native single-qubit matrix control
under both Qiskit 1.4.6 and 2.6.1 Python 3.12 environments, with
exact Git HEAD, package provenance, native test stdout and sealed SHA256
manifests. It also reruns the existing P/U1, U2 and source-safety
regression tests without modifying those production semantics.

If the test reports RED, preserve the unchanged negative evidence
before proposing a **minimal, independently reviewed** native fix. No
RED may be hidden behind an enlarged floating tolerance or an
unconditional `up-to-global-phase` acceptance. Parent source-safety
and U2 semantic PRs remain independent Drafts until their own merge
gates are satisfied.
