# QuPRS — Rust quantum circuit equivalence verification

`quprs` is the native Rust library of [QuPRS](https://github.com/PhysicsQoo/QuPRS).
It checks quantum-circuit equivalence using symbolic path-sum reduction and,
when required, complex weighted model counting (WMC). Unlike the Python
distribution, it has no dependency on Qiskit or the Python runtime.

## Installation

After the crate is published, add it to `Cargo.toml`:

```toml
[dependencies]
quprs = "0.15.0"
```

The default `high-precision-gpmc` Cargo feature requires a C compiler,
`pkg-config` and installed GMP/MPFR development headers and libraries.
To omit that optional native precision bridge:

```toml
[dependencies]
quprs = { version = "0.15.0", default-features = false }
```

Disabling this feature does not remove the Hybrid or WMC-only methods.
It does not install a WMC solver.

## Solver-free reduction example

`ReductionRules` uses symbolic reduction without invoking GPMC or Ganak.
Reduction can be inconclusive (`Unknown`) when it cannot decide a circuit pair.

```rust
use quprs::{
    verification::check_equivalence, EquivalenceStatus, QuantumCircuit,
    VerificationMethod, VerificationOptions,
};

fn main() {
    let mut original = QuantumCircuit::new(1);
    original.h(0).expect("valid H gate");
    original.h(0).expect("valid H gate");
    let identity = QuantumCircuit::new(1);
    let options = VerificationOptions {
        method: VerificationMethod::ReductionRules,
        ..VerificationOptions::default()
    };
    let result = check_equivalence(&original, &identity, &options)
        .expect("RR verification");
    assert_eq!(result.status, EquivalenceStatus::Equivalent);
    assert!(!result.wmc_solver_invoked());
}
```

`QuantumCircuit` is a validated operation list, not the internal symbolic
`PathSum`. It accepts directly constructed gates and a supported unitary
subset of OpenQASM 2/3 through `from_qasm_str` / `from_qasm_file`.
Unsupported operations are rejected. Parameterized rotations use the
exact `quprs::rational::Angle` type instead of implicit `f64` rounding.

## Verification methods and external solvers

| Method | Behavior |
| --- | --- |
| `ReductionRules` | Symbolic reduction only; can return `Unknown` |
| `Hybrid` (default) | Reduce first, then use WMC if needed |
| `WmcOnly` | WMC path; simple cases may still complete analytically |

WMC requires external **GPMC** or **Ganak** executables for nontrivial counts.
Point to them via `QUPRS_GPMC_PATH` / `QUPRS_GANAK_PATH` or put them on
`PATH`. The registry-installed library does not bundle or download these
programs and does not silently switch solvers. An unavailable required
solver produces an error, not a verdict.

For example, with Ganak installed, this compares X against the identity:

```rust
use quprs::{
    check_equivalence_with_options, ir::QuantumOp,
    EquivalenceStatus, VerificationMethod, VerificationOptions,
};

fn main() {
    let options = VerificationOptions {
        method: VerificationMethod::WmcOnly,
        tool_name: "ganak".to_owned(),
        ..VerificationOptions::default()
    };
    let result = check_equivalence_with_options(
        1, &[QuantumOp::X(0)], &[], &options
    ).expect("requires a working Ganak executable");
    assert_eq!(result.status, EquivalenceStatus::NotEquivalent);
    assert!(result.wmc_solver_invoked());
}
```

To use real GPMC in Hybrid mode, keep `VerificationMethod::Hybrid`
(the default), select `tool_name: "gpmc"`, and make GPMC available.
A single Hadamard compared against the identity is a verified example
that reaches the external solver after reduction.

## Interpreting results

`EquivalenceCheckResult::status` is a typed `EquivalenceStatus`:
`Equivalent`, `EquivalentUpToGlobalPhase`, `NotEquivalent`,
`Unknown`, `Timeout` or `MemoryOut`. An inconclusive status is
**not** proof of non-equivalence. `wmc_solver_invoked()` tells you
whether an actual external process was used.

`VerificationOptions` separates RR coefficient-matching tolerance
(`rr_tolerance`, default `1e-10`), phase tolerance (`phase_tolerance`,
default `1e-8` radians), and projective-distance tolerance
(`approximate_distance_tolerance`, default `Some(1e-8)`).
GPMC supports `gpmc_precision_digits` of `30` (default) or `90`.
Solver print precision alone does **not** certify numerical error bounds.

For the full contract, consult the
[Rust API reference](https://docs.rs/quprs/).

## Building from source

`QUPRS_SOLVER_PROVISION=auto` installs pinned solvers only for a
recognized QuPRS source checkout. A registry-extracted crate expects
external solver executables; `QUPRS_SOLVER_PROVISION=external` explicitly
disables source provisioning. This setting affects distribution only,
not the choice of verification method.

- [Project repository](https://github.com/PhysicsQoo/QuPRS)
- [Project documentation](https://physicsqoo.github.io/QuPRS/docs/dev/)
- [Rust API documentation](https://docs.rs/quprs/)

License: [MIT](https://github.com/PhysicsQoo/QuPRS/blob/main/LICENSE.md).
