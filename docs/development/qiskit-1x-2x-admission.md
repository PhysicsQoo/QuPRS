# Qiskit 1.x / 2.x dual-major compatibility admission

## Scope

QuPRS declares `qiskit>=1.0.0,<3.0`, retaining the 1.x support claim while
admitting the 2.x major. Qiskit 3.x is **not** supported by this statement.
Supported interpreter releases remain Python 3.11–3.13. Python 3.14 is
evaluated separately. This change does **not** add general native QASM3
support; the Rust QASM3 subset is a separate gated feature.

The `pqc_generator` circuit library constructors are selected by capability:
new Qiskit releases provide callable `n_local`, `efficient_su2` and other
function constructors; Qiskit 1.0 exposes some modules with the same names
but requires legacy BlueprintCircuit classes. For legacy `NLocal`, use a
symbolic `RYGate(Parameter)` rotation block and a `CXGate` instance.
The established `pqc_generator` API, gate selection, and return triple are
unchanged.

## Pinned supporting evidence

- Native source/angle audit, 1.4.6 and 2.6.1: [Actions 39949138567](https://github.com/PhysicsQoo/QuPRS/actions/runs/39949138567)
- True clean Linux x86_64 wheel installation: [Actions 41665710296](https://github.com/PhysicsQoo/QuPRS/actions/runs/41665710296), Python 3.11–3.13 × Qiskit 1.4.6/2.6.1, 6/6
- Same-source native sdist installation: [Actions 41667021169](https://github.com/PhysicsQoo/QuPRS/actions/runs/41667021169), Qiskit 1.4.6/2.6.1, 2/2
- Real platform wheel installation: [Actions 41727599093](https://github.com/PhysicsQoo/QuPRS/actions/runs/41727599093), Linux ARM64 / macOS Intel / macOS Apple Silicon, two major versions per architecture, 3/3
- Qiskit lower-version regression found: [Actions 41728559783](https://github.com/PhysicsQoo/QuPRS/actions/runs/41728559783), Qiskit 1.0.0 failed the historical function-only import even though package dependency resolution was valid
- Candidate constructor compatibility with source-pinned wheel and 5 generator semantics + Python/Rust RR: [Actions 41730738840](https://github.com/PhysicsQoo/QuPRS/actions/runs/41730738840), Qiskit 1.0.0, 1.4.6, 2.0.0, 2.6.1 4/4

The above research artifacts were pinned to their *own* source trees;
the **combined integration commit** must also pass its exact-HEAD clean
resolver, public API and appropriate native CI before merging. Successful
installation and floating operator parity do not certify all arbitrary
decimal-angle or source-global-phase semantics.

## Explicit limitations

- Qiskit transpilation may remove tiny nonzero rotations at optimization
  levels 2/3; do not infer literal exact equivalence from a floating operator
  comparison.
- QASM2/QASM3 exporter scalar global-phase loss remains a source provenance
  concern. The existing Rust QASM2 bridge fails closed for unequal explicit
  `QuantumCircuit.global_phase` values.
- Full OpenQASM3 classical/dynamic operations, arbitrary source symbolic
  parameters and Python/Rust global-phase provenance require independent
  feature certification.
- Benchmark performance comparisons must come from CodSpeed, not different
  hosted CI runner wall times.
