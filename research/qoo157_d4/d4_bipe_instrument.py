"""Research-only diagnostics in a scratch patched d4@be15f91 38-digit source.

Instruments *after* parsing and around BiPe preprocessing, without altering
the formula, protected-variable logic, solver method or numerical output.
The instrumented d4 must not be shipped or mistaken for pinned upstream.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

PIN = "be15f91f3e9769e1f5cb175fa27e3eca3a1ea690"
NEEDLE = (
    "  preprocManager.run(formula.nbVar, formula.clauses, projected, varProtected,\n"
    "                     optionPreproc);"
)
MARK = "QOO157_BIPE"
INSTRUMENT = """  auto qoo157_active_vars = [&formula]() {
    std::set<int> used;
    for (const auto& clause : formula.clauses)
      for (int lit : clause) used.insert(std::abs(lit));
    return used.size();
  };
  std::cout << "c QOO157_BIPE before vars=" << formula.nbVar
            << " clauses=" << formula.clauses.size()
            << " active=" << qoo157_active_vars()
            << " protected=" << varProtected.size()
            << " weight_entries=" << formula.weightMap.size()
            << " projected=" << projected.size() << "\\n";
  preprocManager.run(formula.nbVar, formula.clauses, projected, varProtected,
                     optionPreproc);
  std::cout << "c QOO157_BIPE after vars=" << formula.nbVar
            << " clauses=" << formula.clauses.size()
            << " active=" << qoo157_active_vars()
            << " protected=" << varProtected.size()
            << " weight_entries=" << formula.weightMap.size()
            << " projected=" << projected.size() << "\\n";"""


def patch(root: Path, evidence: Path) -> dict:
    rev = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    if rev != PIN:
        raise ValueError("d4 upstream revision mismatch")
    file = root / "c++/counter/src/Main.cpp"
    raw = file.read_text()
    if raw.count(NEEDLE) != 1 or MARK in raw or raw.count("#include <string>") != 1:
        raise ValueError("Unrecognized original d4 preprocessing source anchor")
    modified = raw.replace("#include <string>", "#include <string>\n#include <set>\n#include <cstdlib>")
    modified = modified.replace(NEEDLE, INSTRUMENT)
    file.write_text(modified)
    evidence.mkdir(parents=True, exist_ok=True)
    manifest = {
        "upstream_sha": rev,
        "instrumentation_only": True,
        "numeric_patch_already_applied_required": True,
        "source_file": "c++/counter/src/Main.cpp",
        "before_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "after_sha256": hashlib.sha256(modified.encode()).hexdigest(),
        "markers": ["QOO157_BIPE before", "QOO157_BIPE after"],
        "arithmetic_certified": False,
    }
    (evidence / "d4-bipe-scratch-instrumentation.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    return manifest


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(patch(a.source, a.evidence)))
