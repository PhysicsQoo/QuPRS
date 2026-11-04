# CPython 3.14 lightweight compatibility — 2026-11-04

## Scope and provenance

- Source: `dev@e1c551d5a337ea5cdac5d4e87b6b53c6fa486821` with research-only workflow/probe corrections.
- Measured probe SHA: `d4429d4aecb047d6fc42c5cec75070cdcaae1ade`.
- Workflow run: https://github.com/PhysicsQoo/QuPRS/actions/runs/41743839572
- Linux: GitHub-hosted Ubuntu 24.04 x86_64; standard CPython 3.14 (GIL), **not** free-threaded.
- Wheel build: Python 3.12 + Rust/PyO3 0.21.2 with `abi3-py38`; wheel `quprs-0.13.4-cp38-abi3-linux_x86_64.whl`; SHA256 `9e2dcb291db13665930d0817b2a8a9baeb0342dd127d9120a81880f35b751c01`.
- Wheel artifact: https://github.com/PhysicsQoo/QuPRS/actions/runs/41743839572/artifacts/13281384917
- Installation: exact locally built wheel, `pip install --only-binary=:all:` in clean CPython 3.14 jobs, with pinned Qiskit versions and `pip check`. No installed QuPRS package was obtained from PyPI.

## Evidence

| Phase | Qiskit 2.6.1 | Qiskit 1.4.6 |
| --- | --- | --- |
| Clean CPython 3.14 resolver / installed local wheel | PASS | FAIL (no compatible binary SymEngine for Qiskit 1.4.6) |
| `pip check` | PASS | Not reached |
| PyO3 `abi3` extension import | PASS | Not reached |
| SymEngine symbolic expansion, QASM2/QASM3 parsing | PASS | Not reached |
| Python/Rust RR; Python/Rust real GPMC and Ganak EQ/NEQ | PASS (9 standalone probe cases, including safe mode) | Not reached |
| Source-matched existing pytest contracts | **29 passed** | Not reached |

The successful CPython interpreter reported `3.14.9`, and resolver installed:
`QuPRS==0.13.4`, `qiskit==2.6.1`, `qiskit-qasm3-import==0.6.0`,
`numpy==2.5.4`, `symengine==0.15.0`, `sympy==1.14.0`,
`psutil==7.2.2`, `pytest==8.4.2`.
The imported extension path ended in `QuPRS/_pathsum_rust.abi3.so`.

The probe performed 2 Python/Rust RR H-H controls, 6 real solver invocations across
Python/Rust, GPMC/Ganak, `wmc_only`/`hybrid` with EQ and NEQ at
`approximate_distance_tolerance=2e-4`, and 1 Python `safe_mode=True`
spawn control. All expectations matched. The real solver cases are **numerical**
classifications at that requested threshold, not claims of strict equivalence
for different rotations.

The Pytest scope was `test_RR.py`, the Qiskit 1.x/2.x constructor compatibility
module, RR tolerance exact-decimal parity, QASM3 Python/Rust Bell/decimal,
Python QASM3 global phase, packaged Ganak provenance and Python solver lifecycle.
It is a representative subset, not the complete Python test suite.

**Qiskit 1.4.6 failure:** its dependency metadata requires
`symengine>=0.11,<0.14`. For CPython 3.14, the explicitly binary-only
resolver found no compatible distribution in this interval and returned
`ResolutionImpossible`. This result does **not** prove a source build is impossible;
it does establish a practical clean binary-install blocker. No manual
`--no-deps` override was used to conceal the incompatibility.

- Passing evidence: https://github.com/PhysicsQoo/QuPRS/actions/runs/41743839572/artifacts/13283165414
- Failing clean-resolver evidence: https://github.com/PhysicsQoo/QuPRS/actions/runs/41743839572/artifacts/13282354065

## Decision for v0.14.0

**Lightweight audit completed.** Current dev can install and run its source-built
`abi3` wheel on standard CPython 3.14 with Qiskit 2.6.1 in the tested Linux x86_64
environment. Upgrading PyO3 is **not necessary solely to achieve this**.

Do **not** add the Python 3.14 classifier or unskip `cp314*` for the v0.14.0
release on the basis of this lightweight evidence. Official support remains
deferred to a dedicated later release gate: native CPython 3.14 source build,
Linux ARM64/macOS wheels and sdist, broader solver/correctness suite,
and a documented Python-version/Qiskit-version support policy.
Python 3.14 + Qiskit 1.4.6 is **not** binary-installable in this environment;
do not claim the full cross-major Qiskit range works on 3.14.

The overall research workflow is intentionally **red** because its Qiskit 1.4.6
matrix entry exercises and records this genuine limitation. The independent
Qiskit 2.6.1 job and wheel build are green. No dev/main workflow,
release metadata, dependency constraint or CodSpeed benchmark was modified.
