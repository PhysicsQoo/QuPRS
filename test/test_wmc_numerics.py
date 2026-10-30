"""Floating WMC acceptance fixtures, independent of solver implementation."""
import cmath
import math
import pytest
from qiskit import QuantumCircuit

from QuPRS import check_equivalence, config
from QuPRS.interface.ps2wmc import run_wmc, wlogi_to_clauses
from QuPRS.utils.precision_count import parse_printed_count_line, classify_printed_distance, classify_observed_distance
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


@pytest.mark.parametrize('fraction,expected', [(0.99, 'equivalent'), (1.01, 'not_equivalent')])
def test_printed_projective_distance_boundary(fraction, expected):
    from mpmath import mp
    epsilon = 2e-4
    with mp.workdps(90):
        eps = mp.mpf('0.0002')
        threshold = eps**2 / (1 + mp.sqrt(1 - eps**2))
        normalized = 1 - mp.mpf(str(fraction)) * threshold
        raw = mp.nstr(4 * normalized, 70)
    count = parse_printed_count_line('c s exact quadruple float ' + raw)
    assert classify_printed_distance(count, 4, epsilon).status == expected


@pytest.mark.parametrize('solver', ['ganak', 'gpmc'])
@pytest.mark.parametrize('backend,angle,accepted', [
    ('python', 0.0, True), ('python', 0.0026, True), ('python', 0.003, False),
    ('rust', 0.0, True), ('rust', 0.0026, True), ('rust', 0.003, False),
])
def test_real_solvers_near_existing_decision_boundaries(backend, solver, angle, accepted):
    # D_proj(I, Rz(angle)) = abs(sin(angle/2)).
    identity = QuantumCircuit(1)
    circuit = QuantumCircuit(1)
    circuit.h(0)
    circuit.rz(angle, 0)
    circuit.h(0)
    # Equivalent distance threshold for the retired 1e-6 magnitude budget.
    result = check_equivalence(
        identity, circuit, method='wmc_only', tool_name=solver,
        backend=backend, approximate_distance_tolerance=0.0014142132,
        wmc_phase_tolerance=1e-6,
    )
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
    assert result.equivalent in ('equivalent', 'unknown')


@pytest.mark.parametrize('fraction,expected', [(0.99, 'equivalent'), (1.01, 'equivalent*')])
def test_phase_boundary_with_printed_complex_counts(fraction, expected):
    from mpmath import mp
    with mp.workdps(90):
        phase = mp.mpf(str(fraction)) * mp.mpf(str(config.WMC_PHASE_TOLERANCE))
        real = mp.nstr(4 * mp.cos(phase), 70)
        imag = mp.nstr(4 * mp.sin(phase), 70)
    count = parse_printed_count_line('c s exact quadruple float ' + real + '+' + imag + 'i')
    verdict, _ = classify_observed_distance(
        count, 4, 1e-4, config.WMC_PHASE_TOLERANCE,
    )
    assert verdict == expected


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

def test_printed_count_classifier_is_stable_for_extremes():
    huge = parse_printed_count_line('c s exact quadruple float 1e300')
    from QuPRS.utils.precision_count import approximate_printed_log2
    assert math.isfinite(approximate_printed_log2(huge))
    zero = parse_printed_count_line('c s exact quadruple float 0')
    assert classify_printed_distance(zero, 4, 1e-8).status == 'not_equivalent'
    with pytest.raises(ValueError, match='Non-finite'):
        parse_printed_count_line('c s exact quadruple float inf')


# Regression: zero path variables may still encode an unsatisfiable
# trace (e.g., identity versus X). Never shortcut such a CNF to count 2^n.
@pytest.mark.parametrize("solver", ["ganak", "gpmc"])
@pytest.mark.parametrize("backend", ["python", "rust"])
@pytest.mark.parametrize("gate, expected", [
    ("id", "equivalent"),
    ("x", "not_equivalent"),
    ("z", "not_equivalent"),
])
def test_zero_path_variable_wmc_never_forces_equivalence(solver, backend, gate, expected):
    from qiskit.quantum_info import Operator

    identity = QuantumCircuit(1)
    target = QuantumCircuit(1)
    if gate != "id":
        getattr(target, gate)(0)
    oracle = Operator(identity).equiv(Operator(target))
    assert oracle == (expected == "equivalent")
    outcome = check_equivalence(
        identity, target,
        method="wmc_only", backend=backend, tool_name=solver, timeout=60,
    )
    if gate == "id" and solver == "ganak" and outcome.equivalent == "unknown":
        # At D=1e-8, the printed Ganak count may not resolve the
        # 1e-16 squared-magnitude margin even for a source-exact identity.
        # This is a numerical limitation, not a reason to shortcut WMC-only
        # or weaken the exact X/Z negative controls.
        assert outcome.wmc_solver_invoked is True
        assert outcome.wmc_printed_verdict == "unknown"
        assert any(
            reason in (outcome.wmc_precision_reason or "")
            for reason in ("resolution", "nonphysical")
        ), outcome.wmc_precision_reason
    else:
        assert outcome.equivalent == expected, (
            f"Expected {expected} by Qiskit Operator for {gate}, "
            f"got {outcome.equivalent} with {backend}/{solver}"
        )
    assert outcome.tool_name == solver
    assert outcome.tool_time is not None
