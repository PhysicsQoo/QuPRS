"""Pinned native Ganak controls for projected and cancellation-sensitive WMC.

These fixtures keep original rational/binary-exact input weights, disable
Arjun/Puura transformations and compare only the solver's printed complex
observation to an independent tiny exact-model oracle. Printed Mode6 output
is NOT a 38-digit numeric certificate. Debug-exported CNF is not reused.
"""

from fractions import Fraction
from pathlib import Path

import pytest

from QuPRS.utils import WMC
from QuPRS.utils.ganak_distribution import binary_diagnostics
from QuPRS.utils.precision_count import parse_printed_solver_output
from QuPRS.utils.solver_process import run as run_solver

from test_projected_complex_wmc_oracle import exact_projected_count


WEIGHTS = {
    1: (Fraction(0), Fraction(1)),
    -1: (Fraction(1), Fraction(0)),
    2: (Fraction(3, 2), Fraction(1, 4)),
    -2: (Fraction(-1, 2), Fraction(1, 4)),
}
CLAUSES = ((1, 3), (-3, 2))
WEIGHT_LINES = (
    "c p weight 1 0+1i 0",
    "c p weight -1 1+0i 0",
    "c p weight 2 1.5+0.25i 0",
    "c p weight -2 -0.5+0.25i 0",
)


def _native_ganak(path: Path):
    # Resolving the packaged binary checks the pinned architecture/version
    # and source identity. Never silently fall back to another WMC solver.
    with WMC("ganak") as executable:
        provenance = binary_diagnostics(executable)
        assert provenance["pinned"] and not provenance["override"], (
            "Precision control must use the pinned Ganak binary"
        )
        command = (
            str(executable),
            "--mode=6",
            "--mpfrprec=127",
            "--arjun=0",
            "--puura=0",
            str(path),
        )
        observed = run_solver(list(command), timeout=30)
    assert observed.returncode == 0, (
        "Pinned Ganak native execution failed", observed.returncode,
        observed.stdout, observed.stderr,
    )
    assert "s SATISFIABLE" in observed.stdout, (
        "Expected satisfiable weighted CNF", observed.stdout
    )
    parsed = parse_printed_solver_output(observed.stdout)
    return parsed.real, parsed.imag


def _write_projected_example(path: Path, projected: bool):
    lines = [
        "p cnf 3 2",
        "c t pwmc" if projected else "c t wmc",
    ]
    if projected:
        lines.append("c p show 1 2 0")
    lines.extend(WEIGHT_LINES)
    lines.extend(("1 3 0", "-3 2 0"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.mark.parametrize("projected", (True, False), ids=("pwmc", "wmc"))
def test_pinned_native_count_distinguishes_projection(projected, tmp_path):
    cnf = tmp_path / "source.cnf"
    _write_projected_example(cnf, projected)

    if projected:
        has_model, exact = exact_projected_count(
            3, CLAUSES, (1, 2), WEIGHTS
        )
        assert has_model and exact == (Fraction(1), Fraction(5, 4))
    else:
        # Without projection, the satisfying full models with distinct
        # hidden-variable values contribute separately.
        exact = (Fraction(3, 4), Fraction(11, 4))

    real, imag = _native_ganak(cnf)
    # Ganak Mode6 emits about nine significant decimal digits, irrespective
    # of the internal 127-bit arithmetic. This tolerance is an OUTPUT-format
    # fixture budget, never the QuPRS equivalence decision tolerance.
    assert abs(float(real - exact[0])) <= 1e-8
    assert abs(float(imag - exact[1])) <= 1e-8


def test_native_input_preserves_large_cancellation_before_printing(tmp_path):
    # If source weights were truncated to nine digits BEFORE counting,
    # 1000000001 - 1000000000 could spuriously become zero. Compare the
    # native original-CNF path, not the lossy optional debug CNF export.
    cnf = tmp_path / "source_cancellation.cnf"
    cnf.write_text(
        "p cnf 1 0\n"
        "c t wmc\n"
        "c p weight 1 1000000001+0i 0\n"
        "c p weight -1 -1000000000+0i 0\n",
        encoding="utf-8",
    )
    real, imag = _native_ganak(cnf)
    assert abs(float(real - 1)) < 1e-8
    assert abs(float(imag)) < 1e-8


def test_exact_complex_factor_is_separate_from_native_output():
    # The parser's internal source multiplier is applied by Ganak itself.
    # This independent reference's factor is deliberately NOT supplied as
    # a second multiplier to the native solve.
    has_model, count = exact_projected_count(
        3, CLAUSES, (1, 2), WEIGHTS,
        factor=(Fraction(2), Fraction(1, 3)),
    )
    assert has_model
    assert count == (Fraction(19, 12), Fraction(17, 6))


def test_native_precision_boundary_avoids_false_zero_count(tmp_path):
    # The Boolean CNF is trivially satisfiable. Its exact complex weighted
    # sum is (10**25 + 1) - 10**25 == 1.
    cnf = tmp_path / "source_precision_boundary.cnf"
    cnf.write_text(
        "p cnf 1 0\n"
        "c t wmc\n"
        "c p weight 1 10000000000000000000000001+0i 0\n"
        "c p weight -1 -10000000000000000000000000+0i 0\n",
        encoding="utf-8",
    )
    observations = {}
    with WMC("ganak") as executable:
        metadata = binary_diagnostics(executable)
        assert metadata["pinned"] and not metadata["override"]
        for bits in (53, 127, 256):
            run = run_solver([
                str(executable), "--mode=6", f"--mpfrprec={bits}",
                "--arjun=0", "--puura=0", str(cnf),
            ], timeout=30)
            assert run.returncode == 0, (bits, run.stdout, run.stderr)
            parsed = parse_printed_solver_output(run.stdout)
            observations[bits] = (parsed.real, parsed.imag, run.stdout)

    assert observations[127][:2] == (Fraction(1), Fraction(0))
    assert observations[256][:2] == (Fraction(1), Fraction(0))
    assert "s SATISFIABLE" in observations[127][2]
    assert "s SATISFIABLE" in observations[256][2]
    # Under binary53, source-weight rounding produces zero; the native
    # status label follows the numerical weighted count, not an independent
    # Boolean SAT check. This is a bounded negative numerical witness.
    assert observations[53][:2] == (Fraction(0), Fraction(0))
    assert "s UNSATISFIABLE" in observations[53][2]


def test_exact_complex_cancellation_does_not_certify_boolean_unsat(tmp_path):
    # Both assignments satisfy the empty CNF, even though their complex
    # weights cancel exactly. Ganak's status label is based on weighted
    # count == 0, so it is not an independent Boolean SAT certificate.
    cnf = tmp_path / "exact_zero.cnf"
    cnf.write_text(
        "p cnf 1 0\n"
        "c t wmc\n"
        "c p weight 1 1+0i 0\n"
        "c p weight -1 -1+0i 0\n",
        encoding="utf-8",
    )
    with WMC("ganak") as executable:
        metadata = binary_diagnostics(executable)
        assert metadata["pinned"] and not metadata["override"]
        run = run_solver([
            str(executable), "--mode=6", "--mpfrprec=127",
            "--arjun=0", "--puura=0", str(cnf),
        ], timeout=30)
    assert run.returncode == 0, (run.stdout, run.stderr)
    count = parse_printed_solver_output(run.stdout)
    assert (count.real, count.imag) == (Fraction(0), Fraction(0))
    assert "s UNSATISFIABLE" in run.stdout
    # This is a Boolean SAT fact independent of weighted cancellation:
    # both literal assignments satisfy a conjunction of zero clauses.
    models = [bit for bit in (False, True)]
    assert len(models) == 2


@pytest.mark.parametrize("arjun", (0, 1), ids=("no-arjun", "with-arjun"))
def test_forced_complex_weight_survives_preprocessing_once(arjun, tmp_path):
    # x1 must be true, giving weight (2+i); x2 is unconstrained and
    # contributes (3+0i)+(1+0i). The exact weighted count is 8+4i.
    # Test both preprocessing paths, never multiplying the returned count
    # by a separately reconstructed multiplier a second time.
    cnf = tmp_path / "forced_weight.cnf"
    cnf.write_text(
        "p cnf 2 1\n"
        "c t wmc\n"
        "c p weight 1 2+1i 0\n"
        "c p weight -1 3-1i 0\n"
        "c p weight 2 3+0i 0\n"
        "c p weight -2 1+0i 0\n"
        "1 0\n",
        encoding="utf-8",
    )
    with WMC("ganak") as executable:
        metadata = binary_diagnostics(executable)
        assert metadata["pinned"] and not metadata["override"]
        run = run_solver([
            str(executable), "--mode=6", "--mpfrprec=127",
            f"--arjun={arjun}", "--puura=0", str(cnf),
        ], timeout=30)
    assert run.returncode == 0, (arjun, run.stdout, run.stderr)
    result = parse_printed_solver_output(run.stdout)
    assert (result.real, result.imag) == (Fraction(8), Fraction(4))
    assert "s SATISFIABLE" in run.stdout
