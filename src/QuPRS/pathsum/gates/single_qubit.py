# src/QuPRS/pathsum/gates/single_qubit.py
from __future__ import annotations

import math

import symengine as se
import sympy as sp
from sympy.logic.boolalg import to_anf

from QuPRS.utils.util import (
    div_pi,
    find_new_variables,
    logical_to_algebraic,
    reduce_expression,
)

from .. import reduction
from ..core import PathSum
from .base import SingleQubitGate

# --- Single-Qubit Gate Implementations ---


class HGate(SingleQubitGate):
    gate_name = "h"

    def apply(
        self, pathsum: "PathSum", qubit: int | str | se.Symbol, is_bra: bool = False
    ) -> "PathSum":
        new_var = find_new_variables(pathsum.pathvar)[0]
        if not is_bra:
            x_i = logical_to_algebraic(pathsum.f[qubit], 1)
            new_P = pathsum.P + se.Rational(1, 2) * new_var * x_i
            new_f = pathsum.f.update(qubit, new_var)
        else:
            x_i = se.symbols(
                f"{pathsum.bits[qubit]}" if isinstance(qubit, int) else str(qubit)
            )
            new_P = pathsum.P.subs(x_i, new_var) + se.Rational(1, 2) * new_var * x_i
            new_f = pathsum.f.sub(x_i, logical_to_algebraic(new_var))

        new_pathvar = frozenset(set(pathsum.pathvar).union({new_var}))
        new_pathsum = PathSum(new_P, new_f, new_pathvar, pathsum._stats)
        return reduction.apply_reduction(new_pathsum)


class XGate(SingleQubitGate):
    gate_name = "x"

    def apply(
        self, pathsum: "PathSum", qubit: int | str | se.Symbol, is_bra: bool = False
    ) -> "PathSum":
        if not is_bra:
            new_P = pathsum.P
            new_f = pathsum.f.update(qubit, to_anf(sp.Not(pathsum.f[qubit])))
        else:
            x_i = se.symbols(
                f"{pathsum.bits[qubit]}" if isinstance(qubit, int) else str(qubit)
            )
            new_P = pathsum.P.subs(x_i, 1 - x_i)
            new_f = pathsum.f.sub(x_i, sp.Not(x_i))

        new_P = reduce_expression(new_P)
        return PathSum(new_P, new_f, pathsum.pathvar, pathsum._stats)


class YGate(SingleQubitGate):
    gate_name = "y"

    def apply(
        self, pathsum: "PathSum", qubit: int | str | se.Symbol, is_bra: bool = False
    ) -> "PathSum":
        if not is_bra:
            x_i = logical_to_algebraic(pathsum.f[qubit], 1)
            new_P = (pathsum.P + se.Rational(3, 4) + se.Rational(1, 2) * x_i).expand()
            new_f = pathsum.f.update(qubit, to_anf(sp.Not(pathsum.f[qubit])))
        else:
            x_i = se.symbols(
                f"{pathsum.bits[qubit]}" if isinstance(qubit, int) else str(qubit)
            )
            new_P = (
                pathsum.P.subs(x_i, 1 - x_i)
                + se.Rational(3, 4)
                + se.Rational(1, 2) * x_i
            ).expand()
            new_f = pathsum.f.sub(x_i, sp.Not(x_i))

        new_P = reduce_expression(new_P)
        return PathSum(new_P, new_f, pathsum.pathvar, pathsum._stats)


class ZGate(SingleQubitGate):
    gate_name = "z"

    def apply(
        self, pathsum: "PathSum", qubit: int | str | se.Symbol, is_bra: bool = False
    ) -> "PathSum":
        if not is_bra:
            x_i = logical_to_algebraic(pathsum.f[qubit], 1)
            new_P = (pathsum.P + se.Rational(1, 2) * x_i).expand()
        else:
            x_i = se.symbols(
                f"{pathsum.bits[qubit]}" if isinstance(qubit, int) else str(qubit)
            )
            new_P = (pathsum.P + se.Rational(1, 2) * x_i).expand()

        new_P = reduce_expression(new_P)
        return PathSum(new_P, pathsum.f, pathsum.pathvar, pathsum._stats)


class SGate(SingleQubitGate):
    gate_name = "s"

    def apply(
        self, pathsum: "PathSum", qubit: int | str | se.Symbol, is_bra: bool = False
    ) -> "PathSum":
        if not is_bra:
            x_i = logical_to_algebraic(pathsum.f[qubit], 2)
            new_P = (pathsum.P + se.Rational(1, 4) * x_i).expand()
        else:
            x_i = se.symbols(
                f"{pathsum.bits[qubit]}" if isinstance(qubit, int) else str(qubit)
            )
            new_P = (pathsum.P + se.Rational(-1, 4) * x_i).expand()

        new_P = reduce_expression(new_P)
        return PathSum(new_P, pathsum.f, pathsum.pathvar, pathsum._stats)


class SdgGate(SingleQubitGate):
    gate_name = "sdg"

    def apply(
        self, pathsum: "PathSum", qubit: int | str | se.Symbol, is_bra: bool = False
    ) -> "PathSum":
        if not is_bra:
            x_i = logical_to_algebraic(pathsum.f[qubit], 2)
            new_P = (pathsum.P + se.Rational(-1, 4) * x_i).expand()
        else:
            x_i = se.symbols(
                f"{pathsum.bits[qubit]}" if isinstance(qubit, int) else str(qubit)
            )
            new_P = (pathsum.P + se.Rational(1, 4) * x_i).expand()

        new_P = reduce_expression(new_P)
        return PathSum(new_P, pathsum.f, pathsum.pathvar, pathsum._stats)


class TGate(SingleQubitGate):
    gate_name = "t"

    def apply(
        self, pathsum: "PathSum", qubit: int | str | se.Symbol, is_bra: bool = False
    ) -> "PathSum":
        if not is_bra:
            x_i = logical_to_algebraic(pathsum.f[qubit], 3)
            new_P = (pathsum.P + se.Rational(1, 8) * x_i).expand()
        else:
            x_i = se.symbols(
                f"{pathsum.bits[qubit]}" if isinstance(qubit, int) else str(qubit)
            )
            new_P = (pathsum.P + se.Rational(-1, 8) * x_i).expand()

        new_P = reduce_expression(new_P)
        return PathSum(new_P, pathsum.f, pathsum.pathvar, pathsum._stats)


class TdgGate(SingleQubitGate):
    gate_name = "tdg"

    def apply(
        self, pathsum: "PathSum", qubit: int | str | se.Symbol, is_bra: bool = False
    ) -> "PathSum":
        if not is_bra:
            x_i = logical_to_algebraic(pathsum.f[qubit], 3)
            new_P = (pathsum.P + se.Rational(-1, 8) * x_i).expand()
        else:
            x_i = se.symbols(
                f"{pathsum.bits[qubit]}" if isinstance(qubit, int) else str(qubit)
            )
            new_P = pathsum.P + se.Rational(1, 8) * x_i

        new_P = reduce_expression(new_P)
        return PathSum(new_P, pathsum.f, pathsum.pathvar, pathsum._stats)


class PGate(SingleQubitGate):
    gate_name = "p"

    def __init__(self, theta):
        self.theta = div_pi(theta)

    def apply(
        self, pathsum: "PathSum", qubit: int | str | se.Symbol, is_bra: bool = False
    ) -> "PathSum":
        if not is_bra:
            if self.theta.is_number:
                numer, denom = self.theta.as_numer_denom()
                # Use math.log2 for integer and float compatibility
                max_order = math.log2(float(denom))
                max_order = int(max_order) + 1 if max_order == int(max_order) else None
            else:
                max_order = None
            x_i = logical_to_algebraic(pathsum.f[qubit], max_order=max_order)
            new_P = pathsum.P + se.Rational(1, 2) * self.theta * x_i
        else:
            x_i = se.symbols(
                f"{pathsum.bits[qubit]}" if isinstance(qubit, int) else str(qubit)
            )
            new_P = pathsum.P - se.Rational(1, 2) * self.theta * x_i

        new_P = reduce_expression(new_P)
        return PathSum(new_P, pathsum.f, pathsum.pathvar, pathsum._stats)


class RzGate(SingleQubitGate):
    gate_name = "rz"

    def __init__(self, theta):
        self.theta = div_pi(theta)

    def apply(
        self, pathsum: "PathSum", qubit: int | str | se.Symbol, is_bra: bool = False
    ) -> "PathSum":
        if not is_bra:
            if self.theta.is_number:
                numer, denom = self.theta.as_numer_denom()
                max_order = math.log2(float(denom))
                max_order = int(max_order) + 2 if max_order == int(max_order) else None
            else:
                max_order = None
            x_i = logical_to_algebraic(pathsum.f[qubit], max_order=max_order)
            new_P = pathsum.P + se.Rational(1, 4) * (-self.theta + 2 * self.theta * x_i)
        else:
            x_i = se.symbols(
                f"{pathsum.bits[qubit]}" if isinstance(qubit, int) else str(qubit)
            )
            new_P = pathsum.P + se.Rational(1, 4) * (self.theta - 2 * self.theta * x_i)

        new_P = reduce_expression(new_P)
        return PathSum(new_P, pathsum.f, pathsum.pathvar, pathsum._stats)


# The U-family of gates are more complex and rely on other gates.
# We will define them such that they can call other gate logic.
# For simplicity, we'll instantiate the required gates directly.


class UGate(SingleQubitGate):
    gate_name = "u"

    def __init__(self, theta, phi, lam):
        self.theta, self.phi, self.lam = map(div_pi, [theta, phi, lam])

    def apply(
        self, pathsum: "PathSum", qubit: int | str | se.Symbol, is_bra: bool = False
    ) -> "PathSum":
        new_vars = find_new_variables(pathsum.pathvar, 2)
        if not is_bra:
            if self.lam.is_number:
                numer, denom = self.lam.as_numer_denom()
                max_order = math.log2(float(denom))
                max_order = int(max_order) + 1 if max_order == int(max_order) else None
            else:
                max_order = None
            x_i_lam = logical_to_algebraic(pathsum.f[qubit], max_order=max_order)
            x_i = logical_to_algebraic(pathsum.f[qubit], max_order=2)
            new_P = (
                pathsum.P
                + se.Rational(1, 2) * self.lam * x_i_lam
                + se.Rational(1, 2) * self.phi * new_vars[1]
                + se.Rational(1, 4) * self.theta * (2 * new_vars[0] - 1)
                + se.Rational(3, 4) * x_i
                + se.Rational(1, 4) * new_vars[1]
                + se.Rational(1, 2) * x_i * new_vars[0]
                + se.Rational(1, 2) * new_vars[0] * new_vars[1]
            )
            new_f = pathsum.f.update(qubit, new_vars[1])
        else:
            x_i = se.symbols(
                f"{pathsum.bits[qubit]}" if isinstance(qubit, int) else str(qubit)
            )
            new_P = (
                pathsum.P.subs(x_i, new_vars[1])
                + se.Rational(-1, 2) * self.phi * x_i
                + se.Rational(-1, 2) * self.lam * new_vars[1]
                + se.Rational(1, 4) * self.theta * (2 * new_vars[0] - 1)
                + se.Rational(1, 4) * x_i
                + se.Rational(3, 4) * new_vars[1]
                + se.Rational(1, 2) * x_i * new_vars[0]
                + se.Rational(1, 2) * new_vars[0] * new_vars[1]
            )
            new_f = pathsum.f.sub(x_i, logical_to_algebraic(new_vars[1]))

        new_pathvar = frozenset(set(pathsum.pathvar).union(new_vars))
        new_pathsum = PathSum(new_P, new_f, new_pathvar, pathsum._stats)
        return reduction.apply_reduction(new_pathsum)


class RxGate(SingleQubitGate):
    gate_name = "rx"

    def __init__(self, theta):
        self.theta = theta  # div_pi is handled by UGate

    def apply(
        self, pathsum: "PathSum", qubit: int | str | se.Symbol, is_bra: bool = False
    ) -> "PathSum":
        # Decomposes into a U gate
        u_gate = UGate(self.theta, -se.pi / 2, se.pi / 2)
        return u_gate.apply(pathsum, qubit, is_bra)


class RyGate(SingleQubitGate):
    gate_name = "ry"

    def __init__(self, theta):
        self.theta = theta  # div_pi is handled by UGate

    def apply(
        self, pathsum: "PathSum", qubit: int | str | se.Symbol, is_bra: bool = False
    ) -> "PathSum":
        # Decomposes into a U gate
        u_gate = UGate(self.theta, 0, 0)
        return u_gate.apply(pathsum, qubit, is_bra)


class SxGate(SingleQubitGate):
    gate_name = "sx"

    def apply(
        self, pathsum: "PathSum", qubit: int | str | se.Symbol, is_bra: bool = False
    ) -> "PathSum":
        # Apply Rx(pi/2)
        rx_gate = RxGate(se.pi / 2)
        pathsum = rx_gate.apply(pathsum, qubit, is_bra)

        # Apply global phase
        phase_shift = se.Rational(1, 8) if not is_bra else se.Rational(-1, 8)
        new_P = reduce_expression(pathsum.P + phase_shift)
        return PathSum(new_P, pathsum.f, pathsum.pathvar, pathsum._stats)


class SxdgGate(SingleQubitGate):
    gate_name = "sxdg"

    def apply(
        self, pathsum: "PathSum", qubit: int | str | se.Symbol, is_bra: bool = False
    ) -> "PathSum":
        # Apply Rx(-pi/2)
        rx_gate = RxGate(-se.pi / 2)
        pathsum = rx_gate.apply(pathsum, qubit, is_bra)

        # Apply global phase
        phase_shift = se.Rational(-1, 8) if not is_bra else se.Rational(1, 8)
        new_P = reduce_expression(pathsum.P + phase_shift)
        return PathSum(new_P, pathsum.f, pathsum.pathvar, pathsum._stats)


class IdGate(SingleQubitGate):
    gate_name = "id"

    def apply(
        self, pathsum: "PathSum", qubit: int | str | se.Symbol, is_bra: bool = False
    ) -> "PathSum":
        # Identity gate does not change the PathSum
        return PathSum(pathsum.P, pathsum.f, pathsum.pathvar, pathsum._stats)


# --- Aliases and U-based Gates ---


class U1Gate(PGate):  # U1 is an alias for PGate
    gate_name = "u1"

    def __init__(self, theta):
        super().__init__(theta)


class U2Gate(UGate):  # U2 is a specific UGate
    gate_name = "u2"

    def __init__(self, phi, lam):
        super().__init__(se.pi / 2, phi, lam)


class U3Gate(UGate):  # U3 is an alias for UGate
    gate_name = "u3"

    def __init__(self, theta, phi, lam):
        super().__init__(theta, phi, lam)
