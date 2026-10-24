#!/usr/bin/env python3
"""Serialize a small exact-rational interval WMC reference experiment."""
import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path

from interval_wmc import (
    ComplexInterval, WeightedCNF, normalized_magnitude,
    serialize_complex, serialize_interval, unit_phase_rational_radians,
)


def phasor_case(angle):
    half = angle / 2
    return WeightedCNF((), ((unit_phase_rational_radians(half),
                             unit_phase_rational_radians(-half)),))


def records():
    one = ComplexInterval.exact(1)
    cases = [
        ('identity', WeightedCNF((), ((one, one),)), 2,
         'exact_identity', 'trace_model'),
        ('global_phase_i', WeightedCNF((), ((ComplexInterval.exact(0, 1),
                                            ComplexInterval.exact(0, 1)),)), 2,
         'global_phase', 'trace_model'),
        ('rz_delta_1e-3', phasor_case(Fraction(1, 1000)), 2,
         'strict_inequivalent', 'trace_model'),
        ('rz_delta_1e-6', phasor_case(Fraction(1, 10**6)), 2,
         'strict_inequivalent', 'trace_model'),
        ('rz_delta_1e-2', phasor_case(Fraction(1, 100)), 2,
         'strict_inequivalent', 'trace_model'),
        ('weighted_xor', WeightedCNF(((1, 2), (-1, -2)),
                                    ((ComplexInterval.exact(1), ComplexInterval.exact(2)),
                                     (ComplexInterval.exact(3), ComplexInterval.exact(4)))), 1,
         'exact_count_10', 'generic_cnf'),
    ]
    for name, cnf, normalization, expected, model_type in cases:
        count = cnf.count()
        mag = normalized_magnitude(count, normalization)
        is_less_than_one = mag.upper < 1
        is_exactly_one = mag.lower == mag.upper == 1
        passed = (is_less_than_one if expected == 'strict_inequivalent'
                  else is_exactly_one if expected in ('exact_identity', 'global_phase')
                  else count == ComplexInterval.exact(10))
        yield dict(
            name=name, model_type=model_type,
            expected_reference_property=expected,
            source_angular_semantics=('exact rational radians' if name.startswith('rz_')
                                     else 'exact integer weights'),
            clauses=[list(clause) for clause in cnf.clauses],
            weights=[dict(positive=serialize_complex(pos),
                          negative=serialize_complex(neg)) for pos, neg in cnf.weights],
            normalization=normalization,
            count=serialize_complex(count),
            normalized_magnitude=serialize_interval(mag),
            upper_strictly_below_one=is_less_than_one,
            exact_unit_magnitude=is_exactly_one,
            reference_property_passed=passed,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('interval-wmc-reference-results'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    result = list(records())
    payload = dict(
        schema='small-weighted-cnf-rational-interval-v1',
        arithmetic='stdlib Fraction: exact rational + enclosing alternating Taylor series',
        limits=dict(max_variables=12, radian_phase_abs_at_most='1',
                    sqrt_decimal_digits=35),
        certification_scope=('Only the explicitly constructed weighted CNF '
                             'and exact-rational-radian RZ trace examples; '
                             'no inference about QuPRS Path-sum encoding, '
                             'native GPMC/Ganak numerical error, or general quantum circuits'),
        cases=result,
        status='PASS' if all(row['reference_property_passed'] for row in result) else 'FAIL',
    )
    raw = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + '\n'
    filename = args.output / 'reference-results.json'
    filename.write_text(raw, encoding='utf-8')
    (args.output / 'reference-results.sha256').write_text(
        f'{hashlib.sha256(raw.encode()).hexdigest()}  reference-results.json\n', encoding='utf-8'
    )
    print(json.dumps({'status': payload['status'], 'cases': len(result),
                      'negative_strict_bounds': sum(r['upper_strictly_below_one'] for r in result),
                      'output': str(filename)}, sort_keys=True))
    return int(payload['status'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
