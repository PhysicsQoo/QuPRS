# src/QuPRS/pathsum/gates/multi_qubit.py

from __future__ import annotations

from typing import TYPE_CHECKING

import symengine as se
import sympy as sp
from sympy.logic.boolalg import to_anf

from QuPRS.utils.util import logical_to_algebraic, reduce_expression

from ..core import PathSum
from .base import gate

if TYPE_CHECKING:
    from ..core import PathSum

# --- Multi-Qubit Gates ---


# Apply CCX gate
@gate(type="multi")
def ccx(
    self: "PathSum",
    control_qubit1: int | str | se.Symbol,
    control_qubit2: int | str | se.Symbol,
    target_qubit: int | str | se.Symbol,
    is_bra: bool = False,
) -> "PathSum":
    if not is_bra:
        new_f = self.f.update(
            target_qubit,
            to_anf(
                sp.Xor(
                    self.f[target_qubit],
                    sp.And(self.f[control_qubit1], self.f[control_qubit2]),
                )
            ),
        )
        return PathSum(self.P, new_f, self.pathvar)
    else:
        x_i = se.symbols(
            f"{self.bits[target_qubit]}"
            if isinstance(target_qubit, int)
            else str(target_qubit)
        )
        x_j = se.symbols(
            f"{self.bits[control_qubit1]}"
            if isinstance(control_qubit1, int)
            else str(control_qubit1)
        )
        x_k = se.symbols(
            f"{self.bits[control_qubit2]}"
            if isinstance(control_qubit2, int)
            else str(control_qubit2)
        )
        new_var = sp.Xor(x_i, sp.And(x_j, x_k))
        update_var = logical_to_algebraic(new_var)
        new_P = self.P.subs(x_i, update_var)
        new_P = reduce_expression(new_P)
        new_f = self.f.sub(x_i, new_var)
        return PathSum(new_P, new_f, self.pathvar)


# Apply MCX gate
@gate(type="multi")
def mcx(self: "PathSum", *qubits, is_bra: bool = False) -> "PathSum":
    target_qubit = qubits[-1]
    control_qubits = qubits[0:-1]
    if not is_bra:
        new_f = self.f.update(
            target_qubit,
            to_anf(
                sp.Xor(
                    self.f[target_qubit], sp.And([self.f[i] for i in control_qubits])
                )
            ),
        )
        return PathSum(self.P, new_f, self.pathvar)
    else:
        x_i = se.symbols(
            f"{self.bits[target_qubit]}"
            if isinstance(target_qubit, int)
            else str(target_qubit)
        )
        x_j_list = [
            se.symbols(
                f"{self.bits[control_qubit]}"
                if isinstance(control_qubit, int)
                else str(control_qubit)
            )
            for control_qubit in control_qubits
        ]
        new_var = sp.Xor(x_i, sp.And(*x_j_list))
        update_var = logical_to_algebraic(new_var)
        new_P = self.P.subs(x_i, update_var)
        new_P = reduce_expression(new_P)
        new_f = self.f.sub(x_i, new_var)
        return PathSum(new_P, new_f, self.pathvar)
