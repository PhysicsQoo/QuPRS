#!/usr/bin/env python3
"""One actual native Rust FFI invocation, measured without import/QASM setup."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time

from qiskit import qasm2
from QuPRS import _pathsum_rust

STATUS_OK = {"Equivalent", "Equivalent (Up to Global Phase)"}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--left", type=Path, required=True)
    parser.add_argument("--right", type=Path, required=True)
    parser.add_argument("--mode", required=True, choices=("A", "B", "C"))
    parser.add_argument("--case", required=True, choices=("qaoa7", "qft16"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    # The QASM2 conversion and import costs are deliberately OUTSIDE timed FFI.
    # This reproduces the original native-stage scientific pilot's input format.
    left, right = qasm2.dumps(qasm2.load(str(args.left))), qasm2.dumps(qasm2.load(str(args.right)))
    if args.mode == "C":
        os.environ["QUPRS_STAGE_LEDGER"] = "1"
    else:
        os.environ.pop("QUPRS_STAGE_LEDGER", None)
    if not Path(os.environ["QUPRS_GPMC_PATH"]).is_file():
        raise FileNotFoundError("Shared GPMC binary not found")

    start = time.perf_counter()
    raw = _pathsum_rust.check_equivalence(
        left, right, method="hybrid", strategy="Proportional",
        tool_name="gpmc", timeout=args.timeout
    )
    wrapper_wall = time.perf_counter() - start
    stage = raw.get("stage_ledger")
    violations = []
    if raw["status"] not in STATUS_OK:
        violations.append("non-equivalent / undecided native result: " + str(raw["status"]))
    if (stage is not None) != (args.mode == "C"):
        violations.append("opt-in stage_ledger presence mismatch")

    structural = None
    if stage is not None:
        structural = stage.get("structural_elim_attempts")
        if not isinstance(structural, list):
            violations.append("structural_elim_attempts not list")
        else:
            for sample in structural:
                if set(sample) != {"k_r", "l_r", "v_r", "d_r", "w_redundant_estimated"}:
                    violations.append("unexpected structural sample schema")
                    break
                if sample["w_redundant_estimated"] != max(sample["k_r"] - 1, 0) * sample["l_r"]:
                    violations.append("estimated W formula mismatch")
                    break
                if not 0 <= sample["k_r"] <= sample["v_r"]:
                    violations.append("candidate count exceeds active path vars")
                    break
        if stage["has_stage_overlap"] or abs(stage["closure_error_seconds"]) > 1e-6:
            violations.append("stage ledger closure or overlap failure")
        if abs(sum(stage["exclusive_seconds"].values()) - stage["total_native_wall_seconds"]) > 1e-6:
            violations.append("exclusive stage partition failure")

    payload = {
        "schema": "quprs-rust-abc-observation-v1",
        "mode": args.mode,
        "case": args.case,
        "status": raw["status"],
        "classification": "equivalent" if raw["status"] == "Equivalent" else "equivalent*"
                          if raw["status"] == "Equivalent (Up to Global Phase)" else "invalid",
        "input_qasm_sha256": [sha256(left.encode()), sha256(right.encode())],
        "module_path": str(Path(_pathsum_rust.__file__).resolve()),
        "python_version": platform.python_version(),
        "ffi_wrapper_wall_seconds": wrapper_wall,
        "native_total_seconds": raw["verification_time_sec"],
        "native_pathsum_seconds": raw["pathsum_time_sec"],
        "wmc_time_seconds": raw.get("wmc_time_sec"),
        "solver_time_seconds": raw.get("wmc_solver_time_sec"),
        "rules": raw["stats"],
        "final_ps_sha256": sha256(raw["final_ps"].encode()),
        "stage_ledger": stage,
        "validation_errors": violations,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"mode": args.mode, "case": args.case,
                      "status": raw["status"], "wrapper": wrapper_wall,
                      "reduction": stage["exclusive_seconds"].get("reduction") if stage else None}), flush=True)
    return 0 if not violations else 2


if __name__ == "__main__":
    sys.exit(main())
