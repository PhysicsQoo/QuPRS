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
    for marker in (r"\delta_", r"\sqrt2", r"\frac34", "TACAS 2026"):
        if marker not in reductions:
            raise AssertionError(f"Missing published reduction identity: {marker}")
    for marker in (r"D_{\mathrm{proj}}", r"D_{\mathrm{gp}}", r"R_z(\theta)"):
        if marker not in wmc:
            raise AssertionError(f"Missing published metric identity: {marker}")


if __name__ == "__main__":
    check_reduction_identities()
    check_projective_distance()
    check_public_guide_markers()
    print("Public mathematical identity checks: 3 reduction families and projective metric PASS")
