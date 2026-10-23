# Rust QASM tiny-angle semantic-loss diagnostic

This research-only RED isolates source-angle representation from the later
WMC near-unity numerical acceptance rule.

## Independent source oracle

For a one-qubit phase rotation, \`I\` is globally phase equivalent to
\`RZ(δ)\` only if \`δ\` is an integer multiple of \`2π\`.
Every fixture with \`0 < |δ| < 1\` radian is therefore **strictly
non-equivalent even up to global phase**.

The reference deliberately does not use an approximate \`Operator.equiv\`
tolerance. Decimal source literals are read as exact \`Fraction\` values.
For \`x = |δ|/2 ≤ 1/2\`, the rational bounds

\`\`\`
1 - x²/2 ≤ cos(x) ≤ 1 - x²/2 + x⁴/24 < 1    (x > 0)
\`\`\`

give a verifiable positive strict magnitude defect even for \`δ=10^-12\`.

## Native Rust stage isolated

The diagnostic runs the **unchanged** public
\`pathsum::qasm::parse_qasm_str\`, reads the parsed
\`QuantumOp::RZ\`'s \`Angle.constant\` numerator/denominator, and builds the
unreduced miter via \`VerificationStrategy::Naive.run\`. The output records
whether \`PathSum::is_identity()\` is true. This proves whether a source
angle was lost **before WMC**, without executing GPMC/Ganak or using any
\`WMC_MAGNITUDE_TOLERANCE\` setting.

Source fixtures include true zero, ±10^-12 radians, 10^-10, 4×10^-10,
10^-9, 10^-8 and 0.001 radians. They target both the source parser's
\`epsilon=1e-10\` zero test in *π units* and the continued-fraction
\`max_denom=10^9\` cap. These are independently observed from actual
Rust outputs; do not infer a universal cutoff from a handful of samples.

## Run and interpret

With Python 3.12, pytest, Cargo and the crate's build dependencies:

\`\`\`sh
python .diagnostics/rust_qasm_angle_red/run_boundary.py \
  --output .diagnostics/rust_qasm_angle_red/results
python -m pytest -q \
  .diagnostics/rust_qasm_angle_red/test_boundary.py::test_independent_exact_source_oracles \
  .diagnostics/rust_qasm_angle_red/test_boundary.py::test_true_zero_and_retained_angle_controls \
  .diagnostics/rust_qasm_angle_red/test_boundary.py::test_stage_attribution_controls
python -m pytest -vv \
  .diagnostics/rust_qasm_angle_red/test_boundary.py::test_nonzero_qasm_rotation_must_survive_rust_angle_conversion_red
\`\`\`

The first tests must pass for the experiment to be meaningful. The final
test deliberately has a **real failing assertion** when a nonzero source
rotation becomes a zero Rust \`Angle\`. No \`xfail\`, \`skip\`, tolerance
relaxation, or mocked solver error is allowed.

The dedicated opt-in workflow reports a genuinely failing scientific
check, while preserving the source QASM, actual Rust captured numerators,
phase-term counts, independent rational truth, JUnit, raw stdout and
SHA256 hashes.

No production code or published equivalence result is changed. This
diagnostic does not validate arbitrary QASM gate expressions, solver
roundoff, or the WMC classifier. A future production fix should separately
address the source-meaning representation and verify Python/Rust parity.
