#!/usr/bin/env python3
"""Host-side cgroup-v2 witness that survives container driver OOM.

This is a CHEAP controller-readiness gate, not real solver OOM certification.
No QuPRS binary or WMC solver is built or modified. All measurements are
scientific safety observations, never CodSpeed performance data.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

IMAGE = "python:3.12-slim"
PRESSURE_MIB = 192
CONTAINER_CODE = """
from pathlib import Path
import time
while not Path('/control/go').exists():
    time.sleep(.01)
pages = bytearray(192 * 1048576)
for offset in range(0, len(pages), 4096):
    pages[offset] = 1
print('QOO156_TOUCH_COMPLETE', flush=True)
time.sleep(.5)
"""


def docker(*args, timeout=30):
    return subprocess.run(["docker", *map(str, args)], text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=timeout, check=True).stdout.strip()


def inspect(identifier):
    return json.loads(docker("inspect", identifier))[0]


def current_cgroup(host_pid):
    content = Path(f"/proc/{host_pid}/cgroup").read_text()
    relative = next((line[3:] for line in content.splitlines()
                     if line.startswith("0::")), None)
    if relative is None:
        raise RuntimeError("NOT_ADMITTED: cgroup-v2 process identity unavailable")
    root = Path("/sys/fs/cgroup").resolve()
    found = (root / relative.lstrip("/")).resolve()
    if found != root and root not in found.parents:
        raise RuntimeError("NOT_ADMITTED: unexpected cgroup path")
    if not (found / "memory.events").is_file():
        raise RuntimeError("NOT_ADMITTED: host cannot observe container memory.events")
    return found


def read_events(group):
    return {key: int(value) for key, value in
            (line.split() for line in (group / "memory.events").read_text().splitlines())}


def record(target, event, **data):
    with target.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(dict(event=event, **data), sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def exercise(outdir, cap_mib):
    label = f"{cap_mib}mib"
    journal = outdir / f"{label}.jsonl"
    control = Path(tempfile.mkdtemp(prefix=f"qoo156-host-{label}-", dir=outdir))
    # A cap-drop=ALL root inside the container cannot traverse the host's
    # mkdtemp default 0700 directory (no CAP_DAC_READ_SEARCH). The sole
    # control marker is intentionally world-readable; no write is needed
    # inside the container. This prevents a false early PermissionError.
    control.chmod(0o755)
    identifier = None
    try:
        record(journal, "case_started", cap_mib=cap_mib, pressure_mib=PRESSURE_MIB)
        identifier = docker(
            "run", "-d", "--memory", f"{cap_mib}m",
            "--memory-swap", f"{cap_mib}m", "--network=none",
            "--pids-limit=64", "--read-only", "--cap-drop=ALL",
            "--security-opt", "no-new-privileges",
            "--mount", f"type=bind,source={control},target=/control,readonly",
            IMAGE, "python", "-u", "-c", CONTAINER_CODE,
        )
        status = inspect(identifier)
        host_pid = int(status["State"]["Pid"])
        if host_pid <= 0:
            raise RuntimeError("NOT_ADMITTED: container died before host observer armed")
        group = current_cgroup(host_pid)
        actual = (group / "memory.max").read_text().strip()
        assert actual == str(cap_mib * 1048576), (
            f"NOT_ADMITTED: memory.max={actual} not requested {cap_mib} MiB")
        baseline = read_events(group)
        record(journal, "armed", container_id=identifier, host_init_pid=host_pid,
               cgroup=str(group), memory_max_bytes=int(actual),
               baseline=baseline, image_id=docker("image", "inspect", IMAGE,
                                                 "--format", "{{.Id}}"))
        (control / "go").touch()
        deadline = time.monotonic() + 18
        previous_oom = baseline.get("oom_kill", 0)
        latest_events = baseline
        peak = None
        while time.monotonic() < deadline:
            try:
                latest_events = read_events(group)
                peak = int((group / "memory.peak").read_text())
            except OSError as exc:
                record(journal, "observation_lost", detail=str(exc))
                break
            oom = latest_events.get("oom_kill", 0)
            if oom > previous_oom:
                record(journal, "kernel_oom_observed", oom_kill_delta=oom -
                       baseline.get("oom_kill", 0), events=latest_events,
                       memory_peak_bytes=peak)
                previous_oom = oom
            # Docker keeps the container (without --rm) for final inspection.
            if docker("inspect", identifier, "--format", "{{.State.Running}}") == "false":
                break
            time.sleep(.02)
        try:
            docker("wait", identifier, timeout=8)
        except subprocess.TimeoutExpired:
            record(journal, "wait_timeout", note="harness cleanup is not kernel OOM")
            raise RuntimeError("NOT_ADMITTED: container did not finish within bounded wait")
        final_state = inspect(identifier)["State"]
        try:
            final_events = read_events(group)
        except OSError:
            final_events = latest_events
        logs = docker("logs", identifier)
        (outdir / f"{label}.container.log").write_text(logs + "\\n")
        result = {
            "cap_mib": cap_mib,
            "exit_code": int(final_state["ExitCode"]),
            "docker_oom_flag": bool(final_state["OOMKilled"]),
            "kernel_oom_kill_delta": final_events.get("oom_kill", 0) -
                                     baseline.get("oom_kill", 0),
            "memory_peak_bytes": peak,
            "touch_complete": "QOO156_TOUCH_COMPLETE" in logs,
        }
        record(journal, "final", **result)
        if cap_mib == 128:
            ok = (result["kernel_oom_kill_delta"] >= 1 and
                  result["exit_code"] != 0 and not result["touch_complete"])
        else:
            ok = (result["kernel_oom_kill_delta"] == 0 and
                  result["exit_code"] == 0 and result["touch_complete"])
        if not ok:
            raise RuntimeError(f"NOT_ADMITTED: incorrect host witness: {result}")
        return result
    finally:
        if identifier:
            try:
                docker("rm", "-f", identifier, timeout=15)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                record(journal, "cleanup_failed", container_id=identifier)
        shutil.rmtree(control, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()
    outdir = Path(args.evidence).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    summary = outdir / "summary.json"
    try:
        experiments = [exercise(outdir, cap) for cap in (128, 320)]
        summary.write_text(json.dumps(experiments, indent=2, sort_keys=True) + "\n")
        print("QOO156_HOST_EXTERNAL_OOM_WITNESS=PASS", flush=True)
    except Exception as exc:
        summary.write_text(json.dumps({"admission": "NOT_ADMITTED",
                                        "error": str(exc)}, indent=2) + "\n")
        print(f"QOO156_HOST_EXTERNAL_OOM_WITNESS=NOT_ADMITTED: {exc}", flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
