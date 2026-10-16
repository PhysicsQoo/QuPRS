#!/usr/bin/env python3
"""QFT16 MPFR precision sweep. Read P0's exact CNF and oracle; never change QuPRS defaults."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import time


def run(binary, cnf, bits, timeout):
    command = [str(binary), "--mode=6", f"--mpfrprec={bits}", str(cnf)]
    start = time.perf_counter()
    try:
        p = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"elapsed_sec": time.perf_counter()-start, "timed_out": True,
                "command": command}
    from QuPRS.utils.wmc_solvers import parse_count_line
    count = None
    raw = None
    for line in p.stdout.splitlines():
        if line.startswith("c s exact"):
            raw = line
            try:
                val = parse_count_line(line)
                if val is not None:
                    count = [val.real, val.imag]
            except (ValueError, OverflowError) as exc:
                raw += " [parse error: " + str(exc) + "]"
            break
    return {"elapsed_sec": time.perf_counter()-start, "exit_code": p.returncode,
            "count": count, "raw_count_line": raw,
            "stderr_tail": p.stderr[-700:], "stdout_tail": p.stdout[-500:]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True,
                        help="report.json produced by diagnose_ganak_qft16.py")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=3)
    args = parser.parse_args()
    original = json.loads(args.report.read_text())
    reference_value = original["summary"]["2.8.0/mode2"]["count"]
    if not reference_value:
        raise RuntimeError("Missing exact complex-rational oracle")
    ref = complex(*reference_value)
    paths = list((args.report.parent / "captured_cnf").glob("ganak_*.cnf"))
    if len(paths) != 1:
        raise RuntimeError(f"Expected one captured CNF; got {len(paths)}")
    cnf = paths[0]
    digest = hashlib.sha256(cnf.read_bytes()).hexdigest()
    if digest != original["inputs"]["cnf_sha256"]:
        raise RuntimeError("CNF hash mismatch between measurements")
    from QuPRS.utils import WMC
    observations = {}
    with WMC("ganak") as path:
        binary = Path(path).resolve()
        for bits in (128, 256, 512):
            collected = []
            for n in range(args.samples):
                case = run(binary, cnf, bits, timeout=45)
                if case.get("exit_code") == 0 and case.get("count") is not None:
                    z = complex(*case["count"])
                    case["absolute_error"] = abs(z-ref)
                    case["relative_error"] = abs(z-ref)/max(1.0, abs(ref))
                    case["phase_error_rad"] = abs(math.atan2((z/ref).imag, (z/ref).real)) if ref != 0 else None
                collected.append(case)
                print(f"MPFR {bits} bits sample {n+1}: rc={case.get('exit_code')}, "
                      f"sec={case['elapsed_sec']:.4f}, rel_error={case.get('relative_error')}",
                      flush=True)
            observations[str(bits)] = collected
    summary = {}
    for bits, obs in observations.items():
        ok = [s for s in obs if s.get("exit_code") == 0 and s.get("count") is not None]
        summary[bits] = {"success": len(ok), "total": len(obs),
                         "median_seconds": statistics.median(s["elapsed_sec"] for s in ok)
                         if ok else None,
                         "relative_error": ok[0]["relative_error"] if ok else None,
                         "raw_count_line": ok[0]["raw_count_line"] if ok else None}
    payload = {"precision_unit": "bits", "cnf_sha256": digest,
               "oracle": reference_value, "summary": summary,
               "observations": observations,
               "notes": ["MPFR mode 6 is approximate even when higher precision is configured.",
                         "Printed output may round/truncate, regardless of internal precision.",
                         "No production solver setting is changed."]}
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)
    if any(s["success"] != args.samples for s in summary.values()):
        raise SystemExit("One or more MPFR configurations failed; see diagnostic artifact")


if __name__ == "__main__":
    main()
