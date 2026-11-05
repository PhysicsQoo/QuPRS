"""Linux delegated cgroup-v2 resource scope for the private Rust API supervisor.

An explicit physical-memory cap is never substituted with RLIMIT_AS. Only a
dedicated, empty memory-enabled delegated cgroup ancestor is eligible.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import time


class ResourceAdmissionError(RuntimeError):
    pass


def positive_mib(name: str) -> int | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    if not raw.isascii() or not raw.isdecimal():
        raise ResourceAdmissionError(f"{name} must be a positive integer MiB value")
    value = int(raw)
    if not (0 < value <= (2**63 - 1) // (1024 * 1024)):
        raise ResourceAdmissionError(f"{name} is outside the supported MiB range")
    return value


def _unique_counter(data: str, field: str) -> int:
    matches = []
    for line in data.splitlines():
        parts = line.split()
        if parts and parts[0] == field:
            if len(parts) != 2 or not parts[1].isascii() or not parts[1].isdecimal():
                raise ResourceAdmissionError(f"malformed {field} cgroup counter")
            matches.append(int(parts[1]))
    if len(matches) != 1:
        raise ResourceAdmissionError(f"missing or repeated {field} cgroup counter")
    return matches[0]


def parse_oom_events(data: str) -> bool:
    # Both fields must be present even when the first is already nonzero.
    oom = _unique_counter(data, "oom")
    oom_kill = _unique_counter(data, "oom_kill")
    return oom > 0 or oom_kill > 0


def parse_populated(data: str) -> bool:
    populated = _unique_counter(data, "populated")
    if populated not in (0, 1):
        raise ResourceAdmissionError("invalid cgroup.events populated value")
    return populated == 1


class MemoryCgroup:
    def __init__(self, path: Path):
        self.path = path
        self._cleaned = False

    @classmethod
    def create_if_requested(cls) -> MemoryCgroup | None:
        mib = positive_mib("QUPRS_ISOLATED_MAX_MEMORY_MIB")
        if mib is None:
            return None
        if os.name != "posix" or not Path("/proc/self/cgroup").exists():
            raise ResourceAdmissionError("physical memory cap requires delegated Linux cgroup v2")
        try:
            lines = Path("/proc/self/cgroup").read_text().splitlines()
            rel = next(line[3:] for line in lines if line.startswith("0::"))
        except (OSError, StopIteration) as exc:
            raise ResourceAdmissionError("no cgroup-v2 membership found") from exc
        root = Path("/sys/fs/cgroup").resolve(strict=True)
        member = (root / rel.lstrip("/")).resolve(strict=True)
        if not member.is_relative_to(root):
            raise ResourceAdmissionError("cgroup membership escaped controller root")
        candidate = member
        while candidate.is_relative_to(root):
            try:
                enabled = (candidate / "cgroup.subtree_control").read_text().split()
                procs = (candidate / "cgroup.procs").read_text().strip()
            except OSError as exc:
                raise ResourceAdmissionError("cannot inspect delegated cgroup ancestor") from exc
            if "memory" in enabled and not procs:
                try:
                    path = Path(tempfile.mkdtemp(prefix="quprs-py-", dir=candidate))
                except PermissionError:
                    path = None  # Ancestor is not delegated to this user.
                except OSError as exc:
                    raise ResourceAdmissionError("cannot create worker cgroup") from exc
                if path is not None:
                    try:
                        byte_limit = mib * 1024 * 1024
                        (path / "memory.max").write_text(str(byte_limit))
                        (path / "memory.oom.group").write_text("1")
                        if (path / "memory.max").read_text().strip() != str(byte_limit):
                            raise ResourceAdmissionError("memory.max readback mismatch")
                    except Exception:
                        try:
                            path.rmdir()
                        except OSError:
                            pass
                        raise
                    return cls(path)
            if candidate == root:
                break
            candidate = candidate.parent
        raise ResourceAdmissionError("no delegated writable memory cgroup; refused unbounded work")

    def admit(self, pid: int) -> None:
        (self.path / "cgroup.procs").write_text(str(pid))
        members = (self.path / "cgroup.procs").read_text().split()
        if str(pid) not in members:
            raise ResourceAdmissionError("worker did not enter requested memory cgroup")

    def oom_observed(self) -> bool:
        return parse_oom_events((self.path / "memory.events").read_text())

    @staticmethod
    def _process_identity(pid: int) -> tuple[str, str] | None:
        """Return (state, kernel starttime) without signalling a reused PID."""
        try:
            raw = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise ResourceAdmissionError("cannot inspect owned cgroup process") from exc
        try:
            fields = raw.rsplit(") ", 1)[1].split()
            return fields[0], fields[19]  # /proc stat: state (3), starttime (22)
        except (IndexError, ValueError) as exc:
            raise ResourceAdmissionError("invalid owned process identity") from exc

    def _snapshot_processes(self) -> dict[int, str]:
        """Snapshot direct and nested member identities before cgroup.kill."""
        identities: dict[int, str] = {}
        try:
            proc_files = list(self.path.rglob("cgroup.procs"))
        except FileNotFoundError:
            return identities
        except OSError as exc:
            raise ResourceAdmissionError("cannot enumerate owned cgroup") from exc
        for proc_file in proc_files:
            try:
                members = proc_file.read_text().split()
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise ResourceAdmissionError("cannot read owned cgroup members") from exc
            for raw in members:
                if not raw.isascii() or not raw.isdecimal():
                    raise ResourceAdmissionError("invalid owned cgroup PID")
                pid = int(raw)
                identity = self._process_identity(pid)
                if identity is not None:
                    identities[pid] = identity[1]
        return identities

    @classmethod
    def _all_stopped(cls, members: dict[int, str]) -> bool:
        for pid, starttime in members.items():
            identity = cls._process_identity(pid)
            if (identity is not None and identity[1] == starttime
                    and identity[0] not in {"Z", "X", "x"}):
                return False
        return True

    def cleanup(self) -> None:
        """Signal the private cgroup and confirm observed tasks stopped.

        cgroup.kill is asynchronous: rmdir can succeed before a detached
        descendant finishes receiving SIGKILL. Fail closed if any captured
        process with the same kernel identity is still running after 1 s.
        """
        if self._cleaned:
            return
        deadline = time.monotonic() + 1.0
        tracked: dict[int, str] = {}
        removed = False
        while True:
            if not removed:
                try:
                    populated = parse_populated((self.path / "cgroup.events").read_text())
                    if populated:
                        tracked.update(self._snapshot_processes())
                        (self.path / "cgroup.kill").write_text("1")
                    self.path.rmdir()
                    removed = True
                except FileNotFoundError:
                    removed = True
                except OSError as exc:
                    if time.monotonic() >= deadline:
                        raise ResourceAdmissionError(
                            "could not dispose isolated memory cgroup"
                        ) from exc
            if removed and self._all_stopped(tracked):
                self._cleaned = True
                return
            if time.monotonic() >= deadline:
                raise ResourceAdmissionError(
                    "owned cgroup descendant remained running after cleanup"
                )
            time.sleep(.01)
