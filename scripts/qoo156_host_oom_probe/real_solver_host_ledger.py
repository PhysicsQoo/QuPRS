#!/usr/bin/env python3
"""Source-pinned authentic solver OOM pilot with a host-side cgroup recorder.

This is an adversarial test-only pressure experiment, NOT the natural solver
working set, NOT an internal CLI --max-memory-mib certification, and NOT
CodSpeed. Never turn missing evidence into a positive admission.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from host_ledger import docker, inspect, current_cgroup, read_events, record

CAP_MIB = 256
SOLVERS = {
    "gpmc": ("-mode=1", "507919b9af456645b55dc73e7d4db4a56b9293a0fa3ba99f5f8a0986826ef4b1"),
    "ganak": ("--mode=6", "934a79a3db2f5b3928ce89edde20837f652e4679b099320ac71c198699c709dd"),
}
BARRIER_WRAPPER = """
import os,time
from pathlib import Path
while not Path('/control/go').exists():
    time.sleep(.01)
os.execv('/usr/bin/python3', ['/usr/bin/python3','/opt/driver.py'])
"""


def parse_line(logs, prefix):
    lines = [line.split(prefix, 1)[1] for line in logs.splitlines() if prefix in line]
    return json.loads(lines[-1]) if lines else None


def exercise(outdir, solver, workspace):
    mode, digest = SOLVERS[solver]
    journal = outdir / f"{solver}.jsonl"
    control = Path(tempfile.mkdtemp(prefix=f"qoo156-real-{solver}-", dir=outdir))
    control.chmod(0o755)
    ident = None
    try:
        record(journal, "source_pinned_case_start", solver=solver,
               cap_mib=CAP_MIB, expected_sha256=digest, expected_argv_mode=mode)
        ident = docker(
            "run", "-d", "--memory=256m", "--memory-swap=256m",
            "--network=none", "--pids-limit=64", "--read-only",
            "--cap-drop=ALL", "--security-opt", "no-new-privileges",
            "--user", "65534:65534", "--tmpfs", "/tmp:rw,nosuid,size=64m",
            "--mount", f"type=bind,source={control},target=/control,readonly",
            "--mount", f"type=bind,source={workspace}/rust/target/release/QuPRS_cli,target=/opt/QuPRS_cli,readonly",
            "--mount", f"type=bind,source={workspace}/src/QuPRS/utils/wmc_tools/gpmc,target=/opt/gpmc,readonly",
            "--mount", f"type=bind,source={workspace}/src/QuPRS/utils/wmc_tools/ganak,target=/opt/ganak,readonly",
            "--mount", f"type=bind,source={workspace}/benchmarks/MQTBench/vqe_nativegates_ibm_qiskit_opt0_4.qasm,target=/opt/vqe4.qasm,readonly",
            "--mount", f"type=bind,source={workspace}/scripts/qoo156_solver_oom_victim/driver.py,target=/opt/driver.py,readonly",
            "-e", f"QOO156_SOLVER={solver}",
            "--entrypoint", "python3", "qoo156-wmc:host-real-oom",
            "-u", "-c", BARRIER_WRAPPER,
        )
        state = inspect(ident)
        host_pid = int(state["State"]["Pid"])
        if host_pid <= 0:
            raise RuntimeError("NOT_ADMITTED: solver container exited before host observer")
        group = current_cgroup(host_pid)
        cap = (group / "memory.max").read_text().strip()
        if cap != str(CAP_MIB * 1048576):
            raise RuntimeError("NOT_ADMITTED: Docker kernel cap mismatch")
        baseline = read_events(group)
        record(journal, "armed", container_id=ident, host_pid=host_pid,
               cgroup=str(group), baseline=baseline, memory_max_bytes=int(cap))
        (control / "go").touch()
        seen_oom = baseline.get("oom_kill", 0)
        latest = baseline
        peak = None
        deadline = time.monotonic() + 38
        while time.monotonic() < deadline:
            try:
                latest = read_events(group)
                peak = int((group / "memory.peak").read_text().strip())
            except OSError as exc:
                record(journal, "observation_lost", detail=str(exc))
                break
            new_oom = latest.get("oom_kill", 0)
            if new_oom > seen_oom:
                record(journal, "host_kernel_oom", events=latest,
                       oom_kill_delta=new_oom - baseline.get("oom_kill", 0),
                       memory_peak_bytes=peak)
                seen_oom = new_oom
            if docker("inspect", "--format", "{{.State.Running}}", ident) == "false":
                break
            time.sleep(.02)
        try:
            docker("wait", ident, timeout=8)
        except subprocess.TimeoutExpired:
            record(journal, "host_wait_timeout", note="harness cleanup not kernel OOM")
            raise RuntimeError("NOT_ADMITTED: real solver container exceeded bounded wait")
        result_state = inspect(ident)["State"]
        try:
            latest = read_events(group)
        except OSError:
            pass
        logs = docker("logs", ident)
        (outdir / f"{solver}.log").write_text(logs + "\n")
        pre = parse_line(logs, "QOO156_SOLVER_PREPRESSURE_JSON=")
        inner = parse_line(logs, "QOO156_SOLVER_OOM_VICTIM_JSON=")
        kernel_delta = latest.get("oom_kill", 0) - baseline.get("oom_kill", 0)
        identity_valid = bool(
            pre and pre.get("solver") == solver and
            pre.get("solver_elf_sha256") == digest and
            pre.get("oom_score_adj") == 1000 and
            pre.get("target", {}).get("elf_sha256") == digest and
            mode in pre.get("target", {}).get("argv", [])
        )
        inner_valid = bool(
            inner and inner.get("classification") ==
                    "REAL_SOLVER_EXTERNAL_KERNEL_OOM_NO_FALSE_VERDICT_PASS"
            and inner.get("kernel_oom_kill_delta", 0) >= 1
            and inner.get("target_solver", {}).get("pid") ==
                    pre.get("target", {}).get("pid")
            and not inner.get("test_harness_killed_solver")
            and inner.get("cli_stdout") == ""
        ) if pre else False
        classification = (
            "REAL_SOLVER_EXTERNAL_KERNEL_OOM_WITH_HOST_WITNESS_PASS"
            if (identity_valid and inner_valid and kernel_delta >= 1
                and int(result_state["ExitCode"]) == 0)
            else "NOT_ADMITTED_SOLVER_VICTIM_UNVERIFIED"
        )
        summary = {
            "solver": solver, "classification": classification,
            "outer_kernel_oom_kill_delta": kernel_delta, "inner": inner,
            "prepressure": pre, "solver_identity_valid": identity_valid,
            "container_exit": int(result_state["ExitCode"]),
            "docker_oom_flag": bool(result_state["OOMKilled"]),
            "memory_peak_bytes": peak,
            "note": "Artificial pressure, not natural solver RSS or internal CLI memory cap.",
        }
        record(journal, "final", **summary)
        print("QOO156_REAL_SOLVER_HOST_OOM", solver, classification,
              "kernel_oom_kill_delta", kernel_delta, flush=True)
        return summary
    finally:
        if ident:
            try:
                docker("rm", "-f", ident, timeout=15)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                record(journal, "cleanup_failed", container_id=ident)
        shutil.rmtree(control, ignore_errors=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", required=True)
    p.add_argument("--evidence", required=True)
    args = p.parse_args()
    outdir = Path(args.evidence).resolve()
    workspace = Path(args.workspace).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    results = []
    for solver in SOLVERS:
        try:
            results.append(exercise(outdir, solver, workspace))
        except Exception as exc:
            results.append({"solver": solver, "classification": "NOT_ADMITTED_ERROR",
                            "detail": str(exc)})
            print("QOO156_REAL_SOLVER_HOST_OOM", solver, "NOT_ADMITTED_ERROR", exc)
    (outdir / "real_solver_manifest.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n")
    if not all(item["classification"] ==
               "REAL_SOLVER_EXTERNAL_KERNEL_OOM_WITH_HOST_WITNESS_PASS"
               for item in results):
        raise SystemExit("QOO156_REAL_SOLVER_HOST_OOM_CERTIFICATE=NOT_ADMITTED")
    print("QOO156_REAL_SOLVER_HOST_OOM_CERTIFICATE=PASS")


if __name__ == "__main__":
    main()
