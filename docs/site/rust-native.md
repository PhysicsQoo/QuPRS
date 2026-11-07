# Native Rust verification and external WMC solvers

QuPRS provides a native Rust API for Path-sum reduction and complex weighted
model counting. The Rust core supports three verification methods:
`ReductionRules`, `Hybrid` (reduction followed by WMC when needed), and
`WmcOnly`. GPMC is the default external WMC solver; Ganak may be chosen
explicitly. The crate does not silently switch solvers.

**Current distribution:** the supported Rust core is built from the
[QuPRS source workspace](https://github.com/PhysicsQoo/QuPRS/tree/dev/rust).
The registry package name `quprs` is planned but not yet claimed;
**a crates.io release has not been published**. Do not mistake a preview
archive for an available crates.io package.

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

To build GPMC separately, use the versioned
[GPMC source repository](https://github.com/PhysicsQoo/GPMC) and its
[installation instructions](https://github.com/PhysicsQoo/GPMC/blob/master/INSTALL.md).
The normal QuPRS source checkout pins the GPMC submodule revision. A
release build of that checked-out submodule typically produces
`GPMC/bin/gpmc`:

```sh
(cd GPMC && ./build.sh r)
export QUPRS_GPMC_PATH="$(pwd)/GPMC/bin/gpmc"
```

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

The canonical source workspace crate and library are named `quprs`:

```rust
use quprs::{
    EquivalenceStatus, QuantumCircuit, VerificationMethod, VerificationOptions,
};
use quprs::verification::check_equivalence;

let mut original = QuantumCircuit::new(1);
original.h(0)?;
let optimized = QuantumCircuit::new(1);

let options = VerificationOptions {
    method: VerificationMethod::Hybrid,
    ..VerificationOptions::default()
};
let result = check_equivalence(&original, &optimized, &options)?;
assert_eq!(result.status, EquivalenceStatus::NotEquivalent);
assert_eq!(result.equivalent(), "not_equivalent");
assert!(result.wmc_solver_invoked());
```

The snippet assumes it is placed inside a Rust function returning
`anyhow::Result<()>` and that a valid GPMC executable is available.
`QuantumCircuit::from_qasm_str(source)` and
`QuantumCircuit::from_qasm_file(path)` use the same strict unitary
OpenQASM parser as the existing Rust CLI and preserve exact source angles.
For more gate variants, use `QuantumCircuit::push(QuantumOp::...)`, which
validates wire indices and preserves the native `Angle` representation.

The Rust result provides Python-name compatibility methods:
`equivalent()`, `wmc_solver_invoked()`, `final_pathsum()` and
`gate_num()`. They are read-only accessors on the original typed result,
with no duplicated status state or Path-sum copy. Unlike Python's Qiskit
wrapper, which returns `not_equivalent` for differing register widths,
the typed Rust façade rejects that invalid comparison before invoking
a solver and does not fabricate a final symbolic residual.

An independent consumer of the eventually released registry package
uses the same `quprs::...` imports as the source workspace. The package is
not yet released on crates.io.

`VerificationOptions::default()` selects Hybrid, GPMC, 30 solver
decimal digits and the existing tolerance defaults. Explicit GPMC
90-digit solver mode is supported, but **solver print precision is not
a proof of exact or certified numerical error bounds**. Ganak's
printed precision may be insufficient for tight thresholds.
Use `solver_invoked` to distinguish a genuine external solver call
from a reduction or exact analytic shortcut.

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
