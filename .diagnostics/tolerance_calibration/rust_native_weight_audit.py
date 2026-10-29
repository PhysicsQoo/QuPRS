"""Independent high-precision audit of actual Rust serialized WMC weights.

Reads the native Rust unit-test transcript, not a synthetic reimplementation of
the Rust weight generator. Reports source exactness versus f64 CNF collision.
The resulting errors are observations, not universal Solver error bounds.
"""
import json
from decimal import Decimal
from fractions import Fraction
from itertools import permutations
from pathlib import Path

from mpmath import mp

OUT = Path("focused-tolerance-evidence")
LOG = OUT / "native-rust-weight.log"
DEST = OUT / "rust-weight-versus-oracle.json"
REQUIRED = {"sub_f64_defect", "resolved_control", "literal_alias_a", "literal_alias_b"}
rows = {}
for line in LOG.read_text().splitlines():
    if line.startswith("RUST_PHASE\t"):
        parts = line.split("\t", 7)
        assert len(parts) == 8, line
        _, label, source, cn, cd, rn, rd, mono = parts
        obj = rows.setdefault(label, {"literal": source, "phases": [], "weights": {}})
        assert obj["literal"] == source
        obj["phases"].append({
            "constant": [cn, cd], "radians": [rn, rd], "monomial": mono
        })
    if line.startswith("RUST_WEIGHT\t"):
        parts = line.split("\t", 3)
        assert len(parts) == 4, line
        _, label, solver, content = parts
        tokens = content.split()
        assert tokens[:3] == ["c", "p", "weight"], tokens
        var = int(tokens[3])
        if var <= 0:
            continue
        if solver == "gpmc":
            real, imag = tokens[4:6]
        else:
            real, sign, imag = tokens[4:7]
            assert imag.endswith("i")
            imag = imag[:-1]
            assert sign in ("+", "-")
            if sign == "-":
                imag = "-" + imag
        obj = rows.setdefault(label, {"literal": None, "phases": [], "weights": {}})
        obj["weights"].setdefault(solver, []).append({
            "var": var, "real": real, "imag": imag
        })

assert set(rows) == REQUIRED, (set(rows), REQUIRED)
with mp.workdps(110):
    for label, obj in rows.items():
        source = obj["literal"]
        assert source is not None
        oracle = []
        for coeff in obj["phases"]:
            c = Fraction(*map(int, coeff["constant"]))
            r = Fraction(*map(int, coeff["radians"]))
            angle = 2 * mp.pi * mp.mpf(c.numerator) / c.denominator
            angle += 2 * mp.mpf(r.numerator) / r.denominator
            oracle.append(mp.mpc(mp.cos(angle), mp.sin(angle)))
        assert oracle, label
        for solver in ("gpmc", "ganak"):
            weights = obj["weights"][solver]
            assert len(weights) == len(oracle), (label, solver, weights, oracle)
            actual = [
                mp.mpc(mp.mpf(w["real"]), mp.mpf(w["imag"])) for w in weights
            ]
            assignments = [
                (mp.fsum(abs(actual[j] - oracle[i]) for i, j in enumerate(order)), order)
                for order in permutations(range(len(actual)))
            ]
            best, order = min(assignments, key=lambda pair: pair[0])
            for i, j in enumerate(order):
                weights[j]["matched_phase"] = obj["phases"][i]
                weights[j]["oracle_abs_error"] = mp.nstr(
                    abs(actual[j] - oracle[i]), 45
                )
            obj["weights"][solver + "_total_oracle_abs_error"] = mp.nstr(best, 45)
        obj["source_f64_hex"] = float(Decimal(source)).hex()
    a, b = rows["literal_alias_a"], rows["literal_alias_b"]
    assert a["source_f64_hex"] == b["source_f64_hex"], "Expected source-f64 alias absent"
    assert a["phases"] != b["phases"], "Rust exact source phases unexpectedly identical"
    def count_bytes(obj, solver):
        return sorted((w["real"], w["imag"]) for w in obj["weights"][solver])
    for solver in ("gpmc", "ganak"):
        assert count_bytes(a, solver) == count_bytes(b, solver), (
            "Sub-f64 literal difference unexpectedly survived current f64 serialization",
            solver,
        )
    output = {
        "input_labels": sorted(rows),
        "actual_weight_provenance": "Rust WmcManager encode_trace and real CNF serialization",
        "literal_alias_exact_phase_distinct": True,
        "literal_alias_f64_cnf_collision": True,
        "certified_solver_error_bound": False,
        "results": rows,
    }
DEST.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
print("RUST_REAL_CNF_ORACLE_AUDIT_PASS", json.dumps({
    label: {
        s: rows[label]["weights"][s + "_total_oracle_abs_error"]
        for s in ("gpmc", "ganak")
    } for label in sorted(rows)
}, sort_keys=True))
