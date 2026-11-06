# Upgrading from QuPRS v0.14.1 to v0.15.0 (development preview)

**Release status:** v0.15.0 is not yet published. This document describes
features merged to `dev`, not a promise that they are available in the
current `pip install QuPRS` stable release. For the latest officially
published behavior see [v0.14.1](https://github.com/PhysicsQoo/QuPRS/releases/tag/v0.14.1)
and the [CHANGELOG](../../CHANGELOG.md). The final v0.15.0 compatibility
statement will be checked against its protected main release tag.

## What changes

The existing top-level `QuPRS.check_equivalence` Python API remains the
entry point. With `backend="rust"`, the optional `safe_mode=True` request
runs the same native verifier in a separate supervised process, retaining
the normal `EquivalenceCheckResult` shape. It does not switch Python to
the standalone Rust CLI. The default remains the fast in-process route.
See the [isolation contract](../python_rust_isolation.md) for precise
timeout, memory and macOS/Linux process-cleanup limitations.

Public documentation now includes source-derived Python class and
Path-sum gate interfaces, generated `core.pyi` and packaged `py.typed`,
native Rustdoc, runnable examples and the verified theory of Elim/HH/Omega
with explicit preconditions. The version selector will keep a mutable
development site separate from immutable official tags, with the first
versioned official site starting at v0.15.0; v0.14.x will not be backfilled.

## What does not change

- The supported Python versions remain 3.11, 3.12 and 3.13; the declared
  Qiskit range remains `>=1.0.0,<3.0`. No claim is made for Python
  3.14/3.14t or Qiskit 3.x.
- Supported package targets remain Linux x86-64/ARM64 and macOS 15+ on Intel
  and Apple Silicon. The Python wheel does **not** install the standalone
  `QuPRS_cli` binary.
- Solver names remain GPMC and Ganak, selected explicitly. There is no
  automatic solver fallback or unconditional numerical exactness certificate.
- `rr_tolerance` controls local reduction matching, `phase_tolerance`
  controls the global-phase label in radians, and
  `approximate_distance_tolerance` controls the projective distance.
  None is a substitute for another; `unknown`, timeout, resource failure
  or malformed solver output is not proof of inequivalence.

## Before upgrading

1. Review calls that explicitly request `safe_mode=True`; keep the default
   `False` when process isolation is not required.
2. Ensure your interpreter, Qiskit version and wheel platform fall in the
   declared supported set. For unsupported platforms, do not infer support
   from an unrelated runner or experimental source build.
3. Re-run representative EQ/NEQ/global-phase fixtures with the same
   solver, tolerance settings and source inputs. Use the
   [public executable examples](https://physicsqoo.github.io/QuPRS/docs/dev/examples/)
   as development illustrations, not as evidence of a released v0.15.0
   package.
4. After the official tag is released, install the tagged wheel or sdist,
   then verify its version and its matching published documentation.

An official release requires a protected `dev→main` acceptance of
source correctness and installed artifacts; a green development docs
preview alone is not release approval.
