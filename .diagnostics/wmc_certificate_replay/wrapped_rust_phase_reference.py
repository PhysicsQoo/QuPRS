"""Fail-closed small wrapped-phase rational reference for Rust research only.

The existing general phase checker caps denominator at 1e10. For a tiny
represented phase whose fraction is near 0 or 1, use periodicity first,
then the same rigorous Machin pi and Taylor remainder intervals. This
bounds the *represented* coefficient and printed decimal; it does NOT
certify the original QASM->Rust phase translation or native solver floats.
"""
from fractions import Fraction as F
from math import gcd

from interval_wmc import (
    ComplexInterval, Interval, WeightedCNF, serialize_complex,
)
from import_dimacs import normalized_for_pathsum
from phase_coeff_reference import (
    ideal_rational_pi_phase, max_printed_ideal_component_gap,
    outward_decimal_interval, pi_interval, taylor_trig_at_rational,
    union_printed_and_ideal,
)

DENOMINATOR_LIMIT = 10**12
BASE_DENOMINATOR_LIMIT = 10**10
WRAP_RADIUS_LIMIT = F(1,10**6)


def local_wrapped_phase(numerator, denominator):
    if (type(numerator) is not int or type(denominator) is not int
            or denominator <= BASE_DENOMINATOR_LIMIT
            or denominator > DENOMINATOR_LIMIT
            or not 0 <= numerator < denominator
            or gcd(numerator,denominator) != 1):
        raise ValueError("Unverified high-denominator rational phase input")
    q = F(numerator,denominator)
    signed = q if q <= F(1,2) else q-1
    if abs(signed) > WRAP_RADIUS_LIMIT:
        raise ValueError("Large phase not within restricted integer wrap radius")
    # Exp(2*pi*i*q) = exp(2*pi*i*(q-k)), with k=0 or k=1.
    theta = pi_interval() * Interval.exact(2*signed)
    center = (theta.lower+theta.upper)/2
    radius = (theta.upper-theta.lower)/2
    # Radius is bounded by |sin'|,|cos'|<=1, and all arithmetic rational.
    real = taylor_trig_at_rational(center,cosine=True)
    imag = taylor_trig_at_rational(center,cosine=False)
    return ComplexInterval(
        outward_decimal_interval(Interval(real.lower-radius,real.upper+radius)),
        outward_decimal_interval(Interval(imag.lower-radius,imag.upper+radius)),
    )


def audited_represented_weight(numerator,denominator):
    return (local_wrapped_phase(numerator,denominator)
            if denominator > BASE_DENOMINATOR_LIMIT
            else ideal_rational_pi_phase(numerator,denominator))


def actual_rust_cnf_boolean_activation(cnf,phase_map):
    """Restricted one-bit case, exactly one Boolean witness for x0=0 and 1."""
    if len(cnf.weights) != 3 or len(phase_map)!=2:
        raise ValueError("Not a two-phase, one-bit Rust trace CNF")
    roles={}
    for var,(_,_,monomial) in phase_map.items():
        if monomial not in ("","0") or monomial in roles:
            raise ValueError("Unsupported phase monomial or duplicate")
        roles[monomial]=var
    if set(roles)!={"","0"} or len(set(roles.values()))!=2:
        raise ValueError("Unsupported RZ source phase activation set")
    remaining=set((1,2,3))-set(roles.values())
    if len(remaining)!=1:
        raise ValueError("Source bit CNF variable not unique")
    input_var=remaining.pop()
    solutions=[[],[]]
    for mask in range(1<<3):
        if all(any(bool(mask & (1<<(abs(l)-1))) == (l>0)
                   for l in clause) for clause in cnf.clauses):
            bit=int(bool(mask & (1<<(input_var-1))))
            solutions[bit].append(mask)
    if any(len(xs)!=1 for xs in solutions):
        raise ValueError("Not exactly one satisfying extension per source bit")
    m0,m1=solutions[0][0],solutions[1][0]
    enabled=lambda m,var:bool(m&(1<<(var-1)))
    if not (enabled(m0,roles[""]) and enabled(m1,roles[""])
            and not enabled(m0,roles["0"]) and enabled(m1,roles["0"])):
        raise ValueError("CNF phase literals are not source bit activation")
    return {
        "source_input_var":input_var,"input_zero_witness":str(m0),
        "input_one_witness":str(m1),"constant_phase_literal":roles[""],
        "bit_phase_literal":roles["0"],"activation_verified":True,
    }


def narrow_represented_cnf_reference(cnf, phase_map, *, num_qubits, num_pathvar):
    if num_qubits != 1 or num_pathvar != 0:
        raise ValueError("Unsupported tiny-RZ reference path variables")
    activation = actual_rust_cnf_boolean_activation(cnf,phase_map)
    fixed=[]
    rows=[]
    unit=ComplexInterval.exact(1)
    for i,(positive,negative) in enumerate(cnf.weights,1):
        if i in phase_map:
            numer,denom,monomial=phase_map[i]
            if negative!=unit or not 0<=numer<denom:
                raise ValueError("Unexpected Rust phase literal sign/weight")
            represented=audited_represented_weight(numer,denom)
            hull=union_printed_and_ideal(positive,represented)
            gap=max_printed_ideal_component_gap(positive,represented)
            fixed.append((hull,negative))
            rows.append({
                "positive_literal":i,
                "coefficient_numerator":numer,
                "coefficient_denominator":denom,
                "monomial":monomial,
                "represented_coeff_phase_interval":serialize_complex(represented),
                "represented_printed_component_gap_upper":str(gap),
                "wrapped_near_zero_or_integer":denom>BASE_DENOMINATOR_LIMIT,
            })
        else:
            if positive!=unit or negative!=unit:
                raise ValueError("Unattributed nonunit weighted literal")
            fixed.append((positive,negative))
    widened=WeightedCNF(cnf.clauses,tuple(fixed)).count()
    widened_norm=normalized_for_pathsum(
        widened,num_qubits=num_qubits,num_pathvar=num_pathvar)
    return widened,widened_norm,rows,activation
