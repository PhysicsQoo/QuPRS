#!/usr/bin/env python3
"""Create 2x2 immutable counterfactual exports (main/PR x original/hoist)."""
import os
import shutil
from pathlib import Path

root = Path(os.environ["QUPRS_ATTR_ROOT"])
work = root / "work"
hoist_from = """for &var in reducible_vars {
            if !self.p.get_used_vars().contains(&var) {"""
hoist_to = """let used_vars = self.p.get_used_vars();
        for &var in reducible_vars {
            if !used_vars.contains(&var) {"""
for variant, base, hoist in [
    ("A", "A", False),
    ("AH", "A", True),
    ("B10", "B", False),
    ("BH", "B", True),
]:
    dst = work / variant
    src = work / base
    if src != dst:
        if dst.exists():
            raise RuntimeError(f"Refusing existing diagnostic export {dst}")
        shutil.copytree(src, dst)
    if hoist:
        p = dst / "rust/pathsum/src/reduction.rs"
        text = p.read_text()
        assert text.count(hoist_from) == 1, "Unexpected Elim loop: stop rather than guessing"
        p.write_text(text.replace(hoist_from, hoist_to, 1))
    ex = dst / "rust/pathsum/examples"
    ex.mkdir(parents=True, exist_ok=True)
    shutil.copy(root / "harness/probe.rs", ex / "attribution_probe.rs")
    print(variant, "base", base, "hoisted", hoist, flush=True)
