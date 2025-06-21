# src/QuPRS/pathsum/gates/multi_qubit.py

from __future__ import annotations

import symengine as se
import sympy as sp
from sympy.logic.boolalg import to_anf

from QuPRS.utils.util import logical_to_algebraic, reduce_expression

from ..core import PathSum
from .base import MultiQubitGate

# --- Multi-Qubit Gate Implementations ---


class CCXGate(MultiQubitGate):
    gate_name = "ccx"

    def apply(
        self,
        pathsum: "PathSum",
        control_qubit1: int | str | se.Symbol,
        control_qubit2: int | str | se.Symbol,
        target_qubit: int | str | se.Symbol,
        is_bra: bool = False,
    ) -> "PathSum":
        if not is_bra:
            new_f = pathsum.f.update(
                target_qubit,
                to_anf(
                    sp.Xor(
                        pathsum.f[target_qubit],
                        sp.And(pathsum.f[control_qubit1], pathsum.f[control_qubit2]),
                    )
                ),
            )
            return PathSum(pathsum.P, new_f, pathsum.pathvar)
        else:
            x_i = se.symbols(
                f"{pathsum.bits[target_qubit]}"
                if isinstance(target_qubit, int)
                else str(target_qubit)
            )
            x_j = se.symbols(
                f"{pathsum.bits[control_qubit1]}"
                if isinstance(control_qubit1, int)
                else str(control_qubit1)
            )
            x_k = se.symbols(
                f"{pathsum.bits[control_qubit2]}"
                if isinstance(control_qubit2, int)
                else str(control_qubit2)
            )
            new_var = sp.Xor(x_i, sp.And(x_j, x_k))
            update_var = logical_to_algebraic(new_var)
            new_P = pathsum.P.subs(x_i, update_var)
            new_P = reduce_expression(new_P)
            new_f = pathsum.f.sub(x_i, new_var)
            return PathSum(new_P, new_f, pathsum.pathvar)


class MCXGate(MultiQubitGate):
    gate_name = "mcx"

    def apply(
        self, pathsum: "PathSum", *qubits: int | str | se.Symbol, is_bra: bool = False
    ) -> "PathSum":
        if len(qubits) < 2:
            raise ValueError(
                "MCXGate requires at least one control and one target qubit."
            )

        target_qubit = qubits[-1]
        control_qubits = qubits[0:-1]

        if not is_bra:
            control_fs = [pathsum.f[i] for i in control_qubits]
            new_f = pathsum.f.update(
                target_qubit,
                to_anf(sp.Xor(pathsum.f[target_qubit], sp.And(*control_fs))),
            )
            return PathSum(pathsum.P, new_f, pathsum.pathvar)
        else:
            x_i = se.symbols(
                f"{pathsum.bits[target_qubit]}"
                if isinstance(target_qubit, int)
                else str(target_qubit)
            )
            x_j_list = [
                se.symbols(
                    f"{pathsum.bits[control_qubit]}"
                    if isinstance(control_qubit, int)
                    else str(control_qubit)
                )
                for control_qubit in control_qubits
            ]
            new_var = sp.Xor(x_i, sp.And(*x_j_list))
            update_var = logical_to_algebraic(new_var)
            new_P = pathsum.P.subs(x_i, update_var)
            new_P = reduce_expression(new_P)
            new_f = pathsum.f.sub(x_i, new_var)
            return PathSum(new_P, new_f, pathsum.pathvar)
