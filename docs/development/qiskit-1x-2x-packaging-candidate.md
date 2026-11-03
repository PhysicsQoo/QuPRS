# QOO-169 — isolated Qiskit 1.x / 2.x packaging candidate

This research branch deliberately changes `pyproject.toml` to `qiskit>=1.0.0,<3.0` **only here**, not on `dev` or `main`. Qiskit 3.x is not declared supported. The Python package's intended Python support remains 3.11–3.13; Python 3.14 is independently tracked.

## Evidence boundary

Prior Qiskit 1.4.6 / 2.6.1 experiments exercised compiler and source semantics but deliberately installed 2.x using `--no-deps`, leaving the published QuPRS metadata unsatisfied. These observations are **not** resolver or release-artifact certification.

This branch adds a narrow, independent release-installer gate:
1. Build one real abi3 Linux wheel and an sdist from the same source SHA, without changing Rust or solver algorithms.
2. In fresh interpreter environments, ask pip to resolve and install `qiskit==1.4.6` or `qiskit==2.6.1` **together with** the candidate QuPRS wheel. No `--no-deps` overrides.
3. Run `pip check` and actual public Python/Rust smoke for RR/Hybrid and minimal WMC, recording `pip freeze`, wheel SHA and selected versions.
4. Optionally run a true sdist install for both versions on Python 3.12; this must not be substituted with wheel-only metadata inspection.
5. Reuse QOO-121 Qiskit API/semantic SHA evidence rather than re-running historical broad transpiler or tolerance experiments.

The default push gate is the wheel matrix (Python 3.11/3.12/3.13 × Qiskit 1.4.6/2.6.1) and the single build job. The sdist matrix is intentionally an explicit dispatch option to avoid repeatedly rebuilding native dependencies during initial convergence.

## Go / No-Go

- **Not accepted** until the exact-SHA clean wheel *and* sdist install/resolve evidence, a representative platform gate, and the QOO-121 scientific semantic controls pass.
- All failure cases retain full `pip` logs, dependency metadata and the actual version graph; do not treat a force-installed 2.x functional smoke as a packaging success.
- Do not merge this study branch directly into `dev`. On admission, prepare a small controlled PR updating only the version bound, release docs and installer CI.
