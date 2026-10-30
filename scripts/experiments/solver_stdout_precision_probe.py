"""One real solver call per case; capture original stdout in the same call.

Experimental diagnostic only. Printed-digit intervals are conditional on
correct rounding, NOT certified solver-arithmetic or circuit error bounds.
"""
import argparse
from decimal import Decimal
from fractions import Fraction
import json
from pathlib import Path

from mpmath import mp
from QuPRS import check_equivalence
from QuPRS.utils import solver_process
from QuPRS.utils.precision_count import parse_printed_solver_output, classify_observed_distance

HEADER = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
CONTROLS = (
    ("identity_h2", "h q[0];\nh q[0];", None),
    ("rz_0.0001", "rz(0.0001) q[0];", "0.0001"),
    ("rz_0.0002", "rz(0.0002) q[0];", "0.0002"),
    ("rz_2.5e-8", "rz(0.000000025) q[0];", "0.000000025"),
)


def inspect_one(solver, name, rhs, angle):
    original = solver_process.run
    captured = []
    def spy(command, timeout):
        output = original(command, timeout)
        # Ganak has a separate --version/preflight child process.
        # Count only the actual CNF-consuming weighted-count invocation.
        if str(command[-1]).endswith(".cnf"):
            captured.append({
                "argv_without_binary": command[1:-1],
                "stdout": output.stdout,
                "returncode": output.returncode,
            })
        return output
    solver_process.run = spy
    try:
        result = check_equivalence(
            HEADER, HEADER + rhs + "\n", backend="python",
            method="wmc_only", strategy="Naive", tool_name=solver,
            timeout=60, approximate_distance_tolerance=1e-8,
        )
    finally:
        solver_process.run = original
    assert len(captured) == 1, (solver, name, len(captured))
    assert captured[0]["returncode"] == 0
    assert result.wmc_solver_invoked is True
    count = parse_printed_solver_output(captured[0]["stdout"])
    twice = int(round(2 * result.expect))
    status, evidence = classify_observed_distance(count, twice, 1e-8, 1e-8)
    assert result.equivalent == status, (solver, name, result.equivalent, status)
    norm_sq = Fraction(2) ** twice
    lo_re=max(Fraction(0),abs(count.real)-count.real_print_half_unit)
    lo_im=max(Fraction(0),abs(count.imag)-count.imag_print_half_unit)
    hi_re=abs(count.real)+count.real_print_half_unit
    hi_im=abs(count.imag)+count.imag_print_half_unit
    sq_min=(lo_re*lo_re+lo_im*lo_im)/norm_sq
    sq_max=(hi_re*hi_re+hi_im*hi_im)/norm_sq
    # The magnitude loss interval overlaps the requested epsilon_D^2
    # when the output digits cannot resolve the numerical classification.
    deficit_lower = 1-sq_max
    deficit_upper = 1-sq_min
    if angle is None:
        oracle = "0"
    else:
        with mp.workdps(100):
            oracle = mp.nstr(abs(mp.sin(mp.mpf(angle)/2)),35)
    if angle is not None and float(oracle) > 1e-8:
        assert status in ("not_equivalent", "unknown")
    reason=result.wmc_precision_reason
    print(
        f"STDOUT_PRECISION solver={solver} case={name} status={status} "
        f"reason={reason} format={count.format_name} "
        f"real_halfunit={float(count.real_print_half_unit):.6g} "
        f"deficit_interval=[{float(deficit_lower):.6g},{float(deficit_upper):.6g}] "
        f"oracle_D={oracle}",flush=True
    )
    return {
        "case":name,"solver":solver,
        "reported_oracle_distance":oracle,
        "solver_args":captured[0]["argv_without_binary"],
        "result_status":status,
        "reason":reason,
        "printed_evidence_reason":evidence.reason,
        "raw_count_lines":[line for line in captured[0]["stdout"].splitlines()
                           if line.startswith("c s exact ") or line.startswith("c o precision ")],
        "format_name":count.format_name,
        "real":str(count.real),"imag":str(count.imag),
        "real_print_half_unit":str(count.real_print_half_unit),
        "imag_print_half_unit":str(count.imag_print_half_unit),
        "relative_squared_magnitude_deficit_lower":str(deficit_lower),
        "relative_squared_magnitude_deficit_upper":str(deficit_upper),
        "distance_sq_threshold":"1e-16",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--json",required=True,type=Path)
    args=p.parse_args()
    rows=[inspect_one(solver,*control)
          for solver in ("gpmc","ganak") for control in CONTROLS]
    assert len(rows)==8
    args.json.write_text(json.dumps({
        "scope":"original selected solver stdout, exactly one invocation per verification",
        "caveat":"only printed formatting interval; solver arithmetic uncertified",
        "rows":rows
    },indent=2)+"\n")
    print("STDOUT_PRECISION_SUMMARY total=8 passed=8",flush=True)

if __name__=="__main__":
    main()
