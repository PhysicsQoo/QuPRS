# QuPRS

**QuPRS** checks equivalence of quantum circuits using Path-sum reduction and weighted model counting (WMC).

The project provides a Python interface for Qiskit circuits, a native Rust verification library, and a separately built Rust command-line program.

- [Getting started](getting-started.md) explains installation and supported environments.
- [Executable examples](examples.md) provide small runnable equivalence, inequality, global-phase, solver, and Rust CLI cases.
- [Verification](verification.md) introduces the available verification methods and result semantics.
- [Path-sum theory](path-sum.md) and [weighted model counting](weighted-model-counting.md) explain the algorithms and numerical evidence.
- [API Reference](reference.md) links the generated Python and Rust documentation.
- [Architecture](architecture.md) describes the relationship between the Python and native Rust interfaces.

Source code, releases, and contribution instructions are available in the [QuPRS repository](https://github.com/PhysicsQoo/QuPRS).
