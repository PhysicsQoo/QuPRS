"""Research-only: decimal projective-distance evidence from printed WMC counts.

The output interval covers ONLY rounding of the solver's scientific-notation
result, not MPFR arithmetic, source-angle/weight conversion, RR error, or WMC
algorithm error. Verdict labels intentionally include '_printed_only'.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
import json
from pathlib import Path

EPSILONS = ("1e-8", "2e-8", "2e-4")


def half_print_unit(value: str) -> Decimal:
    # MPFR scientific printf represents a true zero as 0.000...e+00.
    # A nonzero MPFR value, however tiny, has its own scientific exponent.
    mantissa, exponent = value.lower().split("e")
    if Decimal(mantissa) == 0:
        return Decimal(0)
    fractional = len(mantissa.split(".", 1)[1]) if "." in mantissa else 0
    return Decimal(5).scaleb(int(exponent) - fractional - 1)


def interval_status(real: str, imag: str, epsilon: str, log2_norm: int = 0):
    with localcontext() as ctx:
        ctx.prec = 150
        r, i = abs(Decimal(real)), abs(Decimal(imag))
        ur, ui = half_print_unit(real), half_print_unit(imag)
        lower_r, lower_i = max(r - ur, Decimal(0)), max(i - ui, Decimal(0))
        upper_r, upper_i = r + ur, i + ui
        norm = Decimal(2) ** log2_norm
        magnitude_low = (lower_r * lower_r + lower_i * lower_i).sqrt() / norm
        magnitude_high = (upper_r * upper_r + upper_i * upper_i).sqrt() / norm
        eps = Decimal(epsilon)
        threshold_magnitude = (Decimal(1) - eps * eps).sqrt()
        if magnitude_low > Decimal(1):
            status = "unknown_overshoot"
        elif magnitude_high < threshold_magnitude:
            status = "not_equivalent_printed_only"
        elif magnitude_low >= threshold_magnitude:
            status = "equivalent_printed_only"
        else:
            status = "unknown_print_resolution"
        return status


def read_fixture(path: Path):
    rows = []
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        case, bits, variant, real, imag = line.split("\t")
        assert variant in {"baseline", "candidate"}
        assert int(bits) in {128, 256}
        rows.append((case, bits, variant, real, imag))
    assert len(rows) == 24
    return rows


def generate(path: Path, folder: Path):
    rows = read_fixture(path)
    records = []
    # Add scaled counterparts with a 2^2 normalization: prove no early
    # binary64 conversion in large-magnitude normalization.
    for case, bits, variant, re, im in rows:
        for log2_norm in (0, 2):
            with localcontext() as ctx:
                ctx.prec = 150
                if log2_norm:
                    sr = format(Decimal(re) * 4, "e")
                    si = format(Decimal(im) * 4, "e")
                else:
                    sr, si = re, im
            for eps in EPSILONS:
                ident = f"{case}_{bits}_{variant}_n{log2_norm}_e{eps}"
                status = interval_status(sr, si, eps, log2_norm)
                records.append((ident, sr, si, eps, log2_norm, status))
    folder.mkdir(exist_ok=True, parents=True)
    (folder / "transport-input.tsv").write_text(
        "".join("\t".join(map(str, x[:5])) + "\n" for x in records)
    )
    (folder / "transport-python.tsv").write_text(
        "".join(x[0] + "\t" + x[5] + "\n" for x in records)
    )
    # Assert meaningful RED/GREEN regression, not just Python/Rust agreement.
    def verdict(case, bits, variant, norm, eps):
        matches = [x for x in records if x[0] == f"{case}_{bits}_{variant}_n{norm}_e{eps}"]
        assert len(matches) == 1
        return matches[0][5]

    for bits in (128, 256):
        for norm in (0, 2):
            assert verdict("sub_f64_magnitude", bits, "baseline", norm, "1e-8") == "unknown_print_resolution"
            assert verdict("sub_f64_magnitude", bits, "candidate", norm, "1e-8") == "not_equivalent_printed_only"
            assert verdict("sub_f64_magnitude", bits, "candidate", norm, "2e-8") == "equivalent_printed_only"
            assert verdict("magnitude_overshoot", bits, "candidate", norm, "1e-8") == "unknown_overshoot"

    report = {
        "records": len(records),
        "source": "CI 40720357077 artifact 12831062644 (immutable fixture subset)",
        "epsilons": EPSILONS,
        "normalization_log2": [0, 2],
        "status_counts": {
            name: sum(x[5] == name for x in records)
            for name in sorted({x[5] for x in records})
        },
        "scope": "printed-output-rounding-only; not a certified solver error bound",
    }
    (folder / "transport-summary.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


def verify(folder: Path):
    expected = (folder / "transport-python.tsv").read_text().splitlines()
    actual = (folder / "transport-rust.tsv").read_text().splitlines()
    assert expected == actual, "Rust high-precision MPFR distance classifications differ from Python Decimal"
    assert len(expected) == 24 * 2 * len(EPSILONS)
    print("PYTHON_RUST_HIGH_PRECISION_PRINT_TRANSPORT_PARITY_PASS:", len(expected))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--fixture", default=".diagnostics/tolerance_calibration/high_precision_count_fixture.tsv")
    p.add_argument("--out", default="focused-tolerance-evidence")
    p.add_argument("--verify", action="store_true")
    args = p.parse_args()
    if args.verify:
        verify(Path(args.out))
    else:
        generate(Path(args.fixture), Path(args.out))
