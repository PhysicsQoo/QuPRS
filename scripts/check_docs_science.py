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

    # HH source phase uses unreduced integer Q; constraint uses Q % 2.
    # Values outside {0, 1} detect accidental replacement of source Q by parity.
    for y1 in (0, 1):
        for Q in range(-4, 6):
            lhs = sum(cmath.exp(2j * pi * 0.5 * y0 * (y1 + Q))
                      for y0 in (0, 1))
            near(lhs, 2 if y1 == Q % 2 else 0)

    # Omega source keeps Q; ONLY the reduced phase uses its Boolean parity.
    for Q in range(-4, 6):
        Q_bar = Q % 2
        for coefficient, offset, slope in (
            (0.25, 0.125, -0.25), (0.75, -0.125, 0.25),
        ):
            lhs = sum(cmath.exp(2j * pi * y0 * (coefficient + 0.5 * Q))
                      for y0 in (0, 1))
            rhs = sqrt(2) * cmath.exp(2j * pi * (offset + slope * Q_bar))
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

    # HH: original source P = 1/2*y0*(y1+Q(x,z)) + R(x,y1,z).
    # Q is an integer-valued expression, possibly negative or > 1.
    # Only the replacement in residual phase and ket uses Q_bar = Q % 2.
    for x in (0, 1):
        for z in (0, 1):
            for bias in (-3, 0, 2):
                Q = x + 2 * z + bias
                Q_bar = Q % 2
                for flip in (0, 1):
                    actual = (0j, 0j)
                    for y1 in (0, 1):
                        for y0 in (0, 1):
                            residual = 0.07 + 0.125 * y1 + 0.03125 * x + 0.0625 * z
                            source_phase = 0.5 * y0 * (y1 + Q) + residual
                            ket = basis(x ^ z ^ y1 ^ flip)
                            actual = add(actual, scale(cmath.exp(2j * pi * source_phase), ket))
                    replaced_residual = 0.07 + 0.125 * Q_bar + 0.03125 * x + 0.0625 * z
                    replaced_ket = basis(x ^ z ^ Q_bar ^ flip)
                    expected = scale(
                        2 * cmath.exp(2j * pi * replaced_residual), replaced_ket
                    )
                    check(actual, expected)

    # Omega: both quarter-cycle branches preserve output ket.
    # The source uses integer Q; only the reduced phase uses Q_bar.
    for Q in range(-4, 6):
        Q_bar = Q % 2
        for output in (0, 1):
            for quarter, offset, slope in (
                (0.25, 0.125, -0.25),
                (0.75, -0.125, 0.25),
            ):
                residual = 0.1375
                amplitude = sum(
                    cmath.exp(2j * pi * (residual + y0 * (quarter + 0.5 * Q)))
                    for y0 in (0, 1)
                )
                lhs = scale(amplitude, basis(output))
                rhs = scale(
                    sqrt(2) * cmath.exp(2j * pi * (residual + offset + slope * Q_bar)),
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
    for marker in (r"\sqrt{2}", r"\frac34", "TACAS 2026",
                   r"P(x,y)=\frac12 y_0\bigl(y_1+Q(x,z)\bigr)+R(x,y')",
                   r"|f(x,y')\rangle",
                   r"|f_{\overline Q}(x,z)\rangle"):
        if marker not in reductions:
            raise AssertionError(f"Missing published reduction identity: {marker}")

    hh_section = reductions.split("**HH.**", 1)[1].split("**Omega.**", 1)[0]
    omega_section = reductions.split("**Omega.**", 1)[1].split("## Reduction rules", 1)[0]
    if r"y=(y_0,y_1,z)" not in hh_section or r"y'=(y_1,z)" not in hh_section:
        raise AssertionError("HH must distinguish full and residual path variables")
    if r"y_1+Q(x,z)" not in hh_section or r"\overline Q=Q(x,z)\bmod 2" not in hh_section:
        raise AssertionError("HH source must use Q; parity reduction occurs only at substitution")
    if r"y_1+\overline Q" in hh_section or r"y_1+q" in hh_section:
        raise AssertionError("HH source incorrectly uses reduced parity instead of Q")
    if r"R(x,y)" in hh_section or r"|f(x,y)\rangle" in hh_section:
        raise AssertionError("HH residual must not depend on eliminated y0")
    if r"|f(x,y')\rangle" not in hh_section or r"|f_{\overline Q}(x,z)\rangle" not in hh_section:
        raise AssertionError("HH must substitute Q parity into the output ket")
    if omega_section.count(r"|f\rangle") < 4:
        raise AssertionError("Omega must retain ket on both sides of both rules")
    if omega_section.count(r"\overline Q") < 3:
        raise AssertionError("Omega reduced phases must use Boolean parity")
    if r"\frac12Q" not in omega_section:
        raise AssertionError("Omega source must keep unreduced integer Q")
    for marker in (r"D_{\mathrm{proj}}", r"D_{\mathrm{gp}}", r"R_z(\theta)"):
        if marker not in wmc:
            raise AssertionError(f"Missing published metric identity: {marker}")


if __name__ == "__main__":
    check_reduction_identities()
    check_reduction_kets()
    check_projective_distance()
    check_public_guide_markers()
    print("Public mathematical identity checks: full ket-preserving reduction identities and projective metric PASS")
