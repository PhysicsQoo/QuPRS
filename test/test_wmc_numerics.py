"""Floating WMC acceptance fixtures, independent of solver implementation."""
import cmath
import math
import pytest
from qiskit import QuantumCircuit

from QuPRS import check_equivalence, config
from QuPRS.interface.ps2wmc import run_wmc, wlogi_to_clauses
from QuPRS.utils.wmc_solvers import classify_weighted_count
import symengine as se
import sympy as sp


# Mode 6 prints nine significant digits. This is a fixture comparison budget,
# not an error bound for arbitrary circuits or an equivalence tolerance.
COUNT_REL_TOL = 1e-8
COUNT_ABS_TOL = 1e-12


@pytest.mark.parametrize('positive,negative', [
    (complex(1.23456789123, -2.34567891234), complex(1, 0)),
    (complex(1e-12, -2.5e-11), complex(1, 0)),
    (complex(1.5, .25), complex(-1.5, -.25)),
    (complex(1.5, .25), complex(-1.5 + 1e-8, -.25)),
])
def test_floating_counts_match_hand_computed_models(tmp_path, positive, negative):
    counts = {}
    expected = positive + negative
    for solver in ('ganak', 'gpmc'):
        weights = []
        for literal, z in ((1, positive), (-1, negative)):
            if solver == 'ganak':
                value = f'{z.real:.17g} {"+" if z.imag >= 0 else "-"} {abs(z.imag):.17g}i'
            else:
                value = f'{z.real:.17g} {z.imag:.17g}'
            weights.append(f'c p weight {literal} {value} 0')
        cnf = tmp_path / f'{solver}.cnf'
        cnf.write_text('p cnf 1 0\nc t wmc\n' + '\n'.join(weights) + '\n')
        counts[solver] = complex(*run_wmc(str(cnf), solver))
        assert counts[solver] == pytest.approx(expected, rel=COUNT_REL_TOL, abs=COUNT_ABS_TOL)
    assert counts['ganak'] == pytest.approx(counts['gpmc'], rel=COUNT_REL_TOL, abs=COUNT_ABS_TOL)


@pytest.mark.parametrize('solver', ['ganak', 'gpmc'])
@pytest.mark.parametrize('fraction,expected', [(0.99, 'equivalent'), (1.01, 'not_equivalent')])
def test_python_normalized_magnitude_boundary(monkeypatch, solver, fraction, expected):
    import QuPRS.interface.ps2wmc as adapter
    # HH yields expected log2=2; compare normalized amplitude without
    # rounding log2 to three decimal places (the old Python-only behavior).
    count = 4 * (1 - fraction * config.WMC_MAGNITUDE_TOLERANCE)
    monkeypatch.setattr(adapter, 'run_wmc', lambda *args: (count, 0.0))
    identity = QuantumCircuit(1)
    hh = QuantumCircuit(1)
    hh.h(0)
    hh.h(0)
    result = check_equivalence(identity, hh, method='wmc_only', tool_name=solver, backend='python')
    assert result.equivalent == expected


@pytest.mark.parametrize('solver', ['ganak', 'gpmc'])
@pytest.mark.parametrize('backend,angle,accepted', [
    ('python', 0.0, True), ('python', 0.0026, True), ('python', 0.003, False),
    ('rust', 0.0, True), ('rust', 0.0026, True), ('rust', 0.003, False),
])
def test_real_solvers_near_existing_decision_boundaries(backend, solver, angle, accepted):
    # |tr(RZ(angle))|/2 = cos(angle/2). Both Python and Rust now use
    # the same normalized-magnitude boundary of 1e-6.
    identity = QuantumCircuit(1)
    circuit = QuantumCircuit(1)
    circuit.h(0)
    circuit.rz(angle, 0)
    circuit.h(0)
    result = check_equivalence(identity, circuit, method='wmc_only', tool_name=solver, backend=backend)
    if accepted:
        assert result.equivalent in {'equivalent', 'equivalent*'}
    else:
        assert result.equivalent == 'not_equivalent'


@pytest.mark.parametrize('solver', ['ganak', 'gpmc'])
def test_large_normalization_identity_with_real_solver(solver):
    identity = QuantumCircuit(1)
    hh = QuantumCircuit(1)
    for _ in range(60):
        hh.h(0)
    # Expected count 2**31 needs more significant digits than mode 6 prints.
    result = check_equivalence(identity, hh, method='wmc_only', tool_name=solver, backend='python')
    assert result.equivalent == 'equivalent'


@pytest.mark.parametrize('solver', ['ganak', 'gpmc'])
@pytest.mark.parametrize('fraction,expected', [(0.99, 'equivalent'), (1.01, 'equivalent*')])
def test_phase_boundary_with_real_floating_counts(tmp_path, monkeypatch, solver, fraction, expected):
    import QuPRS.interface.ps2wmc as adapter
    phase = fraction * config.WMC_PHASE_TOLERANCE
    count = 4 * cmath.exp(1j * phase)
    if solver == 'ganak':
        weight = f'{count.real:.17g} + {count.imag:.17g}i'
        negative = '1 + 0i'
    else:
        weight = f'{count.real:.17g} {count.imag:.17g}'
        negative = '1 0'
    cnf = tmp_path / 'phase.cnf'
    cnf.write_text(f'p cnf 1 1\nc t wmc\nc p weight 1 {weight} 0\n'
                   f'c p weight -1 {negative} 0\n1 0\n')
    real_count = run_wmc(str(cnf), solver)
    assert complex(*real_count) == pytest.approx(count, rel=COUNT_REL_TOL, abs=COUNT_ABS_TOL)
    # Inject only the analytically defined count: the real solver and parser
    # above run unchanged; this isolates the public Python decision boundary.
    monkeypatch.setattr(adapter, 'run_wmc', lambda *args: real_count)
    identity = QuantumCircuit(1)
    hh = QuantumCircuit(1)
    hh.h(0)
    hh.h(0)
    result = check_equivalence(identity, hh, method='wmc_only', tool_name=solver, backend='python')
    assert result.equivalent == expected


@pytest.mark.parametrize('solver', ['ganak', 'gpmc'])
def test_python_dimacs_weights_do_not_truncate_before_solver(solver):
    # A non-Clifford symbolic phase should preserve substantially more than
    # the nine digits formerly written by Rust's GPMC adapter.
    weights, _, _ = wlogi_to_clauses(
        [(se.Rational(1, 7), sp.true)], {}, tool_name=solver,
    )
    fields = weights[0].split()
    re = fields[4]
    assert abs(float(re) - math.cos(2 * math.pi / 7)) < 1e-15
    assert len(re) >= 17  # at least binary64 round-trip precision



@pytest.mark.parametrize('fraction', [
    se.Rational(1, 7), se.Rational(1, 13), se.Rational(9, 37),
])
def test_python_113_bit_weights_match_independent_oracle(fraction):
    # The original length/f64 checks cannot tell a genuine 113-bit result
    # from a padded 53-bit intermediate. mpmath provides an independent
    # 80-decimal-digit reference, with no binary64 cast on either side.
    from mpmath import mp

    phase = 2 * se.pi * fraction
    actual_real = se.cos(phase).evalf(113)
    actual_imag = se.sin(phase).evalf(113)
    with mp.workdps(80):
        angle = 2 * mp.pi * mp.mpf(str(fraction.p)) / mp.mpf(str(fraction.q))
        ref_real, ref_imag = mp.cos(angle), mp.sin(angle)
        error = max(
            abs(mp.mpf(str(actual_real)) - ref_real),
            abs(mp.mpf(str(actual_imag)) - ref_imag),
        )
        # 113 binary bits ~= 34 decimal digits. Allow representation and
        # decimal-print conversion noise but reject silent f64 fallback.
        assert error < mp.mpf("1e-29"), (
            f"113-bit SymEngine phase={fraction} has error={mp.nstr(error, 12)}; "
            f"real={actual_real}, imag={actual_imag}"
        )

def test_python_wmc_count_classification_is_stable_for_extremes():
    kwargs = dict(magnitude_tolerance=1e-6, phase_tolerance=1e-6)
    status, log_value = classify_weighted_count(1e300, 0.0, math.log2(1e300), **kwargs)
    assert status == 'equivalent'
    assert math.isfinite(log_value)

    assert classify_weighted_count(0.0, 0.0, 2.0, **kwargs)[0] == 'not_equivalent'
    assert classify_weighted_count(4.0, -1.9e-6, 2.0, **kwargs)[0] == 'equivalent'
    assert classify_weighted_count(0.0, 4.0, 2.0, **kwargs)[0] == 'equivalent*'
    with pytest.raises(ValueError, match='Non-finite'):
        classify_weighted_count(math.inf, 0.0, 2.0, **kwargs)
