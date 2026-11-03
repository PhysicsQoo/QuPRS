#!/usr/bin/env python3
"""Source-pinned GPMC printed-point column for the historical Qiskit/Ganak matrix."""
from __future__ import annotations
import csv
import json
import re
from decimal import Decimal, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/development/tacas26-qiskit142-frozen-audit"
RUN = 41481701901
SHA = "ff4d3032a83c0ae18ba3a7d195cb1b1a8804492f"


def main():
    qiskit = json.loads((DATA / "qiskit142-20.json").read_text(encoding="utf8"))
    with (DATA / "gpmc30-20-printpoint.csv").open(newline="", encoding="utf8") as f:
        gpmc_rows = list(csv.DictReader(f))
    observations = qiskit["rows"]
    lookup = {x["id"]: x for x in gpmc_rows}
    if (len(observations), len(gpmc_rows), len(lookup)) != (20, 20, 20):
        raise ValueError("Expected 20 original comparisons with no duplicates")
    if {x["case_id"] for x in observations} != set(lookup):
        raise ValueError("Qiskit, Ganak and GPMC case identities differ")
    if qiskit["replay_qiskit"] != "1.4.2":
        raise ValueError("Wrong historical Qiskit version")
    for x in gpmc_rows:
        root = Decimal(x["root_argument"])
        value = x["gpmc30_distance"]
        if root < 0:
            if value != "NONPHYSICAL_PRINTED_MAGNITUDE":
                raise ValueError("Negative normalized root must not be clipped")
        else:
            if value == "NONPHYSICAL_PRINTED_MAGNITUDE":
                raise ValueError("Nonnegative normalized root incorrectly classified")
            with localcontext() as ctx:
                ctx.prec = 75
                ref = root.sqrt()
                if abs(Decimal(value)-ref) > max(Decimal("1e-80"), ref*Decimal("1e-12")):
                    raise ValueError("Inconsistent saved GPMC printed-point result")
        if int(x["normalization_twice_log2"]) < 0:
            raise ValueError("Invalid normalization exponent")
    representatives = {}
    for rec in observations:
        name = rec["case_id"].split(":")[1]
        representatives.setdefault(name, rec)
    table = [
        "| Circuit | Qubits | Numerical check | Qiskit floating distance or sample-state difference | GPMC30 printed-point D | Ganak6 printed-point D |",
        "|---|---:|---|---:|---:|---:|",
    ]
    for name, rec in sorted(representatives.items()):
        ob = rec["independent_qiskit_audit"]
        q = ob.get("projective_distance_float") if ob["status"] == "FULL_FLOAT_OPERATOR" else ob.get("max_sample_state_distance_float")
        g = lookup[rec["case_id"]]["gpmc30_distance"]
        dg = "nonphysical†" if g == "NONPHYSICAL_PRINTED_MAGNITUDE" else format(float(g), ".8g")
        dq = format(q, ".8g") if q is not None else "not measured"
        table.append("| " + name + " | " + str(ob.get("qubits", "?")) + " | " +
                     ob["status"] + " | " + dq + " | " + dg + " | " +
                     format(rec["ganak_point_distance"], ".8g") + " |")
    path = DATA / "README.md"
    original = path.read_text(encoding="utf8")
    pattern = r"\| Circuit \|[^\n]*\n\|---[^\n]*\n(?:\|[^\n]*\n)+"
    revised, count = re.subn(pattern, lambda _: "\n".join(table) + "\n", original, count=1)
    if count != 1:
        raise ValueError("Existing representative matrix not found")
    note = (
        "\n## GPMC30 printed-point distance provenance\n\n"
        "Original Python/GPMC MPFR30 run: "
        "https://github.com/PhysicsQoo/QuPRS/actions/runs/" + str(RUN) +
        " (source SHA " + SHA + "). "
        "Distances are inferred from the exact fractional interpretation "
        "of solver-printed complex components with normalization 2**k; "
        "the trace-based printed-point formula is "
        "sqrt(1-(Re(WMC)**2+Im(WMC)**2)/2**k). "
        "The accompanying 20-row CSV preserves each case's root argument "
        "and exponent k. Solver arithmetic error is NOT_CERTIFIED.\n\n"
        "† The printed-root argument is slightly negative for five cases "
        "due to magnitude exceeding physical normalization by approximately "
        "1e-30 to 1e-61; no real-valued D follows and no clipping to zero "
        "is performed. QFT20, QFT22, QPEexact20 have nonzero GPMC "
        "printed-point D around 7.03e-6, 1.15e-5 and 4.24e-6, all below "
        "the 2e-5 paper-reproduction threshold. "
        "Qiskit values for >8 qubits reflect sampled state differences "
        "instead of a global trace-based operator distance. "
        "Float64 operator-distance calculations near zero can also show "
        "an artificial 1e-8 floor from cancellation.\n"
    )
    revised = revised.split("\n## GPMC30 printed-point distance provenance")[0].rstrip() + "\n" + note
    path.write_text(revised, encoding="utf8")
    print("GPMC_MATRIX_MATCHED", len(gpmc_rows), len(representatives), RUN, SHA)


if __name__ == "__main__":
    main()
