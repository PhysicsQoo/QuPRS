#!/usr/bin/env python3
"""Run the *real archived* TACAS26 QPE-inexact20 positive experiment.

This script is mounted read-only into the archived Docker image. It never
changes QuPRS decision logic or replaces GPMC answers; instrumented wrappers
observe the exact stdout and return objects of the original subprocess.
Not a CodSpeed measurement, and not a full-unitary proof.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

HISTORICAL_SHA = "e928abc47dd15926364ec77905eb0d5dc92ce8cc"
INPUTS = {
    "original": (
        "/app/benchmarks/MQTBench/qpeinexact_nativegates_ibm_qiskit_opt0_20.qasm",
        "1aab3d61462144fc59ace2ffda5d2382776aec4bf5f1bacdb8ac31ee7400751c",
    ),
    "transpiled": (
        "/app/benchmarks/MQTBench/h,ry,rz,cx/qpeinexact_nativegates_ibm_qiskit_opt0_20.qasm",
        "3d8370285c872197c45853c0ebe96be09ef08eabe998da48d426de80e54aeb82",
    ),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_and_check_environment() -> dict:
    from importlib import resources

    import qiskit
    import QuPRS
    from QuPRS import config
    from QuPRS.interface import load_qiskit

    info = {
        "python_version": sys.version,
        "qiskit_version": qiskit.__version__,
        "quprs_distribution_version": importlib.metadata.version("QuPRS"),
        "quprs_python_file": str(Path(QuPRS.__file__).resolve()),
        "quprs_classification_file": str(Path(load_qiskit.__file__).resolve()),
        "quprs_config_tolerance": config.TOLERANCE,
        "source": {},
        "archive_installed_git_sha": None,
        "gpmc_binary_sha256": None,
    }
    head = subprocess.run(["git", "-C", "/app", "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True)
    info["archive_installed_git_sha"] = head.stdout.strip()
    if info["archive_installed_git_sha"] != HISTORICAL_SHA:
        raise ValueError("Archived QuPRS source SHA is not the TACAS v0.9.1 pin")
    if not Path(load_qiskit.__file__).resolve().is_relative_to(Path("/app").resolve()):
        raise ValueError("QuPRS import escaped the archived /app source tree")
    if config.TOLERANCE != 1e-10:
        raise ValueError("Unexpected TACAS QuPRS TOLERANCE")
    text = Path(load_qiskit.__file__).read_text()
    if ("log_wmc = round(np.log2(abs_num), 3)" not in text
            or "abs(log_wmc - expect) < tolerance" not in text):
        raise ValueError("Archived numerical classifier differs from v0.9.1")
    for name, (location, expected) in INPUTS.items():
        actual = _sha256(Path(location))
        if actual != expected:
            raise ValueError(f"Historical input source mismatch: {name}")
        info["source"][name] = {
            "path": location, "sha256": actual,
            "git_blob_from_artifact_research": (
                "4535af5bd2c7603e40e2828bb7438ab6240aea9f" if name == "original"
                else "f7dd85917d461a9d3cfcacc71ba2d9410ba3c471"),
        }
    binary = resources.files("QuPRS.utils").joinpath("gpmc.so")
    if not binary.is_file():
        raise ValueError("Archived native GPMC gpmc.so not found")
    info["gpmc_binary_sha256"] = _sha256(Path(str(binary)))
    return info


def observe_real_verification(output: dict) -> None:
    import numpy as np
    from QuPRS import check_equivalence
    from QuPRS.interface import ps2wmc
    from QuPRS.utils.util import get_theta

    original_run = ps2wmc.subprocess.run
    original_wmc = ps2wmc.run_wmc
    traces = []
    counts = []
    output["solver_subprocesses"] = traces
    output["solver_complex_outputs"] = counts

    def transparent_subprocess_run(args, *pargs, **kwargs):
        result = original_run(args, *pargs, **kwargs)
        args_list = [str(item) for item in args]
        if "-mode=1" in args_list and any("gpmc" in item for item in args_list):
            traces.append({
                "command": args_list,
                "returncode": result.returncode,
                "stdout": result.stdout if isinstance(result.stdout, str)
                          else repr(result.stdout),
                "stderr": result.stderr if isinstance(result.stderr, str)
                          else repr(result.stderr),
            })
        return result

    def transparent_wmc(file="wmc.cnf"):
        real_imag = original_wmc(file)
        counts.append({"real": float(real_imag[0]), "imag": float(real_imag[1])})
        return real_imag

    # Observers return exactly the original objects; no GPMC output rewriting.
    ps2wmc.subprocess.run = transparent_subprocess_run
    ps2wmc.run_wmc = transparent_wmc
    try:
        result = check_equivalence(
            INPUTS["original"][0],
            INPUTS["transpiled"][0],
            method="hybrid",
            strategy="Proportional",
            timeout=200,
        )
    finally:
        ps2wmc.subprocess.run = original_run
        ps2wmc.run_wmc = original_wmc

    outcome = {
        "verdict": str(result.equivalent),
        "method": str(result.method),
        "strategy": str(result.strategy),
        "expect_log2": float(result.expect) if result.expect is not None else None,
        "legacy_rounded_log2_wmc": (
            float(result.log_wmc) if result.log_wmc is not None else None),
        "gpmc_invocations_observed": len(traces),
        "complex_returns_observed": len(counts),
        "phase_angle_rad_from_original_get_theta": None,
        "raw_magnitude_log2": None,
        "replayed_v091_verdict": None,
    }
    if counts:
        r, i = counts[-1]["real"], counts[-1]["imag"]
        magnitude = float(np.sqrt(r*r + i*i))
        if magnitude == 0 or not math.isfinite(magnitude):
            raise ValueError("Invalid historical GPMC magnitude")
        theta = float(get_theta(i / magnitude, r / magnitude))
        raw_log2 = float(np.log2(magnitude))
        outcome["raw_magnitude_log2"] = raw_log2
        outcome["phase_angle_rad_from_original_get_theta"] = theta
        if outcome["expect_log2"] is not None:
            tol = 1e-10
            if abs(round(raw_log2, 3)-outcome["expect_log2"]) < tol:
                outcome["replayed_v091_verdict"] = (
                    "equivalent" if abs(theta) < tol * 2 * np.pi else "equivalent*")
            else:
                outcome["replayed_v091_verdict"] = "not_equivalent"
    output["historical_result"] = outcome


def run(output_file: Path) -> dict:
    data = {
        "schema": "quprs-tacas26-archived-qpe20-live-v1",
        "source_of_truth": "Zenodo record 18158735 prebuilt Docker image",
        "archived_image_tested": True,
        "source_archive_git_sha_required": HISTORICAL_SHA,
        "paper_expected_verdict": "equivalent*",
        "paper_execution": "hybrid proportional, 200-second limit, positive source pair",
        "science_certification": "NOT_YET_VERIFIED",
        "performance_claim": "NONE_NOT_A_CODSPEED_RUN",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "error": None,
    }
    try:
        data["environment"] = load_and_check_environment()
        observe_real_verification(data)
        observed = data["historical_result"]
        if observed["verdict"] != "equivalent*":
            raise AssertionError("Archived TACAS QPE20 expected equivalent* but observed " +
                                 observed["verdict"])
        if observed["gpmc_invocations_observed"] < 1:
            raise AssertionError("No real archived GPMC stdout was observed")
        if observed["replayed_v091_verdict"] != observed["verdict"]:
            raise AssertionError("Observed GPMC complex phase does not replay v0.9.1 verdict")
        if not data["solver_subprocesses"] or any(
                row["returncode"] != 0 for row in data["solver_subprocesses"]):
            raise AssertionError("Archived GPMC process did not complete successfully")
        data["science_certification"] = "ARCHIVE_QPE20_POSITIVE_PASS_ONLY"
    except BaseException as exc:
        data["science_certification"] = "ARCHIVE_QPE20_NOT_CERTIFIED"
        data["error"] = {"type":type(exc).__name__, "message":str(exc),
                         "traceback":traceback.format_exc()[-4500:]}
    finally:
        data["finished_utc"] = datetime.now(timezone.utc).isoformat()
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",
                               encoding="utf-8")
    return data


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True,type=Path)
    opts=p.parse_args()
    result=run(opts.output)
    summary={"verdict":result.get("historical_result",{}).get("verdict"),
             "solver_invoked":bool(result.get("solver_subprocesses")),
             "certification":result["science_certification"],
             "error":result["error"]["message"] if result["error"] else None}
    print("TACAS26_ARCHIVE_QPE20 "+json.dumps(summary,sort_keys=True),flush=True)
    if result["science_certification"]!="ARCHIVE_QPE20_POSITIVE_PASS_ONLY":
        raise SystemExit(1)


if __name__=="__main__":
    main()
