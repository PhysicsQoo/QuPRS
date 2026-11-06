#!/usr/bin/env python3
"""Independently check the scalar algebra in the public theory guide.

This is not a proof of all reduction rules or external WMC solver soundness.
"""

from __future__ import annotations

import cmath
from math import cos, pi, sin, sqrt
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH_GUIDE = ROOT / "docs" / "site" / "path-sum.md"
WMC_GUIDE = ROOT / "docs" / "site" / "weighted-model-counting.md"


def near(actual: complex | float, expected: complex | float) -> None:
    if abs(actual - expected) > 1e-12:
        raise AssertionError(f"Algebraic identity failed: {actual!r} != {expected!r}")


def check_reduction_identities() -> None:
    # Elim: y does not appear in P or output.
    for phi in (0, 0.125, -0.381):
        term = cmath.exp(2j * pi * phi)
        near(sum(term for _ in (0, 1)), 2 * term)

    # HH: y0 sums enforce y1 = Q mod 2.
    for y1 in (0, 1):
        for q in (0, 1):
            lhs = sum(cmath.exp(2j * pi * 0.5 * y0 * (y1 + q))
                      for y0 in (0, 1))
            near(lhs, 2 if y1 == q else 0)

    # Omega: both quarter-cycle branches must have the correct scalar phase.
    for q in (0, 1):
        for coefficient, offset, slope in (
            (0.25, 0.125, -0.25), (0.75, -0.125, 0.25),
        ):
            lhs = sum(cmath.exp(2j * pi * y * (coefficient + 0.5 * q))
                      for y in (0, 1))
            rhs = sqrt(2) * cmath.exp(2j * pi * (offset + slope * q))
            near(lhs, rhs)


def check_reduction_kets() -> None:
    """Check full two-component state vectors, not just scalar phase sums."""

    def basis(index: int) -> tuple[complex, complex]:
        return (1 + 0j, 0j) if index == 0 else (0j, 1 + 0j)

    def scale(a: complex, ket: tuple[complex, complex]) -> tuple[complex, complex]:
        return (a * ket[0], a * ket[1])

    def add(a: tuple[complex, complex], b: tuple[complex, complex]) -> tuple[complex, complex]:
        return (a[0] + b[0], a[1] + b[1])

    def check(a: tuple[complex, complex], b: tuple[complex, complex]) -> None:
        for actual, expected in zip(a, b):
            near(actual, expected)

    # HH: the output f(y1)=y1 XOR flip depends on the target y1.
    # Verify that summing y0 and y1 substitutes y1=Q in *both* R and f.
    for q in (0, 1):
        for flip in (0, 1):
            acc = (0j, 0j)
            for y1 in (0, 1):
                for y0 in (0, 1):
                    residual = (0.07 + 0.125 * y1)
                    weight = cmath.exp(2j * pi * (0.5 * y0 * (y1 + q) + residual))
                    acc = add(acc, scale(weight, basis(y1 ^ flip)))
            expected = scale(2 * cmath.exp(2j * pi * (0.07 + 0.125 * q)), basis(q ^ flip))
            check(acc, expected)

    # Omega: the output f is arbitrary but independent of y.
    # Verify both possible quarter-cycle coefficients and both Boolean Q values.
    for q in (0, 1):
        for output in (0, 1):
            for quarter, offset, slope in (
                (0.25, 0.125, -0.25),
                (0.75, -0.125, 0.25),
            ):
                residual = 0.1375
                amplitude = sum(
                    cmath.exp(2j * pi * (residual + y * (quarter + 0.5 * q)))
                    for y in (0, 1)
                )
                lhs = scale(amplitude, basis(output))
                rhs = scale(
                    sqrt(2) * cmath.exp(2j * pi * (residual + offset + slope * q)),
                    basis(output),
                )
                check(lhs, rhs)


def check_projective_distance() -> None:
    # For I and Rz(theta), the trace is 2*cos(theta/2) and d=2.
    for theta in (0.0, 0.001, 0.2, pi, 2 * pi):
        m = abs(cos(theta / 2))
        d_proj = sqrt(max(0.0, 1.0 - m * m))
        near(d_proj, abs(sin(theta / 2)))
        d_gp_sq = 2 - 2 * m
        near(d_proj * d_proj, d_gp_sq - d_gp_sq**2 / 4)
    if abs(sin(0.001 / 2)) <= 1e-8:
        raise AssertionError("Nontrivial Rz difference falsely accepted")
    # A nonzero scalar phase produces D_proj=0 but is not exact equality.
    phase = cmath.exp(0.7j)
    near(sqrt(max(0.0, 1 - abs(phase) ** 2)), 0)
    if abs(phase - 1) < 0.1:
        raise AssertionError("Global phase incorrectly treated as exact equality")


def check_public_guide_markers() -> None:
    reductions = PATH_GUIDE.read_text(encoding="utf-8")
    wmc = WMC_GUIDE.read_text(encoding="utf-8")
    for marker in (r"\delta_", r"\sqrt{2}", r"\frac34", "TACAS 2026",
                   r"|f(y_1)\rangle", r"|f(Q\bmod2)\rangle"):
        if marker not in reductions:
            raise AssertionError(f"Missing published reduction identity: {marker}")
    hh_section = reductions.split("**HH.**", 1)[1].split("**Omega.**", 1)[0]
    omega_section = reductions.split("**Omega.**", 1)[1].split("## Reduction rules", 1)[0]
    if hh_section.count(r"|f(y_1)\rangle") < 3:
        raise AssertionError("HH must preserve ket and substitute target state")
    if omega_section.count(r"|f\rangle") < 4:
        raise AssertionError("Omega must retain ket on both sides of both rules")
    for marker in (r"D_{\mathrm{proj}}", r"D_{\mathrm{gp}}", r"R_z(\theta)"):
        if marker not in wmc:
            raise AssertionError(f"Missing published metric identity: {marker}")


if __name__ == "__main__":
    check_reduction_identities()
    check_reduction_kets()
    check_projective_distance()
    check_public_guide_markers()
    print("Public mathematical identity checks: full ket-preserving reduction identities and projective metric PASS")
