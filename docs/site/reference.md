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

The native `quprs` crate provides its own typed verification API. It is documented with Rust's `cargo doc` tool. Start with the [native Rust guide](rust-native.md) for a solver-free example, validated options, and the distinction between `QuantumCircuit` and `PathSum`.

<a href="rust-api/quprs/index.html">Rust crate API Reference</a>

Rustdoc is generated separately from the same source revision as this website. A local Zensical-only preview does not contain the Rustdoc subtree until the Rust documentation build has run.

**Choosing a Rust API version:** QuPRS adds a small version selector to newly generated native Rustdoc pages, using the same `docs/versions.json` manifest as the main documentation. The selector navigates to the selected version's crate root rather than assuming item URLs are stable across releases. The Rustdoc search, sidebar and native layout are unchanged. Historical versioned Rustdoc pages created before this feature are retained unchanged and may not contain the selector; use the main documentation's version menu or the [published versions](https://crates.io/crates/quprs/versions) in that case.

## Rust command-line interface

The Rust CLI is a distinct workspace member and is not installed as a standalone executable by the Python wheel. Consult the [Rust workspace](https://github.com/PhysicsQoo/QuPRS/tree/dev/rust) for the native project layout.

For dispatch, solver supervision, and numerical behavior across the interfaces, see [Architecture](architecture.md).
