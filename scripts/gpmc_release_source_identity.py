"""Exact published GPMC source identity for benchmark/CI provenance."""
from pathlib import Path
import re

MANIFEST = Path(__file__).resolve().parents[1] / "src/QuPRS/utils/gpmc-release.txt"


def source_commit() -> str:
    markers = [line[2:] for line in MANIFEST.read_text(encoding="ascii").splitlines()
               if line.startswith("# ") and re.fullmatch(r"[a-f0-9]{40}", line[2:])]
    if len(markers) != 1:
        raise ValueError("Missing or ambiguous pinned GPMC release source SHA")
    return markers[0]
