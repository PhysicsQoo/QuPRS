# Native Rust verification and external WMC solvers

QuPRS provides a native Rust API for Path-sum reduction and complex weighted
model counting. The Rust core supports three verification methods:
`ReductionRules`, `Hybrid` (reduction followed by WMC when needed), and
`WmcOnly`. GPMC is the default external WMC solver; Ganak may be chosen
explicitly. The crate does not silently switch solvers.

**Distribution:** the native [`quprs` crate](https://crates.io/crates/quprs)
is distributed separately from the Python package. The available versions
are listed on [crates.io](https://crates.io/crates/quprs/versions). The native
library is also maintained in the
[QuPRS source workspace](https://github.com/PhysicsQoo/QuPRS/tree/dev/rust).

## Build with full verification capability

On Linux, install CMake, pkg-config, a C/C++ compiler, and GMP/MPFR development
headers. On macOS, the corresponding dependencies are available with Homebrew:

```sh
brew install cmake pkg-config gmp mpfr zlib
```

Clone the repository and its native GPMC dependency:

```sh
git clone --recurse-submodules https://github.com/PhysicsQoo/QuPRS.git
cd QuPRS
cargo test --manifest-path rust/Cargo.toml -p quprs
```

The **default monorepo build** currently provisions the pinned GPMC/Ganak
executables and integrates with the Python wheel. It is not the isolated
crate installation path.

For a source-only Rust build that **does not download or build the
WMC solvers**, set the explicit provisioning mode (not a Cargo feature):

```sh
QUPRS_SOLVER_PROVISION=external cargo check --manifest-path rust/Cargo.toml -p quprs \
  --all-features
```

This preserves the full verification API and the high-precision MPFR
weight bridge while delegating solver installation to the user.
It does not reduce QuPRS to RR-only.

## Provide external GPMC and Ganak executables

The QuPRS source checkout uses the **GPMC v1.0.2 public CLI Release**,
pinned by exact archive SHA256 and producer source commit in
[`gpmc-release.txt`](https://github.com/PhysicsQoo/QuPRS/blob/dev/src/QuPRS/utils/gpmc-release.txt).
It does not need a nested GPMC source checkout. The installed binary is
written to `src/QuPRS/utils/wmc_tools/gpmc` (or `gpmc.exe` on Windows).

The published CLI has **external runtime dependencies**. On Ubuntu 22.04+
it uses `libmpfr.so.6` and a glibc 2.35 minimum; macOS requires the
matching Homebrew GMP/MPFR libraries. These requirements also apply when
building Python source wheels that embed the executable. A Linux wheel
targeting an older glibc baseline must not be described as end-to-end
solver-compatible merely because the Python extension loads.

To verify the official archive and install its CLI explicitly:

```sh
python3 scripts/install_gpmc_release.py --verify-only
python3 scripts/install_gpmc_release.py --dest /absolute/path/to/gpmc
export QUPRS_GPMC_PATH="/absolute/path/to/gpmc"
```

The original GPMC code remains available in its
[independent source repository](https://github.com/PhysicsQoo/GPMC)
for users who need to compile against an older system ABI.

For Ganak, install a compatible executable from the
[upstream Ganak releases](https://github.com/meelgroup/ganak/releases).
QuPRS pins the supported Ganak 2.8.0 assets and their archive and
executable SHA256 checksums in
[`ganak-release.txt`](https://github.com/PhysicsQoo/QuPRS/blob/dev/src/QuPRS/utils/ganak-release.txt).
Choose the matching operating system and architecture, verify the
download and executable checksums, then configure its absolute path:

```sh
export QUPRS_GANAK_PATH="/absolute/path/to/ganak"
```

The source-checkout default can provision its pinned solvers for the
existing Python/CLI build; the staged registry crate never downloads them.
Use `QUPRS_SOLVER_PROVISION=external` in a source checkout to opt out.
Do not download binaries during a registry consumer's `cargo build`. Using an explicit solver
path is an **override**, not proof that the executable matches a
pinned artifact. Only use binaries obtained from trusted sources and
verified against the relevant release manifest. An override that cannot
be verified must not be represented as a certified native solver build.

The external-solver Rust implementation also supports resolving
`gpmc` or `ganak` from `PATH` when no explicit path is supplied.
A missing executable causes a solver execution error, **not**
`NotEquivalent`, and there is no automatic cross-solver fallback.

## Use the Rust API

The canonical Rust package and library are `quprs`. The high-level
`quprs::verification::check_equivalence` accepts two validated
`QuantumCircuit` inputs and `VerificationOptions`.

### Start with ReductionRules (no external WMC executable)

This complete Rust example compares two Hadamard gates with the identity.
`ReductionRules` never starts GPMC or Ganak. Build-time provisioning is a
separate setting: `QUPRS_SOLVER_PROVISION=external` avoids installing
solvers in a source checkout without removing any verification methods.

```rust
use quprs::{
    EquivalenceStatus, QuantumCircuit, VerificationMethod, VerificationOptions,
};
use quprs::verification::check_equivalence;

fn main() {
    let mut original = QuantumCircuit::new(1);
    original.h(0).expect("valid H");
    original.h(0).expect("valid H");
    let identity = QuantumCircuit::new(1);

    let options = VerificationOptions {
        method: VerificationMethod::ReductionRules,
        ..VerificationOptions::default()
    };
    let result = check_equivalence(&original, &identity, &options)
        .expect("valid comparison");
    assert_eq!(result.status, EquivalenceStatus::Equivalent);
    assert!(!result.wmc_solver_invoked());
}
```

With a source checkout, use `rust/pathsum` as the local path dependency
(whose Cargo package name is `quprs`). Irreducible RR-only comparisons
can return `EquivalenceStatus::Unknown`, not a proof of inequality.

### Extend to Hybrid and WmcOnly with external solvers

To perform WMC, first install GPMC or Ganak as described above and provide
its executable through `QUPRS_GPMC_PATH`, `QUPRS_GANAK_PATH`, or `PATH`.
This example runs Hybrid with GPMC, followed by WMC-only with Ganak:

```rust
use quprs::{
    EquivalenceStatus, QuantumCircuit, VerificationMethod, VerificationOptions,
};
use quprs::verification::check_equivalence;

fn main() {
    let identity = QuantumCircuit::new(1);
    let mut h = QuantumCircuit::new(1);
    h.h(0).expect("valid H");

    let hybrid = check_equivalence(
        &h, &identity, &VerificationOptions::default(),
    ).expect("GPMC must be installed");
    assert_eq!(hybrid.status, EquivalenceStatus::NotEquivalent);
    assert!(hybrid.wmc_solver_invoked());

    let mut x = QuantumCircuit::new(1);
    x.x(0).expect("valid X");
    let options = VerificationOptions {
        method: VerificationMethod::WmcOnly,
        tool_name: "ganak".to_owned(),
        ..VerificationOptions::default()
    };
    let wmc = check_equivalence(&x, &identity, &options)
        .expect("Ganak must be installed");
    assert_eq!(wmc.status, EquivalenceStatus::NotEquivalent);
    assert!(wmc.wmc_solver_invoked());
}
```

These assertions are for the shown circuits, **not** a solver-arithmetic
certificate for arbitrary inputs. Missing solvers, invalid inputs and solver
failures return errors; there is no automatic solver fallback.

### VerificationOptions: defaults, units and validation

The native verifier validates these fields on each request:

| Rust field | Default | Valid values or meaning |
| --- | --- | --- |
| `method` | `Hybrid` | `ReductionRules`, `Hybrid`, `WmcOnly`; runtime method, not a Cargo feature |
| `strategy` | `Difference` | Also `Proportional`, `Naive`, `Straightforward` |
| `tool_name` | `"gpmc"` | `"gpmc"` or `"ganak"`, no implicit fallback |
| `timeout_secs` | `600` | Requested seconds; in-process symbolic work is not guaranteed a hard whole-call deadline |
| `rr_tolerance` | `1e-10` | Finite, nonnegative matching threshold; not radians |
| `phase_tolerance` | `1e-8` | Global-phase threshold in **radians**; finite and strictly between 0 and 1 |
| `wmc_phase_tolerance` | `1e-8` | Compatibility alias of the same phase threshold, in **radians** |
| `approximate_distance_tolerance` | `Some(1e-8)` | Projective Hilbert–Schmidt **distance**, finite `0 < x < 1`; `None` also selects the `1e-8` default, not “off” |
| `gpmc_precision_digits` | `30` | `30` or `90`; `90` applies to GPMC only |

Change **one** of `phase_tolerance` or `wmc_phase_tolerance` and
leave the other at its default `1e-8`; if both are non-default and
different, native validation returns an error. The fields do not create
two independent phase classifications.

The RR matching tolerance is not an angle threshold, and projective
distance is not radians or raw trace-magnitude error. Solver printed
30/90 digits are **not** a certified bound on numerical arithmetic error.

### QuantumCircuit, PathSum, and source-preserving Angle

`QuantumCircuit` holds an owned, validated sequence of `QuantumOp`
gates and a register width. It is **not** a symbolic `PathSum`;
the verifier constructs symbolic Path-sums and reduces them internally.
Use `result.final_pathsum()` to borrow the remaining symbolic residual.

`QuantumCircuit::from_qasm_str` and `from_qasm_file` accept the
supported unitary OpenQASM 2/3 subset, rejecting unsupported operations.
Supported decimal radian literals remain exact rational terms and `pi`
factors remain symbolic in `Angle` rather than silently becoming `f64`.
The Rust rotation helpers require `Angle`:

```rust
use quprs::{rational::Angle, QuantumCircuit};

fn main() {
    let angle = Angle::from_qasm_str("1.2345678901234567")
        .expect("supported exact angle");
    let mut direct = QuantumCircuit::new(1);
    direct.rz(0, angle).expect("valid RZ");
    let qasm = QuantumCircuit::from_qasm_str(
        "OPENQASM 3.0;\nqubit[1] q;\nrz(1.2345678901234567) q[0];\n"
    ).expect("supported QASM");
    assert_eq!(direct, qasm);
}
```

An unsupported QASM operation or arbitrary unbound Qiskit expression is
not silently approximated by the native Rust circuit type.

### Read the native result

Rust keeps `result.status: EquivalenceStatus` as an enum;
`result.equivalent()` returns the Python-compatible verdict spelling
(`equivalent`, `equivalent*`, `not_equivalent`, `unknown`,
`Timeout`, `MemoryOut`). `wmc_solver_invoked()`, `gate_num()`
and `final_pathsum()` are read-only, non-copying accessors corresponding
to Python attributes of those names.

Unlike Python's Qiskit wrapper, which returns `not_equivalent` for
unequal circuit widths, native Rust rejects mismatched widths as an
**input-validation error** before solver invocation. `Unknown`,
`Timeout`, `MemoryOut` and execution errors do not prove inequality.

A standalone Rust consumer uses the same `quprs::` imports as the source
workspace. Select a version listed on
[crates.io](https://crates.io/crates/quprs) and replace `VERSION` with it:

```sh
cargo add quprs@VERSION
```

The published crate contains the native verification API but does not bundle
GPMC or Ganak executables for nontrivial weighted model counting.

## Build and runtime contracts

- The isolated full-verification crate does not package GPMC or Ganak
  executables or install them automatically.
- The high-precision MPFR feature requires system GMP/MPFR libraries and
  headers; disabling it changes the available source-weight precision
  behavior and is not equivalent to the full high-precision configuration.
- Timeouts, memory protection and error reporting follow the native
  Rust solver process contracts, subject to the documented platform
  limitations. A timeout or inconclusive count is not a non-equivalence
  proof.
- Windows is not part of QuPRS's current supported native release
  matrix. Use a supported Linux environment such as WSL2.

See [weighted model counting](weighted-model-counting.md) for
numerical-verdict limitations and [verification methods](verification.md)
for the algorithmic distinction between RR, Hybrid and WMC-only.
