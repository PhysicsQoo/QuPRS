#!/usr/bin/env python3
"""QFT16: preserve one Rust-generated CNF and compare Ganak 2.5.2 / 2.8.0 with mode 2 / 6."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import tempfile
import time
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
QASM = "qft_nativegates_ibm_qiskit_opt0_16.qasm"
UPSTREAM = "https://github.com/meelgroup/ganak/releases/download/release/2.5.2/ganak-linux-amd64.zip"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_legacy_binary(folder):
    request = urllib.request.Request(UPSTREAM, headers={"User-Agent": "QuPRS-benchmark-diagnostic"})
    with urllib.request.urlopen(request, timeout=90) as response:
        archive = response.read()
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        names = [n for n in zf.namelist() if n.split("/")[-1] == "ganak"]
        if len(names) != 1:
            raise RuntimeError("Unexpected legacy archive structure: " + repr(names))
        executable = folder / "ganak-2.5.2"
        executable.write_bytes(zf.read(names[0]))
        executable.chmod(0o755)
    return executable, hashlib.sha256(archive).hexdigest()


def run_case(binary, mode, cnf, timeout):
    t = time.perf_counter()
    try:
        result = subprocess.run([str(binary), f"--mode={mode}", str(cnf)],
                                text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"seconds": time.perf_counter()-t, "timed_out": True}
    from QuPRS.utils.wmc_solvers import parse_count_line
    count, raw_line = None, None
    for line in result.stdout.splitlines():
        if line.startswith("c s exact"):
            raw_line = line[:1600]
            try:
                c = parse_count_line(line)
                if c is not None:
                    count = [c.real, c.imag]
            except Exception as e:
                raw_line += " [parse error: " + str(e) + "]"
            break
    return {"seconds": time.perf_counter()-t, "returncode": result.returncode,
            "count": count, "result_line": raw_line,
            "stderr_tail": result.stderr[-1000:], "stdout_tail": result.stdout[-500:]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=45)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    os.chdir(ROOT)
    from QuPRS import check_equivalence
    from QuPRS.utils import WMC

    original = ROOT / "benchmarks/MQTBench" / QASM
    decomposed = ROOT / "benchmarks/MQTBench/h,ry,rz,cx" / QASM
    cnf_dir = args.output.parent / "captured_cnf"
    cnf_dir.mkdir(exist_ok=True)
    old_capture = os.environ.get("QUPRS_WMC_DIAGNOSTICS_DIR")
    os.environ["QUPRS_WMC_DIAGNOSTICS_DIR"] = str(cnf_dir.resolve())
    start = time.perf_counter()
    try:
        # Exactly test/test_MQT.py: switch=True, proportional, hybrid, Rust.
        verification = check_equivalence(str(decomposed), str(original),
                                         method="hybrid", strategy="proportional",
                                         tool_name="ganak", backend="rust", timeout=120)
    finally:
        full_walltime = time.perf_counter()-start
        if old_capture is None:
            os.environ.pop("QUPRS_WMC_DIAGNOSTICS_DIR", None)
        else:
            os.environ["QUPRS_WMC_DIAGNOSTICS_DIR"] = old_capture
    cnfs = sorted(cnf_dir.glob("ganak_*.cnf"))
    if len(cnfs) != 1:
        raise RuntimeError(f"Expected one CNF, found {len(cnfs)}")
    cnf = cnfs[0]

    with tempfile.TemporaryDirectory() as folder:
        legacy, archive_sha = get_legacy_binary(Path(folder))
        with WMC("ganak") as new_binary:
            binaries = {"2.5.2": legacy, "2.8.0": Path(new_binary).resolve()}
            combos = [(v, m) for v in binaries for m in (2, 6)]
            observations = {f"{v}/mode{m}": [] for v, m in combos}
            binary_sha = {v: sha256(p) for v, p in binaries.items()}
            for n in range(args.samples):
                for version, mode in combos[n % 4:] + combos[:n % 4]:
                    result = run_case(binaries[version], mode, cnf, args.timeout)
                    observations[f"{version}/mode{mode}"].append(result)
                    print(f"round={n+1} {version} mode={mode} "
                          f"time={result['seconds']:.3f}s rc={result.get('returncode')}", flush=True)

    summaries = {}
    for key, samples in observations.items():
        valid = [s for s in samples if s.get("returncode") == 0 and s.get("count") is not None]
        summaries[key] = {"success": len(valid), "total": len(samples),
                          "median_seconds": statistics.median(s["seconds"] for s in valid) if valid else None,
                          "count": valid[0]["count"] if valid else None}
    reference = summaries["2.8.0/mode2"]["count"]
    for record in summaries.values():
        value = record["count"]
        if value is not None and reference is not None:
            a = complex(*value)
            b = complex(*reference)
            record["relative_count_difference"] = abs(a-b)/max(abs(b), 1.0)

    payload = {
        "experiment": "QFT16 Rust exact input / Ganak 2.5.2 vs 2.8.0 / modes 2 and 6",
        "github_sha": os.environ.get("GITHUB_SHA"),
        "cpu": platform.processor(), "platform": platform.platform(),
        "inputs": {"decomposed_qasm_sha256": sha256(decomposed),
                   "original_qasm_sha256": sha256(original),
                   "cnf_sha256": sha256(cnf), "cnf_bytes": cnf.stat().st_size},
        "quprs_walltime_seconds": full_walltime,
        "quprs_status": str(verification.equivalent),
        "legacy_archive_sha256": archive_sha, "binary_sha256": binary_sha,
        "observations": observations, "summary": summaries,
        "limitations": [
            "2.5.2 is downloaded from upstream at run time; identity with historical cache must be checked.",
            "One NEW Rust-generated CNF is reused verbatim; old versus new encoder output is not yet compared.",
            "Mode 6 may have inadequate output precision; relative_count_difference is diagnostic only.",
        ],
    }
    args.output.write_text(json.dumps(payload, indent=2)+"\n")
    print(json.dumps({"inputs": payload["inputs"], "summary": summaries}, indent=2), flush=True)


if __name__ == "__main__":
    main()
