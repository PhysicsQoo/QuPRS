#!/usr/bin/env python3
"""Real QuPRS debug worker under externally enforced Docker memory.max.

External Docker memory control only: this does NOT certify QuPRS's internal
--max-memory-mib child-cgroup implementation or a typed OOM result.
"""
import json
import os
import pathlib
import signal
import subprocess
import sys
import time

LIMIT_MIB = int(os.environ["QOO156_CONTAINER_MEM_MIB"])
ALLOCATION_MIB = 192
ROOT = pathlib.Path("/sys/fs/cgroup")
CLI = "/opt/QuPRS_cli"
QASM = "/opt/single_h.qasm"


def read_events():
    path = ROOT / "memory.events"
    return {k: int(v) for k, v in (line.split() for line in path.read_text().splitlines())}


def main():
    memory_max = (ROOT / "memory.max").read_text().strip()
    observed_max = int(memory_max) if memory_max != "max" else None
    before = read_events()
    env = os.environ.copy()
    env["QUPRS_CLI_TEST_ALLOC_MIB"] = str(ALLOCATION_MIB)
    command = [CLI, QASM, "--timeout", "12", "--quiet"]
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, start_new_session=True, env=env)
    try:
        out, err = p.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        out, err = p.communicate(timeout=5)
    after = read_events()
    delta = after.get("oom_kill", 0) - before.get("oom_kill", 0)
    no_scientific_verdict = not any(
        token in out.lower()
        for token in ("equivalent", "not_equivalent", "reduced pathsum state")
    )
    actual_limit = LIMIT_MIB * 1024 * 1024
    if LIMIT_MIB == 384:
        passed = (observed_max == actual_limit and delta == 0 and p.returncode == 0
                  and "Reduced PathSum State" in out)
    else:
        passed = (observed_max == actual_limit and delta >= 1
                  and p.returncode != 0 and no_scientific_verdict)
    record = {
        "test": "quprs_real_cli_external_docker_memory",
        "limit_mib": LIMIT_MIB,
        "touch_mib": ALLOCATION_MIB,
        "kernel_memory_max_bytes": observed_max,
        "kernel_oom_kill_delta": delta,
        "worker_or_cli_exit": p.returncode,
        "no_partial_scientific_result": no_scientific_verdict,
        "stdout_tail": out[-750:],
        "stderr_tail": err[-1200:],
        "classification": "EXTERNAL_DOCKER_CLI_MEMORY_PASS" if passed else "NOT_ADMITTED",
        "internal_quprs_memory_cap_certificate": "NOT_TESTED",
    }
    print("QOO156_EXTERNAL_CLI_MEM_JSON=" + json.dumps(record, sort_keys=True), flush=True)
    print(f"QOO156_EXTERNAL_CLI_MEMORY_{LIMIT_MIB}_MIB={record['classification']}", flush=True)
    return 0 if passed else 2


if __name__ == "__main__":
    sys.exit(main())
