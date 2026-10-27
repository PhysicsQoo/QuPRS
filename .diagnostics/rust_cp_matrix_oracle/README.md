# Controlled phase: exact two-qubit source/PathSum oracle

This independent diagnostic validates the actual Rust QASM2 `CP(theta)`
lowering in a source-pinned, deliberately small family. Unlike checking
`CP` against another decomposed `P/CX` circuit or a floating WMC count,
the verifier computes the **unreduced native PathSum's phase function**
for **every one of the four computational-basis inputs**.

For any input `b0,b1 in {0,1}`, the exact controlled-phase matrix is
`diag(1,1,1,exp(i*theta))`. Since PathSum phase coefficients are
normalized to a full `2*pi` cycle, the expected coefficient is
`(theta / (2*pi)) * b0*b1 (mod 1)`, with no other phase contribution.

The Rust diagnostic requires **no fresh path variables**, verifies
that all two-qubit Boolean outputs equal the respective inputs and
sums every activated phase-polynomial monomial using the existing
exact modulo-one `Rational` type (not floating tolerance). It checks
`CP(pi)`, `CP(pi/2)`, `CP(pi/4)`, `CP(-pi/2)`, both control/target
orders and the conjugated Bra pathway. Negative controls verify that
nonzero CP was not erased, and a consecutive `CP(pi/2) CP(-pi/2)`
returns exact identity. An independent `CZ` gate is used as a second
reference for `CP(pi)`.

**Limits:** This is a formal finite-state audit only for the specified
rational multiples of pi. It relies on `Angle::from_qasm_str` resolving
those simple expressions as intended, and on the Rust PathSum's exact
phase arithmetic. It does not validate arbitrary source decimal
radians, general QASM semantics, external floating GPMC/Ganak
arithmetic, or multiqubit circuits with path-variable-generating
Hadamards. It does not touch the public API or package requirements.

The new opt-in workflow records the exact source HEAD/tree, successful
native Rust regression logs and an independently checkable SHA256
manifest. This research change is stacked on the CP parser branch;
it should not be merged until its strict-parser and corrected P/U1
phase dependencies are accepted.
