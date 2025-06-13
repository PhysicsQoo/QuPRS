# src/QuPRS/pathsum/gates/two_qubit.py
from __future__ import annotations
from typing import TYPE_CHECKING
import symengine as se
import sympy as sp
import math
from sympy.logic.boolalg import to_anf
from QuPRS.utils.util import logical_to_algebraic, reduce_expression, div_pi, find_new_variables
from ..core import PathSum
from .. import reduction
from .base import gate

if TYPE_CHECKING:
    from ..core import PathSum

# --- Two-Qubit Gates ---
# Apply CX gate
@gate(type='two')
def cx(self: 'PathSum', control_qubit: int | str | se.Symbol, target_qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
    if not is_bra:
        new_f = self.f.update(target_qubit, to_anf(sp.Xor(self.f[control_qubit], self.f[target_qubit])))
        return PathSum(self.P, new_f, self.pathvar)
    else:
        x_i = se.symbols(f'{self.bits[target_qubit]}' if isinstance(target_qubit, int) else str(target_qubit))
        x_j = se.symbols(f'{self.bits[control_qubit]}' if isinstance(control_qubit, int) else str(control_qubit))
        new_var = sp.Xor(x_i, x_j)
        update_var = logical_to_algebraic(new_var)
        new_P = self.P.subs(x_i, update_var)
        new_P = reduce_expression(new_P)
        new_f = self.f.sub(x_i, new_var)
        return PathSum(new_P, new_f, self.pathvar)

# Apply CH gate
@gate(type='two')
def ch(self: 'PathSum', control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
    new_pathsum = self.s(target_qubit, is_bra)
    new_pathsum = new_pathsum.h(target_qubit, is_bra)
    new_pathsum = new_pathsum.t(target_qubit, is_bra)
    new_pathsum = new_pathsum.cx(control_qubit, target_qubit, is_bra)
    new_pathsum = new_pathsum.tdg(target_qubit, is_bra)
    new_pathsum = new_pathsum.h(target_qubit, is_bra)
    new_pathsum = new_pathsum.sdg(target_qubit, is_bra)
    return new_pathsum

# Apply CZ gate
@gate(type='two')
def cz(self: 'PathSum', control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
    if not is_bra:
        x_i = logical_to_algebraic(self.f[control_qubit], 1)
        x_j = logical_to_algebraic(self.f[target_qubit], 1)
        new_P = self.P + se.Rational(1, 2) * x_i * x_j
    else:
        x_i = se.symbols(f'{self.bits[control_qubit]}' if isinstance(control_qubit, int) else str(control_qubit))
        x_j = se.symbols(f'{self.bits[target_qubit]}' if isinstance(target_qubit, int) else str(target_qubit))
        new_P = self.P + se.Rational(1, 2) * x_i * x_j
    new_P = reduce_expression(new_P)
    return PathSum(new_P, self.f, self.pathvar)

# Apply CRk gate
@gate(type='two')
def CRk(self: 'PathSum', k: int, control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
    if not is_bra:
        x_i = logical_to_algebraic(self.f[control_qubit], k)
        x_j = logical_to_algebraic(self.f[target_qubit], k)
        new_P = self.P + se.Rational(1, 2**k) * x_i * x_j
    else:
        x_i = se.symbols(f'{self.bits[control_qubit]}' if isinstance(control_qubit, int) else str(control_qubit))
        x_j = se.symbols(f'{self.bits[target_qubit]}' if isinstance(target_qubit, int) else str(target_qubit))
        new_P = self.P + se.Rational(-1, 2**k) * x_i * x_j
    new_P = reduce_expression(new_P)
    return PathSum(new_P, self.f, self.pathvar)

# Apply CRk dagger gate
@gate(type='two')
def CRkdg(self: 'PathSum', k: int, control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
    if not is_bra:
        x_i = logical_to_algebraic(self.f[control_qubit], k)
        x_j = logical_to_algebraic(self.f[target_qubit], k)
        new_P = self.P + se.Rational(-1, 2**k) * x_i * x_j
    else:
        x_i = se.symbols(f'{self.bits[control_qubit]}' if isinstance(control_qubit, int) else str(control_qubit))
        x_j = se.symbols(f'{self.bits[target_qubit]}' if isinstance(target_qubit, int) else str(target_qubit))
        new_P = self.P + se.Rational(1, 2**k) * x_i * x_j
    new_P = reduce_expression(new_P)
    return PathSum(new_P, self.f, self.pathvar)

# Apply CRZ gate
@gate(type='two')
def crz(self: 'PathSum', theta, control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
    theta = div_pi(theta)
    if not is_bra:
        if theta.is_number:
            max_order = math.log2(theta.as_numer_denom()[1]) 
            max_order = int(max_order) +2 if int(max_order) == max_order else None
        else:
            max_order = None
        x_i = logical_to_algebraic(self.f[control_qubit], max_order=max_order)
        x_j = logical_to_algebraic(self.f[target_qubit], max_order=max_order)
        new_P = self.P + se.Rational(1, 4) * x_i * (-theta + 2 * theta * x_j)
    else:
        x_i = se.symbols(f'{self.bits[control_qubit]}' if isinstance(control_qubit, int) else str(control_qubit))
        x_j = se.symbols(f'{self.bits[target_qubit]}' if isinstance(target_qubit, int) else str(target_qubit))
        new_P = self.P + se.Rational(1, 4) * x_i * (theta - 2 * theta * x_j)
    new_P = reduce_expression(new_P)
    return PathSum(new_P, self.f, self.pathvar)

# Apply CRY gate
@gate(type='two')
def cry(self: 'PathSum', theta, control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
    new_pathsum = self.ry(theta/2, target_qubit, is_bra)
    new_pathsum = new_pathsum.cx(control_qubit, target_qubit, is_bra)
    new_pathsum = new_pathsum.ry(-theta/2, target_qubit, is_bra)
    new_pathsum = new_pathsum.cx(control_qubit, target_qubit, is_bra)
    return new_pathsum

# Apply CRX gate
@gate(type='two')
def crx(self: 'PathSum', theta, control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
    new_pathsum = self.h(target_qubit, is_bra)
    new_pathsum = new_pathsum.crz(theta, control_qubit, target_qubit, is_bra)
    new_pathsum = new_pathsum.h(target_qubit, is_bra)
    return new_pathsum

# Apply CP gate
@gate(type='two')
def cp(self: 'PathSum', theta, control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
    theta = div_pi(theta)
    if not is_bra:
        if theta.is_number:
            max_order = math.log2(theta.as_numer_denom()[1]) 
            max_order = int(max_order) +1 if int(max_order) == max_order else None
        else:
            max_order = None
        x_i = logical_to_algebraic(self.f[control_qubit], max_order=max_order)
        x_j = logical_to_algebraic(self.f[target_qubit], max_order=max_order)
        new_P = self.P + se.Rational(1, 2) * theta * x_i * x_j
    else:
        x_i = se.symbols(f'{self.bits[control_qubit]}' if isinstance(control_qubit, int) else str(control_qubit))
        x_j = se.symbols(f'{self.bits[target_qubit]}' if isinstance(target_qubit, int) else str(target_qubit))
        new_P = self.P - se.Rational(1, 2) * theta * x_i * x_j
    new_P = reduce_expression(new_P)
    return PathSum(new_P, self.f, self.pathvar)
@gate(type='two')
def cu1(self: 'PathSum', theta, control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
    return self.cp(theta, control_qubit, target_qubit, is_bra)
@gate(type='two')
def cu3(self: 'PathSum', theta, phi, lam, control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
    new_pathsum = self.crz(lam, control_qubit, target_qubit, is_bra)
    new_pathsum = new_pathsum.cry(theta, control_qubit, target_qubit, is_bra)
    new_pathsum = new_pathsum.crz(phi, control_qubit, target_qubit, is_bra)
    new_pathsum = new_pathsum.cp(se.Rational(1, 2) * (phi + lam), control_qubit, target_qubit, is_bra)  # global phase
    return new_pathsum
@gate(type='two')
def cu(self: 'PathSum', theta, phi, lam, gamma, control_qubit: int, target_qubit: int, is_bra: bool = False) -> 'PathSum':
    new_pathsum = self.cu3(theta, phi, lam, control_qubit, target_qubit, is_bra)
    new_pathsum = new_pathsum.cp(gamma, control_qubit, target_qubit, is_bra)
    return new_pathsum

# Apply SWAP gate
@gate(type='two')
def swap(self: 'PathSum', qubit1: int | str | se.Symbol, qubit2: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
    if not is_bra:
        new_P = self.P
        new_f = self.f.update(qubit1, self.f[qubit2])
        new_f = new_f.update(qubit2, self.f[qubit1])
    else:
        x_i = se.symbols(f'{self.bits[qubit1]}' if isinstance(qubit1, int) else str(qubit1))
        x_j = se.symbols(f'{self.bits[qubit2]}' if isinstance(qubit2, int) else str(qubit2))
        temp_sym = se.symbols('temp')
        new_P = self.P.subs({x_i:x_j, x_j:x_i})
        new_P = reduce_expression(new_P)
        # new_f = self.f.sub({x_i:temp_sym, x_j:x_i, temp_sym:x_j})
        new_f = self.f.sub(x_i,temp_sym)
        new_f = self.f.sub(x_j,x_i)
        new_f = self.f.sub(temp_sym,x_j)
    return PathSum(new_P, new_f, self.pathvar)