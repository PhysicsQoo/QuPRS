"""Minimal standalone PyO3 worker, without importing the QuPRS Python package.

The embedding Python API already imports Qiskit and resolves solver resources.
This one-shot worker loads the trusted installed extension by its absolute path
and invokes the *same* native PyO3 function, without importing QuPRS.__init__.
The public Python API and scientific result format remain unchanged.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

_PROTOCOL_VERSION = 1
_MAX_REQUEST_BYTES = 64 * 1024 * 1024
_MAX_RESULT_BYTES = 16 * 1024 * 1024


def _load_native_extension(path: str):
    if not isinstance(path, str) or not os.path.isabs(path):
        raise ValueError("worker requires an absolute native extension path")
    p = Path(path)
    if p.suffix not in {".so", ".pyd", ".dylib"} or not p.is_file():
        raise ValueError("worker native extension path is not an installed library")
    spec = importlib.util.spec_from_file_location("_pathsum_rust", str(p))
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load native PyO3 extension")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(_MAX_REQUEST_BYTES + 1)
        if len(raw) > _MAX_REQUEST_BYTES:
            raise ValueError("worker request exceeds IPC limit")
        request = json.loads(raw)
        if not isinstance(request, dict) or request.get("version") != _PROTOCOL_VERSION:
            raise ValueError("worker protocol version mismatch")
        circuits = (request["circuit1"], request["circuit2"])
        if not all(isinstance(x, str) for x in circuits):
            raise TypeError("worker expects two QASM paths or text strings")
        options = request["options"]
        if not isinstance(options, dict):
            raise TypeError("worker options must be an object")
        native = _load_native_extension(request["rust_extension_path"])
        result = native.check_equivalence(
            *circuits,
            method=options["method"],
            strategy=options["strategy"],
            tool_name=options["tool_name"],
            timeout=options["timeout"],
            safe_mode=False,
            wmc_phase_tolerance=options["wmc_phase_tolerance"],
            approximate_distance_tolerance=options["approximate_distance_tolerance"],
            rr_tolerance=options["rr_tolerance"],
            phase_tolerance=options["phase_tolerance"],
            gpmc_precision_digits=options["gpmc_precision_digits"],
        )
        envelope = {"version": _PROTOCOL_VERSION, "ok": True, "result": result}
    except Exception as exc:
        envelope = {
            "version": _PROTOCOL_VERSION,
            "ok": False,
            "error_type": type(exc).__name__,
            "message": str(exc)[:512],
        }
    try:
        data = json.dumps(envelope, allow_nan=False, separators=(",", ":")).encode()
        if len(data) > _MAX_RESULT_BYTES:
            raise RuntimeError("worker result exceeds IPC limit")
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
        return 0
    except Exception as exc:
        print(f"PyO3 worker output failed: {type(exc).__name__}", file=sys.stderr)
        return 125


if __name__ == "__main__":
    sys.exit(main())
