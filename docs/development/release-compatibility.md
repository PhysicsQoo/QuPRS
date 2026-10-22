# Platform compatibility and release acceptance

QuPRS distinguishes three different forms of evidence. Passing one does not
imply the others have passed.

| Stage | Source of truth | When it runs | What it establishes |
| --- | --- | --- | --- |
| Development correctness | `dev-fast.yml` and relevant native PR CI | Code- or solver-sensitive changes to `dev` | Rust/Python semantics, GPMC/Ganak execution and benchmark verdict integrity on tested runners |
| Pre-packaging source compatibility | `release-ready-main.yml` → `source-correctness` (`pytest.yml`) | Release candidate PR from `dev` to `main`; manual release readiness | Supported OS/architecture × Python source/native build and correctness, **before** creating release archives |
| Built-artifact acceptance | `release-ready-main.yml` → `installed-artifacts` (`release-artifact-ci.yml`) | After the source matrix passes, before merging to `main` | Candidate wheel/sdist creation, wheel tag/deployment consistency, clean installation and native-solver smoke |

## Development: do not duplicate release matrices

The normal PR checks remain scoped to modified sources and their dependent
native/backend correctness checks. `ubuntu-latest` is intentionally a moving
GitHub-hosted runner label. It does not fix the Ubuntu version, CPU model,
compiler toolchain or measured external-solver wall time. Keep paper input
integrity, semantic failures, `INCONCLUSIVE_RESOURCE` and true skips separate.

A one-off platform probe can establish whether a new GitHub image can build
the source; it is **not** a new permanent CI obligation. For example, the
Ubuntu 26.04 x86-64/ARM64 Python 3.12 native pilot
([validation evidence](https://github.com/PhysicsQoo/QuPRS/actions/runs/39758337836))
passed original Rust/Python tests and the 32 representative benchmarks.
It did not certify Python 3.11/3.13, built wheels, source archives, Docker
images or binary compatibility across older distributions.

## Pre-packaging: source support

On a release candidate to `main`, the existing `source-correctness`
reusable workflow validates **four platform/architecture groups × Python
3.11/3.12/3.13**. It includes real solver dependencies and the original
32-case benchmark verdict audit. The artifact stage now depends on completion
of this gate rather than executing concurrently. Failed or missing source
coverage must block release-artifact work, not be silently treated as a pass.

A change in supported Python/OS/architecture, solver packaging, GMP/MPFR
dependencies or deployment policy must be validated with an explicit source
compatibility test first. Do not expand `requires-python`, platform
classifiers or the README based solely on a runner-label change.

## Post-build: certify the distribution users will actually install

A source build does not prove that the wheel or sdist can be installed in
a clean environment. The current reusable release-artifact workflow builds
four platform wheel groups and an sdist, then tests **12 clean wheel
installations** and **two clean sdist installations**. The tag-triggered
`python-publish.yml` uses the corresponding nonpublishing build/install
checks before publication. `scripts/verify_release_artifact_workflow_parity.py`
checks both builders for drift.

The existing `scripts/verify_macos_wheel_support.py` and tests verify the
documented macOS **15+** minimum against the release deployment target and
wheel filename/embedded tags. Historic macOS 14 sdist evidence is limited
and is not evidence of supported macOS 14 wheels.

Record release-source SHA, actual runner image and architecture, Python and
Rust versions, solver identity/provenance, candidate archive filenames and
hashes, WHEEL tags, install smoke results and any unsupported combinations.
Use these artifacts to review `README.md`, `pyproject.toml`, contributor
documentation, and release notes. A failed install on a genuinely supported
target blocks publishing even if source correctness passed.

The `main` release acceptance should remain read-only and fail-closed.
Only the dedicated tag-time workflow publishes to PyPI. Do not add a
shared-runner Walltime percentage threshold or change equivalence semantics
to make the packaging gate pass. For controlled solver performance
comparisons, see [benchmark testing](benchmark-testing.md).
