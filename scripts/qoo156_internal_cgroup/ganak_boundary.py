#!/usr/bin/env python3
"""One bounded Ganak 2.8.0 CLI-internal cgroup threshold observation.

The only changed independent variable is memory.max. Reuses the already
source-pinned authentic release Ganak test and *unmodified* Rust CLI supervisor.
An absent PID is explicitly NOT a genuine-solver-kill certificate.
This is a scientific admission test, never a CodSpeed performance measurement.
"""
import json
from pathlib import Path
import sys

from pilot import delegated_parent
from release_solver import run_case

# Previous identical source: 64/70 MiB typed internal OOM without witnessed
# solver PID; release Ganak high control 256 MiB fully completed, memory.peak
# near 71.5 MiB. Probe only a narrow 71--80 MiB interval plus one high control.
CAPS_MIB = (71, 72, 73, 74, 80)
CONTROL_MIB = 256


def characterize(value, expected_cap):
    pid = value["solver_process"]
    if value["cap_mib"] != expected_cap:
        raise AssertionError("inconsistent cap")
    if value["readback_max_bytes"] != expected_cap * 1048576:
        raise AssertionError("memory.max was not genuinely enforced")
    if value["cli_uid"] != 65534:
        raise AssertionError("CLI was not run as delegated non-root user")
    if value["harness_killed_cli"]:
        raise AssertionError("harness kill invalidates kernel-OOM attribution")

    witnessed = bool(
        pid and value.get("solver_pid_gone") is True and
        pid["elf_sha256"] == value["exact_solver_elf_sha256"] and
        "--mode=6" in pid["argv"]
    )
    oom = value["cgroup_oom_kill"]
    if (value["cli_exit_code"] == 0 and
            value["stdout"].strip() == "not_equivalent" and
            oom == 0 and witnessed):
        classification = "REAL_GANAK_COMPLETE_WITHIN_INTERNAL_CAP"
    elif (value["cli_exit_code"] == 125 and
          value["stdout"] == "" and
          "MemoryLimitExceeded" in value["stderr"] and
          isinstance(oom, int) and oom >= 1):
        # Missing PID does not mean Ganak never exec'ed. It only means
        # this polling harness cannot attribute the kernel victim to it.
        classification = (
            "INTERNAL_CGROUP_OOM_GANAK_PID_WITNESSED"
            if witnessed else
            "INTERNAL_CGROUP_OOM_NO_GANAK_PID_WITNESS"
        )
    else:
        classification = "NOT_ADMITTED_UNEXPECTED_CLI_OR_KERNEL_EVENT"
    return {
        "cap_mib": expected_cap,
        "classification": classification,
        "solver_pid_witnessed": witnessed,
        "solver_pid": pid["pid"] if pid else None,
        "solver_birth": pid["birth"] if pid else None,
        "kernel_oom_kill": oom,
        "memory_max_readback": value["readback_max_bytes"],
        "memory_peak_bytes": value["peak_bytes"],
        "cli_returncode": value["cli_exit_code"],
        "science_stdout": value["stdout"],
        "diagnostic": value["stderr"],
        "solver_elf_sha256": value["exact_solver_elf_sha256"],
        "cli_sha256": value["cli_sha256"],
        "original_harness_admitted": value["admitted"],
    }


def main():
    delegate = delegated_parent()
    results = []
    try:
        for cap in (*CAPS_MIB, CONTROL_MIB):
            # Existing source-pinned run_case checks real Ganak ELF/argv.
            # It expects a predefined outcome, so characterize independently
            # rather than re-labeling its raw "admitted" field.
            raw = run_case(delegate, "ganak", "vqe4", cap, "--mode=6",
                           high_cap=(cap == CONTROL_MIB))
            verdict = characterize(raw, cap)
            results.append(verdict)
            print("QOO156_GANAK_BOUNDARY_JSON=" +
                  json.dumps(verdict, sort_keys=True), flush=True)
        print("QOO156_GANAK_BOUNDARY_MANIFEST=" +
              json.dumps(results, sort_keys=True), flush=True)
        if results[-1]["classification"] != "REAL_GANAK_COMPLETE_WITHIN_INTERNAL_CAP":
            raise RuntimeError("NOT_ADMITTED: authentic 256MiB complete control")
        if any(r["classification"].startswith("NOT_ADMITTED") for r in results):
            raise RuntimeError("NOT_ADMITTED: unexpected state in Ganak cap sweep")
        print("QOO156_GANAK_CGROUP_BOUNDARY_SAFETY=PASS", flush=True)
        if any(r["classification"] == "INTERNAL_CGROUP_OOM_GANAK_PID_WITNESSED"
               for r in results):
            print("QOO156_GANAK_INTERNAL_PID_OOM_ATTRIBUTION=WITNESSED", flush=True)
        else:
            print("QOO156_GANAK_INTERNAL_PID_OOM_ATTRIBUTION=NOT_ADMITTED", flush=True)
    finally:
        try:
            (delegate / "supervisor").rmdir()
            delegate.rmdir()
        except OSError as error:
            print(f"QOO156_DELEGATED_CGROUP_CLEANUP_PENDING={error}", file=sys.stderr)


if __name__ == "__main__":
    main()
