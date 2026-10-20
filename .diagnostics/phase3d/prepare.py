#!/usr/bin/env python3
"""Inspect exact immutable dev/candidate source exports and add unchanged probe."""
import os
import shutil
from pathlib import Path

root = Path(os.environ["QUPRS_ATTR_ROOT"])
before = "if !self.p.get_used_vars().contains(&var) {"
after = "if !used_vars.contains(&var) {"
for variant in ("A", "AH"):
    dst = root / "work" / variant
    p = dst / "rust/pathsum/src/reduction.rs"
    content = p.read_text()
    if variant == "A":
        assert content.count(before) == 1 and after not in content, "Baseline Elim source mismatch"
    else:
        assert content.count(after) == 1 and before not in content, "Candidate Elim source mismatch"
        assert content.count("let used_vars = self.p.get_used_vars();") == 1, "Hoist must be unique"
    ex = dst / "rust/pathsum/examples"
    ex.mkdir(parents=True, exist_ok=True)
    shutil.copy(root / "harness/probe.rs", ex / "attribution_probe.rs")
    print("SOURCE VERIFIED", variant, flush=True)
