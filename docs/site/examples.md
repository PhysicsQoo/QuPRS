# Executable examples

These complete examples use the public interfaces. Each Python block is run independently by the documentation examples check using the current source build, and the shell block is checked against the native CLI. Start with [installation](getting-started.md).

All examples use one qubit so that their expected classifications are easy to audit. A timeout, solver error or `unknown` status is **not** equivalent to a successful inequality result.

## 1. Exact-equivalence control (reduction rules)

Two Hadamard gates cancel. This comparison needs no external model counter.

```python
from qiskit import QuantumCircuit
from QuPRS import check_equivalence

original = QuantumCircuit(1)
optimized = QuantumCircuit(1)
optimized.h(0)
optimized.h(0)

result = check_equivalence(original, optimized, method="reduction_rules",
                           backend="python", timeout=30)
assert result.equivalent == "equivalent", result.equivalent
assert result.wmc_solver_invoked is False
```

## 2. Inequivalent control (reduction rules)

An X gate changes the basis-state mapping relative to the identity. This is not a global phase.

```python
from qiskit import QuantumCircuit
from QuPRS import check_equivalence

original = QuantumCircuit(1)
different = QuantumCircuit(1)
different.x(0)

result = check_equivalence(original, different, method="reduction_rules",
                           backend="python", timeout=30)
assert result.equivalent == "not_equivalent", result.equivalent
```

## 3. Global phase is a separate classification

A scalar phase changes the operator but not its action on measurement probabilities. `equivalent*` is distinct from exact `equivalent`.

```python
from math import pi
from qiskit import QuantumCircuit
from QuPRS import check_equivalence

original = QuantumCircuit(1)
phase_shifted = QuantumCircuit(1)
phase_shifted.global_phase = pi / 2

result = check_equivalence(original, phase_shifted, method="reduction_rules",
                           backend="python", timeout=30)
assert result.equivalent == "equivalent*", result.equivalent
```

## 4. WMC-only and explicit solver selection

The gates below differ by a nontrivial relative phase. The projective distance between `I` and `RZ(0.2)` is `|sin(0.1)|`, much larger than the default numerical tolerance.

Each selected solver is called explicitly; the program does not silently fall back from one to the other.

```python
from qiskit import QuantumCircuit
from QuPRS import check_equivalence

original = QuantumCircuit(1)
different = QuantumCircuit(1)
different.rz(0.2, 0)

for solver in ("gpmc", "ganak"):
    result = check_equivalence(
        original, different,
        method="wmc_only", backend="python", tool_name=solver,
        approximate_distance_tolerance=1e-8, timeout=30,
    )
    assert result.equivalent == "not_equivalent", (solver, result.equivalent)
    assert result.wmc_solver_invoked is True, solver
    assert result.wmc_numerical_verdict is not None, solver
```

A WMC verdict is a finite-precision *observation* rather than a certificate of source-exact equivalence. Inspect `wmc_solver_invoked` and `wmc_numerical_verdict` separately; a reached WMC stage may still use an analytic shortcut instead of spawning a solver.

## 5. Python interface to the isolated Rust backend

`backend="rust"` calls the Rust engine through PyO3. Enabling `safe_mode` executes that extension in a supervised child process, **not** through the standalone Rust CLI. Isolation does not make parent-side circuit serialization preemptible and is not a universal memory guarantee.

```python
from qiskit import QuantumCircuit
from QuPRS import check_equivalence

original = QuantumCircuit(1)
optimized = QuantumCircuit(1)
optimized.x(0)
optimized.x(0)

result = check_equivalence(original, optimized, method="reduction_rules",
                           backend="rust", safe_mode=True, timeout=30)
assert result.equivalent == "equivalent", result.equivalent
```

## 6. Fail closed on inconclusive results

The example below tests the **consumer's status-handling policy**. The
`SimpleNamespace` values simulate possible result statuses; they are not
claims that the trivial test circuit can produce a real timeout or unknown
solver result. Real timeout and resource supervision have separate runtime
tests.

```python
from types import SimpleNamespace
from qiskit import QuantumCircuit
from QuPRS import check_equivalence

original = QuantumCircuit(1)
optimized = QuantumCircuit(1)
optimized.h(0)
optimized.h(0)
result = check_equivalence(original, optimized, method="reduction_rules",
                           backend="python", timeout=30)

def classify(result):
    status = result.equivalent
    if status in {"unknown", "Timeout", "MemoryOut"}:
        return "inconclusive"
    if status in {"equivalent", "equivalent*"}:
        return "equivalent"
    if status == "not_equivalent":
        return "not_equivalent"
    raise ValueError(f"Unsupported verification status: {status}")

assert classify(result) == "equivalent"
for status in ("unknown", "Timeout", "MemoryOut"):
    assert classify(SimpleNamespace(equivalent=status)) == "inconclusive"
assert classify(SimpleNamespace(equivalent="not_equivalent")) == "not_equivalent"
```

## 7. Standalone Rust CLI

For a source checkout with native dependencies installed, run the Rust CLI using QASM2 files. Its command-line options are not Python API arguments, and installing the Python wheel does not install a standalone CLI command.

```bash
set -eu
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
cat > "$scratch/identity.qasm" <<'QASM'
OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
QASM
cat > "$scratch/two-h.qasm" <<'QASM'
OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
h q[0];
h q[0];
QASM
status="$(cargo run --quiet --locked --manifest-path rust/Cargo.toml -p QuPRS_cli -- \
  "$scratch/identity.qasm" "$scratch/two-h.qasm" --method reduction-rules --quiet)"
test "$status" = "equivalent"
```

For other supported inputs and options, see the [Python API](python-api.md), [verification methods](verification.md), [solver contract](weighted-model-counting.md) and [architecture](architecture.md). Results may be `unknown` or resource-limited; callers must handle those states explicitly rather than treating them as `not_equivalent`.
