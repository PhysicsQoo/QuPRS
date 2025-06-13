# src/QuPRS/pathsum/gates/single_qubit.py
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

# --- Single-Qubit Gates ---

@gate(type='single')
def h(self: 'PathSum', qubit: int | str, is_bra: bool = False) -> 'PathSum':
    new_var = find_new_variables(self.pathvar)[0]
    if not is_bra:
        x_i = logical_to_algebraic(self.f[qubit], 1)
        new_P = self.P + se.Rational(1, 2) * new_var * x_i
        new_f = self.f.update(qubit, new_var)
    else:
        x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
        new_P = self.P.subs(x_i, new_var) + se.Rational(1, 2) * new_var * x_i
        new_f = self.f.sub(x_i, logical_to_algebraic(new_var))
    new_pathvar = frozenset(set(self.pathvar).union({new_var}))
    new_pathsum = PathSum(new_P, new_f, new_pathvar)
    return reduction.apply_reduction(new_pathsum)

# Apply X gate
@gate(type='single')
def x(self: 'PathSum', qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
    if not is_bra:
        new_P = self.P
        new_f = self.f.update(qubit, to_anf(sp.Not(self.f[qubit])))
    else:
        x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
        new_P = self.P.subs(x_i, 1 - x_i)
        new_f = self.f.sub(x_i, sp.Not(x_i))
    new_P = reduce_expression(new_P)
    return PathSum(new_P, new_f, self.pathvar)

# Apply Y gate
@gate(type='single')
def y(self: 'PathSum', qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
    if not is_bra:
        x_i = logical_to_algebraic(self.f[qubit], 1)
        new_P = (self.P + se.Rational(3, 4) + se.Rational(1, 2) * x_i).expand()
        new_f = self.f.update(qubit, to_anf(sp.Not(self.f[qubit])))
    else:
        x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
        new_P = (self.P.subs(x_i, 1 - x_i) + se.Rational(3, 4) + se.Rational(1, 2) * x_i).expand()
        new_f = self.f.sub(x_i, sp.Not(x_i))
    new_P = reduce_expression(new_P)
    return PathSum(new_P, new_f, self.pathvar)

# Apply Z gate
@gate(type='single')
def z(self: 'PathSum', qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
    if not is_bra:
        x_i = logical_to_algebraic(self.f[qubit], 1)
        new_P = (self.P + se.Rational(1, 2) * x_i).expand()
    else:
        x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
        new_P = (self.P + se.Rational(1, 2) * x_i).expand()
    new_P = reduce_expression(new_P)
    return PathSum(new_P, self.f, self.pathvar)

# Apply S gate
@gate(type='single')
def s(self: 'PathSum', qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
    if not is_bra:
        x_i = logical_to_algebraic(self.f[qubit], 2)
        new_P = (self.P + se.Rational(1, 4) * x_i).expand()
    else:
        x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
        new_P = (self.P + se.Rational(-1, 4) * x_i).expand()
    new_P = reduce_expression(new_P)
    return PathSum(new_P, self.f, self.pathvar)

# Apply Sdg gate
@gate(type='single')
def sdg(self: 'PathSum', qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
    if not is_bra:
        x_i = logical_to_algebraic(self.f[qubit], 2)
        new_P = (self.P + se.Rational(-1, 4) * x_i).expand()
    else:
        x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
        new_P = (self.P + se.Rational(1, 4) * x_i).expand()
    new_P = reduce_expression(new_P)
    return PathSum(new_P, self.f, self.pathvar)

# Apply T gate
@gate(type='single')
def t(self: 'PathSum', qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
    if not is_bra:
        x_i = logical_to_algebraic(self.f[qubit], 3)
        new_P = (self.P + se.Rational(1, 8) * x_i).expand()
    else:
        x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
        new_P = (self.P + se.Rational(-1, 8) * x_i).expand()
    new_P = reduce_expression(new_P)
    return PathSum(new_P, self.f, self.pathvar)

# Apply Tdg gate
@gate(type='single')
def tdg(self: 'PathSum', qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
    if not is_bra:
        x_i = logical_to_algebraic(self.f[qubit], 3)
        new_P = (self.P + se.Rational(-1, 8) * x_i).expand()
    else:
        x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
        new_P = self.P + se.Rational(1, 8) * x_i
    new_P = reduce_expression(new_P)
    return PathSum(new_P, self.f, self.pathvar)

# Apply Sx gate
@gate(type='single')
def sx(self: 'PathSum', qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
    self = self.rx(se.pi / 2, qubit, is_bra)
    new_P = self.P + se.Rational(1, 8) if not is_bra else self.P - se.Rational(1, 8)
    new_P = reduce_expression(new_P)
    return PathSum(new_P, self.f, self.pathvar)

# Apply Sxdg gate
@gate(type='single')
def sxdg(self: 'PathSum', qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
    self = self.rx(-se.pi / 2, qubit, is_bra)
    new_P = self.P - se.Rational(1, 8) if not is_bra else self.P + se.Rational(1, 8)
    new_P = reduce_expression(new_P)
    return PathSum(new_P, self.f, self.pathvar)

# Apply P gate
@gate(type='single')
def p(self: 'PathSum', theta, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
    theta = div_pi(theta)
    if not is_bra:
        if theta.is_number:
            max_order = math.log2(theta.as_numer_denom()[1])
            max_order = int(max_order) + 1 if int(max_order) == max_order else None
        else:
            max_order = None
        x_i = logical_to_algebraic(self.f[qubit], max_order=max_order)
        new_P = self.P + se.Rational(1, 2) * theta * x_i
    else:
        x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
        new_P = self.P - se.Rational(1, 2) * theta * x_i
    new_P = reduce_expression(new_P)
    return PathSum(new_P, self.f, self.pathvar)

# Apply Rz gate
@gate(type='single')
def rz(self: 'PathSum', theta, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
    theta = div_pi(theta)
    if not is_bra:
        if theta.is_number:
            max_order = math.log2(theta.as_numer_denom()[1])
            max_order = int(max_order) + 2 if int(max_order) == max_order else None
        else:
            max_order = None
        x_i = logical_to_algebraic(self.f[qubit], max_order=max_order)
        new_P = self.P + se.Rational(1, 4) * (-theta + 2 * theta * x_i)
    else:
        x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
        new_P = self.P + se.Rational(1, 4) * (theta - 2 * theta * x_i)
    new_P = reduce_expression(new_P)
    return PathSum(new_P, self.f, self.pathvar)

# Apply Rx gate
@gate(type='single')
def rx(self: 'PathSum', theta, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
    return self.u(theta, -se.pi / 2, se.pi / 2, qubit, is_bra)

# Apply Ry gate
@gate(type='single')
def ry(self: 'PathSum', theta, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
    return self.u(theta, 0, 0, qubit, is_bra)

# Apply U gate
@gate(type='single')
def u(self: 'PathSum', theta, phi, lam, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
    theta, phi, lam = map(div_pi, [theta, phi, lam])
    new_vars = find_new_variables(self.pathvar, 2)
    if not is_bra:
        if lam.is_number:
            max_order = math.log2(lam.as_numer_denom()[1]) 
            max_order = int(max_order) +1 if int(max_order) == max_order else None
        else:
            max_order = None
        x_i_lam = logical_to_algebraic(self.f[qubit], max_order=max_order)
        x_i = logical_to_algebraic(self.f[qubit], max_order=2 )
        new_P = self.P + se.Rational(1, 2) * lam * x_i_lam + \
                    se.Rational(1, 2) * phi * new_vars[1] + \
                    se.Rational(1, 4) * theta * (2 * new_vars[0] - 1) + \
                    se.Rational(3, 4) * x_i + \
                    se.Rational(1, 4) * new_vars[1] + \
                    se.Rational(1, 2) * x_i * new_vars[0] + \
                    se.Rational(1, 2) * new_vars[0] * new_vars[1]
        new_f = self.f.update(qubit, new_vars[1])
    else:
        x_i = se.symbols(f'{self.bits[qubit]}' if isinstance(qubit, int) else str(qubit))
        new_P = self.P.subs(x_i, new_vars[1]) + \
                    se.Rational(-1, 2) * phi * x_i + \
                    se.Rational(-1, 2) * lam * new_vars[1] + \
                    se.Rational(1, 4) * theta * (2 * new_vars[0] - 1) + \
                    se.Rational(1, 4) * x_i + \
                    se.Rational(3, 4) * new_vars[1] + \
                    se.Rational(1, 2) * x_i * new_vars[0] + \
                    se.Rational(1, 2) * new_vars[0] * new_vars[1]
        new_f = self.f.sub(x_i, logical_to_algebraic(new_vars[1]))
    new_pathvar = frozenset(set(self.pathvar).union(new_vars))
    new_pathsum = PathSum(new_P, new_f, new_pathvar)
    return reduction.apply_reduction(new_pathsum)

@gate(type='single')
def u1(self: 'PathSum', theta, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
    return self.p(theta, qubit, is_bra)

@gate(type='single')
def u2(self: 'PathSum', phi, lam, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
    return self.u(se.Rational(1, 2) * se.pi, phi, lam, qubit, is_bra)

@gate(type='single')
def u3(self: 'PathSum', theta, phi, lam, qubit: int | str | se.Symbol, is_bra: bool = False) -> 'PathSum':
    return self.u(theta, phi, lam, qubit, is_bra)