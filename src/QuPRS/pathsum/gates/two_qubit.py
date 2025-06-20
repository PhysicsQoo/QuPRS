# src/QuPRS/pathsum/gates/two_qubit.py
from __future__ import annotations

import math

import symengine as se
import sympy as sp
from sympy.logic.boolalg import to_anf

from QuPRS.utils.util import div_pi, logical_to_algebraic, reduce_expression

from ..core import PathSum
from .base import TwoQubitGate
from .single_qubit import HGate, RyGate, SdgGate, SGate, TdgGate, TGate

# --- Two-Qubit Gate Implementations ---


class CXGate(TwoQubitGate):
    gate_name = "cx"

    def apply(
        self,
        pathsum: "PathSum",
        control_qubit: int | str | se.Symbol,
        target_qubit: int | str | se.Symbol,
        is_bra: bool = False,
    ) -> "PathSum":
        # ... (Implementation is the same)
        if not is_bra:
            new_f = pathsum.f.update(
                target_qubit,
                to_anf(sp.Xor(pathsum.f[control_qubit], pathsum.f[target_qubit])),
            )
            return PathSum(pathsum.P, new_f, pathsum.pathvar)
        else:
            x_i = se.symbols(
                f"{pathsum.bits[target_qubit]}"
                if isinstance(target_qubit, int)
                else str(target_qubit)
            )
            x_j = se.symbols(
                f"{pathsum.bits[control_qubit]}"
                if isinstance(control_qubit, int)
                else str(control_qubit)
            )
            new_var = sp.Xor(x_i, x_j)
            update_var = logical_to_algebraic(new_var)
            new_P = pathsum.P.subs(x_i, update_var)
            new_P = reduce_expression(new_P)
            new_f = pathsum.f.sub(x_i, new_var)
            return PathSum(new_P, new_f, pathsum.pathvar)


class CZGate(TwoQubitGate):
    gate_name = "cz"

    def apply(
        self,
        pathsum: "PathSum",
        control_qubit: int,
        target_qubit: int,
        is_bra: bool = False,
    ) -> "PathSum":
        # ... (Implementation is the same)
        if not is_bra:
            x_i = logical_to_algebraic(pathsum.f[control_qubit], 1)
            x_j = logical_to_algebraic(pathsum.f[target_qubit], 1)
            new_P = pathsum.P + se.Rational(1, 2) * x_i * x_j
        else:
            x_i = se.symbols(
                f"{pathsum.bits[control_qubit]}"
                if isinstance(control_qubit, int)
                else str(control_qubit)
            )
            x_j = se.symbols(
                f"{pathsum.bits[target_qubit]}"
                if isinstance(target_qubit, int)
                else str(target_qubit)
            )
            new_P = pathsum.P + se.Rational(1, 2) * x_i * x_j
        new_P = reduce_expression(new_P)
        return PathSum(new_P, pathsum.f, pathsum.pathvar)


class SwapGate(TwoQubitGate):
    gate_name = "swap"

    def apply(
        self,
        pathsum: "PathSum",
        qubit1: int | str | se.Symbol,
        qubit2: int | str | se.Symbol,
        is_bra: bool = False,
    ) -> "PathSum":
        # ... (Implementation is the same)
        if not is_bra:
            f1 = pathsum.f[qubit1]
            f2 = pathsum.f[qubit2]
            new_f = pathsum.f.update(qubit1, f2)
            new_f = new_f.update(qubit2, f1)
            new_P = pathsum.P
        else:
            x_i = se.symbols(
                f"{pathsum.bits[qubit1]}" if isinstance(qubit1, int) else str(qubit1)
            )
            x_j = se.symbols(
                f"{pathsum.bits[qubit2]}" if isinstance(qubit2, int) else str(qubit2)
            )
            temp_sym = se.Symbol("temp_swap_var")
            new_P = pathsum.P.subs({x_i: x_j, x_j: x_i})
            new_P = reduce_expression(new_P)
            new_f = pathsum.f.sub(x_i, temp_sym)
            new_f = new_f.sub(x_j, x_i)
            new_f = new_f.sub(temp_sym, x_j)
        return PathSum(new_P, new_f, pathsum.pathvar)


class CHGate(TwoQubitGate):
    gate_name = "ch"

    def __init__(self):
        self.s = SGate()
        self.h = HGate()
        self.t = TGate()
        self.cx = CXGate()
        self.tdg = TdgGate()
        self.sdg = SdgGate()

    def apply(
        self,
        pathsum: "PathSum",
        control_qubit: int,
        target_qubit: int,
        is_bra: bool = False,
    ) -> "PathSum":
        pathsum = self.s.apply(pathsum, target_qubit, is_bra)
        pathsum = self.h.apply(pathsum, target_qubit, is_bra)
        pathsum = self.t.apply(pathsum, target_qubit, is_bra)
        pathsum = self.cx.apply(pathsum, control_qubit, target_qubit, is_bra)
        pathsum = self.tdg.apply(pathsum, target_qubit, is_bra)
        pathsum = self.h.apply(pathsum, target_qubit, is_bra)
        pathsum = self.sdg.apply(pathsum, target_qubit, is_bra)
        return pathsum


class CRkGate(TwoQubitGate):
    gate_name = "CRk"

    def __init__(self, k: int):
        self.k = k

    def apply(
        self,
        pathsum: "PathSum",
        control_qubit: int,
        target_qubit: int,
        is_bra: bool = False,
    ) -> "PathSum":
        # ... (Implementation is the same)
        phase_factor = se.Rational(1, 2**self.k)
        if is_bra:
            phase_factor = -phase_factor
        if not is_bra:
            x_i = logical_to_algebraic(pathsum.f[control_qubit], self.k)
            x_j = logical_to_algebraic(pathsum.f[target_qubit], self.k)
        else:
            x_i = se.symbols(
                f"{pathsum.bits[control_qubit]}"
                if isinstance(control_qubit, int)
                else str(control_qubit)
            )
            x_j = se.symbols(
                f"{pathsum.bits[target_qubit]}"
                if isinstance(target_qubit, int)
                else str(target_qubit)
            )
        new_P = pathsum.P + phase_factor * x_i * x_j
        new_P = reduce_expression(new_P)
        return PathSum(new_P, pathsum.f, pathsum.pathvar)


class CRkdgGate(TwoQubitGate):
    gate_name = "CRkdg"

    def __init__(self, k: int):
        self.k = k

    def apply(
        self,
        pathsum: "PathSum",
        control_qubit: int,
        target_qubit: int,
        is_bra: bool = False,
    ) -> "PathSum":
        # ... (Implementation is the same)
        phase_factor = se.Rational(-1, 2**self.k)
        if is_bra:
            phase_factor = -phase_factor
        if not is_bra:
            x_i = logical_to_algebraic(pathsum.f[control_qubit], self.k)
            x_j = logical_to_algebraic(pathsum.f[target_qubit], self.k)
        else:
            x_i = se.symbols(
                f"{pathsum.bits[control_qubit]}"
                if isinstance(control_qubit, int)
                else str(control_qubit)
            )
            x_j = se.symbols(
                f"{pathsum.bits[target_qubit]}"
                if isinstance(target_qubit, int)
                else str(target_qubit)
            )
        new_P = pathsum.P + phase_factor * x_i * x_j
        new_P = reduce_expression(new_P)
        return PathSum(new_P, pathsum.f, pathsum.pathvar)


class CPGate(TwoQubitGate):
    gate_name = "cp"

    def __init__(self, theta):
        self.theta = div_pi(theta)

    def apply(
        self,
        pathsum: "PathSum",
        control_qubit: int,
        target_qubit: int,
        is_bra: bool = False,
    ) -> "PathSum":
        # ... (Implementation is the same)
        phase_factor = se.Rational(1, 2) * self.theta
        if is_bra:
            phase_factor = -phase_factor
        if not is_bra:
            if self.theta.is_number:
                numer, denom = self.theta.as_numer_denom()
                max_order = math.log2(float(denom))
                max_order = int(max_order) + 1 if max_order == int(max_order) else None
            else:
                max_order = None
            x_i = logical_to_algebraic(pathsum.f[control_qubit], max_order=max_order)
            x_j = logical_to_algebraic(pathsum.f[target_qubit], max_order=max_order)
        else:
            x_i = se.symbols(
                f"{pathsum.bits[control_qubit]}"
                if isinstance(control_qubit, int)
                else str(control_qubit)
            )
            x_j = se.symbols(
                f"{pathsum.bits[target_qubit]}"
                if isinstance(target_qubit, int)
                else str(target_qubit)
            )
        new_P = pathsum.P + phase_factor * x_i * x_j
        new_P = reduce_expression(new_P)
        return PathSum(new_P, pathsum.f, pathsum.pathvar)


class CRZGate(TwoQubitGate):
    gate_name = "crz"

    def __init__(self, theta):
        self.theta = div_pi(theta)

    def apply(
        self,
        pathsum: "PathSum",
        control_qubit: int,
        target_qubit: int,
        is_bra: bool = False,
    ) -> "PathSum":
        # ... (Implementation is the same)
        if not is_bra:
            if self.theta.is_number:
                numer, denom = self.theta.as_numer_denom()
                max_order = math.log2(float(denom))
                max_order = int(max_order) + 2 if max_order == int(max_order) else None
            else:
                max_order = None
            x_i = logical_to_algebraic(pathsum.f[control_qubit], max_order=max_order)
            x_j = logical_to_algebraic(pathsum.f[target_qubit], max_order=max_order)
            new_P = pathsum.P + se.Rational(1, 4) * x_i * (
                -self.theta + 2 * self.theta * x_j
            )
        else:
            x_i = se.symbols(
                f"{pathsum.bits[control_qubit]}"
                if isinstance(control_qubit, int)
                else str(control_qubit)
            )
            x_j = se.symbols(
                f"{pathsum.bits[target_qubit]}"
                if isinstance(target_qubit, int)
                else str(target_qubit)
            )
            new_P = pathsum.P + se.Rational(1, 4) * x_i * (
                self.theta - 2 * self.theta * x_j
            )
        new_P = reduce_expression(new_P)
        return PathSum(new_P, pathsum.f, pathsum.pathvar)


class CRYGate(TwoQubitGate):
    gate_name = "cry"

    def __init__(self, theta):
        self.ry_pos = RyGate(theta / 2)
        self.ry_neg = RyGate(-theta / 2)
        self.cx = CXGate()

    def apply(
        self,
        pathsum: "PathSum",
        control_qubit: int,
        target_qubit: int,
        is_bra: bool = False,
    ) -> "PathSum":
        pathsum = self.ry_pos.apply(pathsum, target_qubit, is_bra)
        pathsum = self.cx.apply(pathsum, control_qubit, target_qubit, is_bra)
        pathsum = self.ry_neg.apply(pathsum, target_qubit, is_bra)
        pathsum = self.cx.apply(pathsum, control_qubit, target_qubit, is_bra)
        return pathsum


class CRXGate(TwoQubitGate):
    gate_name = "crx"

    def __init__(self, theta):
        self.h = HGate()
        self.crz = CRZGate(theta)

    def apply(
        self,
        pathsum: "PathSum",
        control_qubit: int,
        target_qubit: int,
        is_bra: bool = False,
    ) -> "PathSum":
        pathsum = self.h.apply(pathsum, target_qubit, is_bra)
        pathsum = self.crz.apply(pathsum, control_qubit, target_qubit, is_bra)
        pathsum = self.h.apply(pathsum, target_qubit, is_bra)
        return pathsum


# --- Aliases and Complex Decompositions ---


class CU1Gate(CPGate):
    gate_name = "cu1"

    def __init__(self, theta):
        super().__init__(theta)


class CU3Gate(TwoQubitGate):
    gate_name = "cu3"

    def __init__(self, theta, phi, lam):
        self.crz_lam = CRZGate(lam)
        self.cry_theta = CRYGate(theta)
        self.crz_phi = CRZGate(phi)
        self.cp_phase = CPGate(se.Rational(1, 2) * (phi + lam))

    def apply(
        self,
        pathsum: "PathSum",
        control_qubit: int,
        target_qubit: int,
        is_bra: bool = False,
    ) -> "PathSum":
        pathsum = self.crz_lam.apply(pathsum, control_qubit, target_qubit, is_bra)
        pathsum = self.cry_theta.apply(pathsum, control_qubit, target_qubit, is_bra)
        pathsum = self.crz_phi.apply(pathsum, control_qubit, target_qubit, is_bra)
        pathsum = self.cp_phase.apply(pathsum, control_qubit, target_qubit, is_bra)
        return pathsum


class CUGate(TwoQubitGate):
    gate_name = "cu"

    def __init__(self, theta, phi, lam, gamma):
        self.cu3 = CU3Gate(theta, phi, lam)
        self.cp_gamma = CPGate(gamma)

    def apply(
        self,
        pathsum: "PathSum",
        control_qubit: int,
        target_qubit: int,
        is_bra: bool = False,
    ) -> "PathSum":
        pathsum = self.cu3.apply(pathsum, control_qubit, target_qubit, is_bra)
        pathsum = self.cp_gamma.apply(pathsum, control_qubit, target_qubit, is_bra)
        return pathsum
