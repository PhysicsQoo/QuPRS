"""QOO-157 read-only formula dump after pinned d4 BiPe, scratch only.

Patch applied AFTER matched_precision_variant.py and d4_bipe_instrument.py,
so every existing WMC/prec/active-variable diagnostic is retained unchanged.
Environment-gated output executes only during untimed science analysis.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path

ANCHOR = "  // Reflect the (possibly narrowed) projected set back into the formula"
INSTRUMENT = """  // QOO-157 experimental canonical residual export; NEVER enabled in CodSpeed.
  if (const char* qoo157_dump = std::getenv("QOO157_RESIDUAL_DUMP")) {
    std::ofstream out(qoo157_dump);
    if (!out) { std::cerr << "QOO157_DUMP_ERROR\\n"; std::exit(1); }
    out << "v " << formula.nbVar << "\\n";
    out << "c " << formula.clauses.size() << "\\n";
    out << "p";
    for (int v : projected) out << " " << v;
    out << "\\n";
    for (const auto& [lit, weight] : formula.weightMap)
      out << "w " << lit << " " << weight << "\\n";
    for (const auto& clause : formula.clauses) {
      out << "l";
      for (int lit : clause) out << " " << lit;
      out << "\\n";
    }
  }
"""


def patch(root: Path, evidence: Path) -> dict:
    path = root / "c++/counter/src/Main.cpp"
    old = path.read_text()
    if old.count(ANCHOR) != 1 or old.count("QOO157_BIPE after vars=") != 1:
        raise ValueError("Unrecognized instrumented pinned d4 source")
    if "QOO157_RESIDUAL_DUMP" in old or old.count("#include <filesystem>") != 1:
        raise ValueError("Unrecognized or already patched d4 source")
    new = old.replace("#include <filesystem>", "#include <filesystem>\n#include <fstream>")
    new = new.replace(ANCHOR, INSTRUMENT + "\n" + ANCHOR)
    path.write_text(new)
    evidence.mkdir(parents=True, exist_ok=True)
    info = {
        "source_patch_only": True,
        "enabled_only_by_env_var": "QOO157_RESIDUAL_DUMP",
        "original_source_sha256": sha256(old.encode()).hexdigest(),
        "patched_source_sha256": sha256(new.encode()).hexdigest(),
        "numerics_unchanged_intended_not_certified": True,
        "used_for_codspeed": False,
    }
    (evidence / "d4-residual-dump-source.json").write_text(
        json.dumps(info, indent=2) + "\n")
    return info


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    v = p.parse_args()
    print(json.dumps(patch(v.source, v.evidence)))
