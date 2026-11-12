# Getting started

## Install the Python package

The v0.16.0 release line qualifies standard CPython 3.11, 3.12, 3.13, and 3.14. Python 3.14 is qualified with Qiskit 2.x; Qiskit 1.x is retained for compatible older Python environments and is not claimed on Python 3.14. Free-threaded Python 3.14t is not supported. Release-specific compatibility should be checked against the published version metadata. Wheels are built for Linux x86-64 and ARM64, and macOS 15 or later on Intel and Apple Silicon. Windows users should use a supported Linux environment such as WSL2.

Create a virtual environment and install the package:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install QuPRS
```

For macOS and Linux, see the [repository installation guide](https://github.com/PhysicsQoo/QuPRS#installation) for platform-specific requirements.

## Verify two circuits

```python
from qiskit import QuantumCircuit
from QuPRS import check_equivalence

original = QuantumCircuit(1)
optimized = QuantumCircuit(1)

result = check_equivalence(original, optimized, method="hybrid")
print(result.equivalent)
```

See the [fully tested examples](examples.md) for positive/negative controls, global phase, GPMC/Ganak selection, isolated Rust verification, and native CLI input.

## Rust users

The native [`quprs` Rust crate](https://crates.io/crates/quprs) is distributed separately from the Python package, with available versions listed on crates.io. The standalone CLI is built from the [Rust workspace](https://github.com/PhysicsQoo/QuPRS/tree/dev/rust), not installed by the Python wheel. For native RR, Hybrid and WMC-only use and external solver requirements, see [Native Rust and external solvers](rust-native.md); the standalone CLI has its own [example](examples.md#7-standalone-rust-cli).
