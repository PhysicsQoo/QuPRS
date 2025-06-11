import symengine as se
import sympy as sp
from QuPRS.utils.util import reduce_expression, algebraic_to_logical, logical_to_algebraic
import math
from QuPRS import config

def match_Elim(P, reducible_vars):
    P_free_symbols = P.free_symbols
    for yo_val in reducible_vars:
        if yo_val not in P_free_symbols:
            return yo_val
    return None

def match_HH(P, reducible_vars, pathvar, bits):
    P_expanded = P.expand()
    valid_symbols = {str(bit) for bit in bits}.union(str(var) for var in pathvar)

    for yo_val in reducible_vars:
        P_coeff = P_expanded.coeff(yo_val)
        possible_yi = [yi_val for yi_val in P_coeff.free_symbols if yi_val in pathvar and yi_val != yo_val]

        for yi_val in possible_yi:
            Q_val = reduce_expression((2 * P_coeff - yi_val), 2)
            Q_val_free_symbols = Q_val.free_symbols
            if (
                not yi_val in Q_val_free_symbols
                and all(str(symbol) in valid_symbols for symbol in Q_val_free_symbols)
                and reduce_expression(Q_val).is_zero
            ):
                R_val = (P_expanded - yo_val * P_coeff).expand()
                return yo_val, yi_val, Q_val, R_val

    return None, None, None, None

def match_omega(P, reducible_vars, pathvar, bits):
    tolerance = config.TOLERANCE
    P_expanded = P.expand()
    valid_symbols = {str(bit) for bit in bits}.union(str(var) for var in pathvar)
    for yo_val in reducible_vars:
        coeff = P_expanded.coeff(yo_val)
        for term in coeff.args:
            if isinstance(term, se.Rational):
                if abs(term - se.Rational(1, 4)) <= tolerance:
                    return_flag = True
                elif abs(term - se.Rational(3, 4)) <= tolerance:
                    return_flag = False
                else:
                    break

                Q_val = (2 * (coeff - term))
                Q_val = reduce_expression(Q_val, 2)

                if (
                    all(str(symbol) in valid_symbols for symbol in Q_val.free_symbols) 
                    and reduce_expression(Q_val).is_zero
                ):
                    R_val = (P_expanded - yo_val * coeff).expand()
                    return yo_val, Q_val, R_val, return_flag

    return None, None, None, None

def HH_reduction(pathsum, yo_val, yi_val, Q_val, R_val):
    Q_val = algebraic_to_logical(Q_val)
    
    new_f = pathsum.f
    new_f = new_f.sub(yi_val, Q_val)

    
    if yi_val in R_val.free_symbols:
        coeff_yval= sp.sympify(R_val.coeff(yi_val))
        if all(item in set(pathsum.pathvar).union(pathsum.bits) for item in coeff_yval.free_symbols):
            coeff_R = set(coeff_yval.as_coefficients_dict().values())

            order_R = [math.log2(item.as_numer_denom()[1]) for item in coeff_R if item != 0]
            if all([int(item) == item for item in order_R]):
                Q_val = logical_to_algebraic(Q_val, max_order=int(max(order_R)))
        else:
            Q_val = logical_to_algebraic(Q_val)

        new_P = R_val.subs({yi_val: Q_val})
        new_P = reduce_expression(new_P)
    else:
        new_P = R_val

    new_pathvar = set(pathsum.pathvar)
    new_pathvar.remove(yo_val)
    new_pathvar = frozenset(new_pathvar)
    new_pathsum = pathsum.__class__(new_P, new_f, new_pathvar)
    return new_pathsum

def omega_reduction(pathsum, yo_val, Q_val, R_val, return_flag):
    Q_val = algebraic_to_logical(Q_val)
    Q_val = logical_to_algebraic(Q_val, 2)
    if return_flag:
        new_P = se.Rational(1, 8) - se.Rational(1, 4) * Q_val + R_val
    else:
        new_P = se.Rational(-1, 8) + se.Rational(1, 4) * Q_val + R_val
    new_P = reduce_expression(new_P)
    new_pathvar = set(pathsum.pathvar)
    new_pathvar.remove(yo_val)

    new_pathsum = pathsum.__class__(new_P, pathsum.f, frozenset(new_pathvar))
    
    return new_pathsum
