import uuid
from itertools import combinations, count

import numpy as np
import symengine as se
import sympy as sp
from qiskit.circuit import Parameter, ParameterExpression
from qiskit.circuit.tools.pi_check import pi_check

from QuPRS import config
from QuPRS.cache_manager.cache_decorator import tracked_lru_cache

_one_div_pi = 1 / se.pi


@tracked_lru_cache(maxsize=4096)
def logical_to_algebraic(expr, max_order=None):
    def calculate_expr(algebraic_exprs, max_order):
        n = len(algebraic_exprs)
        max_order = max_order if max_order else n
        expr = 0
        coefficients = [0] * (max_order + 1)
        coefficients[1] = 1
        for order in range(2, max_order + 1):
            coefficients[order] = -2 * coefficients[order - 1]

        # Generate all combinations up to max_order
        all_combinations = []
        for order in range(1, max_order + 1):
            if order > n:
                break
            all_combinations.extend(combinations(range(n), order))

        # Calculate the expression
        for comb in all_combinations:
            term = se.Rational(coefficients[len(comb)], 1)
            for idx in comb:
                term *= algebraic_exprs[idx]
            expr += term
        return expr

    if expr.is_Symbol:
        return expr
    if expr is sp.true or (expr is se.S.true):
        return se.S.One
    if expr is sp.false or (expr is se.S.false):
        return se.S.Zero

    if isinstance(expr, sp.Xor):
        algebraic_exprs = [logical_to_algebraic(arg, max_order) for arg in expr.args]
        return calculate_expr(algebraic_exprs, max_order)
    elif isinstance(expr, sp.And):
        return se.Mul(*[logical_to_algebraic(arg, max_order) for arg in expr.args])
    elif isinstance(expr, sp.Or):
        terms = [logical_to_algebraic(arg, max_order) for arg in expr.args]
        return se.S.One - se.Mul(*[1 - term for term in terms])
    elif isinstance(expr, sp.Not):
        return se.S.One - logical_to_algebraic(expr.args[0], max_order)

    return expr


@tracked_lru_cache(maxsize=2048)
def algebraic_to_logical(expr: sp.Expr | se.Expr) -> sp.Expr:
    if expr.is_Add:
        factors = [algebraic_to_logical(arg) for arg in expr.args]
        expr = sp.Xor(*factors)
        return expr
    elif expr.is_Mul:
        factors = [algebraic_to_logical(arg) for arg in expr.args if not arg.is_Number]
        expr = sp.And(*factors)
        return expr
    else:
        return expr if not expr.is_Number else (expr > 0)


@tracked_lru_cache(maxsize=524288)
def process_term(term: se.Expr, mod_coeffs=1, linearize=True):

    tolerance = config.TOLERANCE

    if term.is_Mul:
        coeffs = []
        noncoeffs = []
        pi_flag = False

        for arg in term.args:
            if arg.is_Number:
                coeffs.append(arg)
            elif (
                linearize
                and arg.is_Pow
                and arg.args[1].is_positive
                and arg.args[1].is_integer
            ):
                noncoeffs.append(arg.args[0])
            elif arg == se.pi or arg == _one_div_pi:
                pi_flag = True
                coeffs.append(arg)
            else:
                noncoeffs.append(arg)
        coeff = se.Mul(*coeffs)
        if mod_coeffs and not pi_flag:
            coeff = coeff % mod_coeffs
            if coeff <= tolerance or coeff >= mod_coeffs - tolerance:
                return se.S.Zero

        return se.Mul(coeff, *noncoeffs)
    elif term.is_Number:
        term = term % mod_coeffs
        if term <= tolerance or term >= mod_coeffs - tolerance:
            return se.S.Zero
        return term
    else:
        if mod_coeffs == 1:
            return se.S.Zero
        else:
            return term


@tracked_lru_cache(maxsize=65536)
def reduce_expression(expr: se.Expr, mod_coeffs=1, linearize=True):
    expanded_expr = expr.expand()
    if expanded_expr.is_Add:
        # Process each term in the expanded expression
        processed_terms = [
            process_term(term, mod_coeffs, linearize) for term in expanded_expr.args
        ]
        # Combine the processed terms
        result = se.Add(*processed_terms)
    else:
        # Process the single term
        result = process_term(expanded_expr, mod_coeffs, linearize)
    return result


@tracked_lru_cache(maxsize=1024)
def div_pi(theta: se.Expr | sp.Expr | float | Parameter | ParameterExpression):
    if isinstance(theta, Parameter) or isinstance(theta, ParameterExpression):
        theta = se.sympify(
            pi_check(theta, output="qasm").replace("[", "_").replace("]", "")
        )
        theta = (theta / se.pi).expand()
    elif isinstance(theta, float):
        theta = se.sympify(sp.Rational(theta / np.pi)).expand()
    else:
        theta = theta / se.pi
    return theta


def fraction_to_nearest_binary(numerator, denominator, precision=10):
    # Get the integer part and fraction part
    integer_part = numerator // denominator
    fraction = numerator % denominator / denominator

    # Convert the integer part to binary
    binary_integer_part = bin(integer_part)[2:]  # Remove '0b'

    # Initialize the binary fraction string
    binary_fraction_part = "."

    # Calculate the binary representation of the fraction part
    for _ in range(precision):
        fraction *= 2
        bit = int(fraction)
        binary_fraction_part += str(bit)
        # Remove the integer part, keep the fraction part for the next calculation
        fraction -= bit

    # Rounding: check the next bit to decide whether to carry
    if fraction >= 0.5:
        # Carry from the last bit to the front
        binary_fraction_part = list(binary_fraction_part)
        for i in range(len(binary_fraction_part) - 1, 0, -1):
            if binary_fraction_part[i] == "1":
                binary_fraction_part[i] = "0"
            elif binary_fraction_part[i] == ".":
                continue
            else:
                binary_fraction_part[i] = "1"
                break
        else:
            # If all bits are carried to the front, add a '1' after the decimal point
            binary_fraction_part.insert(1, "1")

        binary_fraction_part = "".join(binary_fraction_part)

    # Final result
    return binary_integer_part + binary_fraction_part


def get_theta(imag, real):
    """Use np.arctan2 to directly calculate the θ value of e^(2πiθ) = z"""
    theta = np.arctan2(imag, real)
    theta = theta if theta >= 0 else theta + 2 * np.pi
    return theta


def find_new_variables(pathvar: set | frozenset, num_vars_needed=1) -> list[se.Symbol]:
    new_vars = []
    for i in count():
        if len(new_vars) >= num_vars_needed:
            break
        candidate_var = se.Symbol(f"y_{i}")
        if candidate_var not in pathvar:
            new_vars.append(candidate_var)
    return new_vars


def generate_unique_key():
    unique_key = str(uuid.uuid4())
    return unique_key
