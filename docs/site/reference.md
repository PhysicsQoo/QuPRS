# API Reference

## Python

The principal public Python entry point is `QuPRS.check_equivalence()`, which accepts supported Qiskit circuits and QASM inputs. Python imports and the documented function signature are maintained in the [public Python package](https://github.com/PhysicsQoo/QuPRS/tree/dev/src/QuPRS).

## Rust

The native verification library is the `pathsum` crate in the [Rust workspace](https://github.com/PhysicsQoo/QuPRS/tree/dev/rust/pathsum). Its API is documented through Rust's native `cargo doc` output.

## Command-line interface

The standalone Rust command-line program is built from the [CLI workspace member](https://github.com/PhysicsQoo/QuPRS/tree/dev/rust/cli) and is not part of the PyPI wheel installation.
