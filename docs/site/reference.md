# API Reference

QuPRS exposes a Python API, a native Rust library, and a separate Rust command-line program. Their public interfaces and available input formats differ.

## Python API

The user-facing Python entry point is `QuPRS.check_equivalence()` (import it with `from QuPRS import check_equivalence`). Its signature and return object are generated from the implementation:

[General Python API Reference](python-api.md)

For the lower-level symbolic Path-sum, output mapping, dynamic gate methods,
and reduction statistics, consult the
[Advanced Path-sum API Reference](pathsum-api.md). Its gate signatures are
extracted from the source-generated `core.pyi` stub without importing or
executing QuPRS during the documentation build.

## Rust library

The native `pathsum` crate provides its own typed verification API. It is documented with Rust's `cargo doc` tool.

<a href="rust-api/quprs/index.html">Rust crate API Reference</a>

Rustdoc is generated separately from the same source revision as this website. A local Zensical-only preview does not contain the Rustdoc subtree until the Rust documentation build has run.

## Rust command-line interface

The Rust CLI is a distinct workspace member and is not installed as a standalone executable by the Python wheel. Consult the [Rust workspace](https://github.com/PhysicsQoo/QuPRS/tree/dev/rust) for the native project layout.

For dispatch, solver supervision, and numerical behavior across the interfaces, see [Architecture](architecture.md).
