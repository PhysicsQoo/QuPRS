"""Same-host original/candidate Ganak source-build output precision A/B.

Research only. Never substitutes for the packaged or provenance-validated
release binary and never interprets f64 parser output as a numerical bound.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time

CASES = (
    ("sub_f64_magnitude", "0.99999999999999994746875", "0", "1", "0", True),
    ("magnitude_overshoot", "1.00000000000000005253125", "0", "1", "0", True),
    ("tiny_complex_phase", "1", "0.0000000000000000000001", "1", "0", True),
    ("catastrophic_cancellation", "10000000000000001", "0", "-10000000000000000", "0", False),
    ("signed_complex_cancellation", "10000000000000001", "0.00000000000000000001", "-10000000000000000", "0", False),
    ("negative_tiny_imaginary", "1", "-0.00000000000000000000000001", "1", "0", True),
)
COUNT_RE = re.compile(
    r"^c s exact (half|single|double|quadruple|octuple) float\s+"
    r"([+-]?(?:[0-9.]+)[eE][+-]?\d+)\s*([+-])\s*"
    r"([+-]?[0-9.]+[eE][+-]?\d+)i\s*$"
)


def cnf(case):
    _, pr, pi, nr, ni, forced = case
    def sign(z):
        return "- " + z[1:] + "i" if z.startswith("-") else "+ " + z + "i"
    return "\n".join((
        "p cnf 1 " + str(int(forced)),
        "c t wmc",
        "c p weight 1 " + pr + " " + sign(pi) + " 0",
        "c p weight -1 " + nr + " " + sign(ni) + " 0",
        *(("1 0",) if forced else ()), "",
    ))


def oracle(case):
    _, pr, pi, nr, ni, forced = case
    with localcontext() as ctx:
        ctx.prec = 120
        return (
            Decimal(pr) if forced else Decimal(pr) + Decimal(nr),
            Decimal(pi) if forced else Decimal(pi) + Decimal(ni),
        )


def count(stdout):
    found = []
    for line in stdout.splitlines():
        match = COUNT_RE.fullmatch(line.strip())
        if match:
            typ, real, sign, imag = match.groups()
            im = Decimal(imag)
            found.append((typ, Decimal(real), -im if sign == "-" else im, line))
    if len(found) != 1:
        raise ValueError("Expected one exact floating complex count; found " + str(len(found)))
    return found[0]


def run(executable, precision, probabilistic, cnf_path, tmp):
    flags = ["--mode=6", "--mpfrprec", str(precision)]
    if not probabilistic:
        flags.extend(["--prob", "0"])
    stats = tmp / "stats.txt"
    cmd = [
        "/usr/bin/time", "-f", "wall_seconds=%e\npeak_rss_kib=%M",
        "-o", str(stats), executable, *flags, str(cnf_path),
    ]
    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=12,
            start_new_session=True, check=False,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Native Solver timed out before producing a result")
    if result.returncode != 0:
        raise RuntimeError(
            "Ganak exit=" + str(result.returncode) +
            " stderr=" + result.stderr[-1200:]
        )
    typ, re_value, im_value, line = count(result.stdout)
    metrics = dict(item.split("=", 1) for item in stats.read_text().splitlines())
    return {
        "count_type": typ,
        "parsed_real": str(re_value),
        "parsed_imag": str(im_value),
        "count_line": line,
        "stdout": result.stdout[-65536:],
        "stderr": result.stderr[-8192:],
        "elapsed_measured_sec": time.monotonic() - start,
        "walltime_sec": float(metrics["wall_seconds"]),
        "peak_rss_kib": int(metrics["peak_rss_kib"]),
        "flags": flags,
        "decimal": (re_value, im_value),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    exe = {
        "baseline": str(Path(args.baseline).resolve()),
        "candidate": str(Path(args.candidate).resolve()),
    }
    output = {
        "experiment": "ganak-same-host-printer-only-source-ab",
        "source_upstream": "b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281",
        "binary_sha256": {
            name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
            for name, path in exe.items()
        },
        "observations": [],
    }
    failures = []
    gains = []
    with tempfile.TemporaryDirectory(prefix="ganak-printer-ab-") as td:
        tmp = Path(td)
        for case in CASES:
            fixture = cnf(case)
            path = tmp / (case[0] + ".cnf")
            path.write_text(fixture)
            expected = oracle(case)
            for bits in (128, 256):
                for probabilistic in (False, True):
                    pair = {}
                    for name, binary in exe.items():
                        try:
                            row = run(binary, bits, probabilistic, path, tmp)
                            got = row.pop("decimal")
                            row["absolute_error"] = [
                                str(abs(got[0] - expected[0])),
                                str(abs(got[1] - expected[1])),
                            ]
                            pair[name] = row
                        except Exception as exc:
                            pair[name] = {"error": repr(exc)}
                    observation = {
                        "case": case[0],
                        "bits": bits,
                        "probabilistic_cache": probabilistic,
                        "cnf_sha256": hashlib.sha256(fixture.encode()).hexdigest(),
                        "oracle": [str(v) for v in expected],
                        "runs": pair,
                    }
                    output["observations"].append(observation)
                    if any("error" in v for v in pair.values()):
                        failures.append([case[0], bits, probabilistic, pair])
                        continue
                    base_err = Decimal(pair["baseline"]["absolute_error"][0])
                    good_err = Decimal(pair["candidate"]["absolute_error"][0])
                    if good_err > base_err:
                        failures.append([case[0], bits, "candidate_worse", str(base_err), str(good_err)])
                    if case[0] in ("sub_f64_magnitude", "magnitude_overshoot"):
                        limit = Decimal("1e-30") if bits == 128 else Decimal("1e-50")
                        if base_err > 0 and good_err < limit:
                            gains.append([case[0], bits, probabilistic])
                        else:
                            failures.append([case[0], bits, "insufficient_precision_gain", str(base_err), str(good_err)])
    output["summary"] = {
        "observations": len(output["observations"]),
        "native_invocations": len(output["observations"]) * 2,
        "improvements_near_one": len(gains),
        "expected_improvements": 2 * 2 * 2,
        "failures": failures,
    }
    Path(args.output).write_text(json.dumps(output, indent=2, default=str))
    print(json.dumps(output["summary"], indent=2))
    if len(output["observations"]) != 24 or len(gains) != 8 or failures:
        raise SystemExit("Ganak output precision A/B did not meet its bounded expectations")


if __name__ == "__main__":
    main()
