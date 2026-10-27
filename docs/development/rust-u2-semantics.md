# Qiskit U2–U3 source-semantic parity

An audit of the post-paper Rust backend identified a scaling discrepancy:
the Rust `Angle` representation stores a rotation angle as `theta/pi`;
`Angle::QUARTER` therefore means **pi/4**, not **pi/2**.

By definition, `U2(phi,lambda) = U3(pi/2,phi,lambda)`.
The old Rust `apply_u2` calls `apply_u(qubit, Angle::QUARTER, phi, lambda, ...)`
and thus encodes a different gate.

The scientific regression checks **unsimplified native phase polynomial,
Boolean output map and allocated path variable structure**, separately on
Ket/Bra and at multiple rational-pi parameter pairs. This avoids
accidentally accepting two numerically close but distinct unitaries.
Public Python→Rust source-QASM integration also compares actual
`u2(phi,lambda)` with `u3(pi/2,phi,lambda)`; independent Qiskit
operator controls confirm that `pi/4` and `pi/2` are clearly distinct.

This work does **not** tune tolerance, change WMC/Hybrid execution,
or claim Qiskit2 package metadata support. The source-angle
`Angle::from_qasm_str` approximation is a separate constraint,
particularly for tiny arbitrary decimal radians. The original
paper-era implementation was Python-only, so this Rust correction
is **not** retroactive evidence about the historical paper code.

Use the opt-in `rust-u2-semantics.yml` workflow with pinned Qiskit
1.4.6 and 2.6.1 to capture native unit and public QASM validation, raw
logs, source HEAD/tree and SHA256 manifests. Scientific acceptance
requires the RED control to fail on the old `Angle::QUARTER` and turn
GREEN only after a minimal, local angle-unit correction.
