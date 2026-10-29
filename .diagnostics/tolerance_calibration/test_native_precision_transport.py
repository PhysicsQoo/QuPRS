"""Native WMC weighted-count precision characterization, isolated on the existing research branch.

Report-only high-precision Ganak probes may yield missing result lines; log them instead
of treating an external solver exit code 0 as scientific equivalence evidence.
The corresponding 16-case public API parity has already been captured at the
v0.14.0 dev exact-tree and is not rerun on this older experimental branch.
"""

def test_focused_native_precision_transport_evidence():
    """Bounded native A/B evidence on the existing WMC CI runner.

    Experimental source is unchanged. Raw decimal Solver output is preserved
    before Python or Rust converts it to binary64. This test does not claim a
    numerical error certificate.
    """
    import hashlib
    import json
    import re
    import subprocess
    import time
    from contextlib import ExitStack
    from decimal import Decimal, localcontext
    from pathlib import Path

    from QuPRS.utils.solver_process import run as run_solver
    from QuPRS.utils import WMC

    base = "b122962eccb9b686cb614b6e84f539e8b5cd9a14"
    gpmc_rev = "a1bda3489e959d3695b6798d327c5a1fc1bed305"
    source_diff = subprocess.check_output([
        "git", "diff", "--name-only", base, "HEAD", "--",
        "src/QuPRS", "rust/pathsum", "rust/python_ffi", "GPMC",
    ], text=True).strip()
    # This experiment may carry only the two transport-parser fixes.
    # All numerical solver implementations and other production sources
    # remain pinned to the original research baseline.
    parser_paths = {
        "src/QuPRS/utils/wmc_solvers.py",
        "src/QuPRS/utils/precision_count.py",
        "src/QuPRS/utils/solver_adapter.py",
        "src/QuPRS/interface/ps2wmc.py",
        "rust/pathsum/src/wmc.rs",
        "rust/pathsum/src/lib.rs",
        "rust/pathsum/src/precision_count.rs",
        "rust/pathsum/src/solver_adapter.rs",
    }
    changed = set(source_diff.splitlines()) if source_diff else set()
    assert changed <= parser_paths, (
        "Unexpected production source changes relative to precision baseline: "
        + repr(sorted(changed - parser_paths))
    )
    assert subprocess.check_output(
        ["git", "rev-parse", "HEAD:GPMC"], text=True
    ).strip() == gpmc_rev

    cases = (
        ("sub_f64_magnitude", "0.99999999999999994746875", "0", "1", "0", True),
        ("magnitude_overshoot", "1.00000000000000005253125", "0", "1", "0", True),
        ("tiny_complex_phase", "1", "0.0000000000000000000001", "1", "0", True),
        ("catastrophic_cancellation", "10000000000000001", "0", "-10000000000000000", "0", False),
        ("signed_complex_cancellation", "10000000000000001", "0.00000000000000000001", "-10000000000000000", "0", False),
        ("negative_tiny_imaginary", "1", "-0.00000000000000000000000001", "1", "0", True),
    )
    modes = {
        "gpmc": (
            ("default", ("-mode=1",)),
            ("digits128", ("-mode=1", "-prec=128")),
            ("digits256", ("-mode=1", "-prec=256")),
        ),
        "ganak": (
            ("default_prob", ("--mode=6",)),
            ("default_prob0", ("--mode=6", "--prob", "0")),
            ("bits128_prob", ("--mode=6", "--mpfrprec", "128")),
            ("bits128_prob0", ("--mode=6", "--mpfrprec", "128", "--prob", "0")),
            ("bits256_prob", ("--mode=6", "--mpfrprec", "256")),
            ("bits256_prob0", ("--mode=6", "--mpfrprec", "256", "--prob", "0")),
        ),
    }
    prefixes = (
        "c s exact double prec-sci", "c s exact arb cpx",
        "c s exact quadruple float", "c s exact octuple float",
        "c s exact arb frac",
    )

    def sign_im(part):
        return "- " + part[1:] + "i" if part.startswith("-") else "+ " + part + "i"

    def make_cnf(solver, case):
        _, pos_re, pos_im, neg_re, neg_im, forced = case
        if solver == "gpmc":
            weights = (
                "c p weight 1 " + pos_re + " " + pos_im + " 0",
                "c p weight -1 " + neg_re + " " + neg_im + " 0",
            )
        else:
            weights = (
                "c p weight 1 " + pos_re + " " + sign_im(pos_im) + " 0",
                "c p weight -1 " + neg_re + " " + sign_im(neg_im) + " 0",
            )
        return "\n".join((
            "p cnf 1 " + str(int(forced)), "c t wmc",
            *weights, *(("1 0",) if forced else ()), "",
        ))

    def exact(case):
        _, pr, pi, nr, ni, forced = case
        with localcontext() as ctx:
            ctx.prec = 110
            return (
                Decimal(pr) if forced else Decimal(pr) + Decimal(nr),
                Decimal(pi) if forced else Decimal(pi) + Decimal(ni),
            )

    def as_decimal(part):
        if "/" in part:
            n, d = part.split("/")
            with localcontext() as ctx:
                ctx.prec = 110
                return Decimal(n) / Decimal(d)
        return Decimal(part)

    def read_raw(stdout):
        values = []
        for line in stdout.splitlines():
            for prefix in prefixes:
                if line.startswith(prefix) and (
                    len(line) == len(prefix) or line[len(prefix)].isspace()
                ):
                    raw = re.sub(r"\s+", "", line[len(prefix):]).replace("+-", "-")
                    try:
                        if not raw.endswith("i"):
                            parts = (raw, "0")
                        else:
                            raw_no_i = raw[:-1]
                            split = [
                                idx for idx in range(1, len(raw_no_i))
                                if raw_no_i[idx] in "+-" and raw_no_i[idx - 1] not in "eE"
                            ]
                            parts = (
                                (raw_no_i[:split[-1]], raw_no_i[split[-1]:])
                                if split else ("0", raw_no_i)
                            )
                        decimal_pair = tuple(as_decimal(p) for p in parts)
                        values.append((line[len(prefix):].strip(), decimal_pair))
                    except Exception as exc:
                        return {"error": "invalid_solver_count", "detail": repr(exc)}
        if not values:
            return {"error": "missing_solver_count"}
        if any(v[1] != values[0][1] for v in values[1:]):
            return {"error": "conflicting_solver_counts"}
        return {
            "raw": values[0][0],
            "real_decimal": str(values[0][1][0]),
            "imag_decimal": str(values[0][1][1]),
            "count_lines": len(values),
        }

    evidence = {
        "experiment": "source-pinned-native-precision-transport",
        "source_base": base,
        "gpmc_submodule": gpmc_rev,
        "source_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "native": [],
        "public_api": [],
    }
    folder = Path("focused-tolerance-evidence")
    folder.mkdir(exist_ok=True)
    import tempfile

    with ExitStack() as stack:
        binary = {
            solver: Path(stack.enter_context(WMC(solver)))
            for solver in ("gpmc", "ganak")
        }
        fingerprints = {
            solver: hashlib.sha256(path.read_bytes()).hexdigest()
            for solver, path in binary.items()
        }
        with tempfile.TemporaryDirectory(prefix="quprs-precision-") as tmp:
            for solver in ("gpmc", "ganak"):
                for case in cases:
                    payload = make_cnf(solver, case)
                    cnf_path = Path(tmp) / (solver + "-" + case[0] + ".cnf")
                    cnf_path.write_text(payload)
                    ref = exact(case)
                    for variant, flags in modes[solver]:
                        started = time.monotonic()
                        row = {
                            "solver": solver, "case": case[0],
                            "variant": variant, "flags": list(flags),
                            "binary_sha256": fingerprints[solver],
                            "cnf_sha256": hashlib.sha256(payload.encode()).hexdigest(),
                            "oracle": [str(ref[0]), str(ref[1])],
                        }
                        try:
                            result = run_solver(
                                [str(binary[solver]), *flags, str(cnf_path)],
                                timeout=10,
                            )
                            row.update({
                                "returncode": result.returncode,
                                "stdout": result.stdout[-65536:],
                                "stdout_length": len(result.stdout),
                                "stderr": result.stderr[:4000],
                            })
                            parsed = read_raw(result.stdout)
                            row["parsed_raw"] = parsed
                            if "real_decimal" in parsed:
                                with localcontext() as ctx:
                                    ctx.prec = 110
                                    row["absolute_error"] = [
                                        str(abs(as_decimal(parsed["real_decimal"]) - ref[0])),
                                        str(abs(as_decimal(parsed["imag_decimal"]) - ref[1])),
                                    ]
                        except Exception as exc:
                            row["error"] = repr(exc)
                        row["elapsed_sec"] = round(time.monotonic() - started, 6)
                        evidence["native"].append(row)


    evidence_file = folder / "native-precision-focused.json"
    evidence_file.write_text(json.dumps(evidence, indent=2, default=str))
    print(
        "Focused precision native measurements:", len(evidence["native"]),
        "public API:", len(evidence["public_api"]),
        "artifact:", evidence_file,
    )
    assert len(evidence["native"]) == 54
    assert len(evidence["public_api"]) == 0
    baseline_failures = [
        x for x in evidence["native"]
        if x["variant"] in ("default", "default_prob")
        and (x.get("returncode") != 0 or "real_decimal" not in x.get("parsed_raw", {}))
    ]
    assert not baseline_failures, "Default native precision cases failed; inspect artifact"
    high_precision_format_failures = [
        x for x in evidence["native"]
        if x["solver"] == "ganak" and x["variant"].startswith("bits256")
        and (x.get("returncode") != 0 or "real_decimal" not in x.get("parsed_raw", {}))
    ]
    assert not high_precision_format_failures, (
        "Ganak 256-bit raw count output not recognized; inspect artifact"
    )
