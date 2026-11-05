"""QOO-157 P8 scratch-only preproc-only exit for same-binary official CodSpeed.

Apply only after pinned 38d, existing BiPe output diagnostics and P7 residual
dump injection. Not a production mode. Same source and compiled executable
for preproc-only and full solver benchmark variants.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ANCHOR = "  if (formula.quantifications[0].size()) {\n    options.optionSpecManager"
INJECTION = r'''  // QOO157 P8: preprocessor-only research control, unavailable unless env set.
  if (const char* qoo157_preproc_only = std::getenv("QOO157_PREPROC_ONLY")) {
    if (std::string(qoo157_preproc_only) != "1") {
      std::cerr << "c QOO157_PREPROC_ONLY_INVALID\n";
      return 2;
    }
    std::cout << "c QOO157_PREPROC_ONLY_DONE\n";
    return EXIT_SUCCESS;
  }

'''

def patch(root: Path, evidence: Path) -> dict:
    path=root/"c++/counter/src/Main.cpp"
    old=path.read_text()
    if old.count(ANCHOR)!=1 or "QOO157_RESIDUAL_DUMP" not in old or "QOO157_BIPE after vars=" not in old:
        raise ValueError("Required source-pinned prec/BiPe/residual preflight anchors absent")
    if "QOO157_PREPROC_ONLY" in old:
        raise ValueError("Already patched")
    new=old.replace(ANCHOR,INJECTION+ANCHOR)
    path.write_text(new)
    evidence.mkdir(parents=True, exist_ok=True)
    data={"only_change":"env-gated skip before calling counter() after complete BiPe",
          "before_sha256":hashlib.sha256(old.encode()).hexdigest(),
          "after_sha256":hashlib.sha256(new.encode()).hexdigest(),
          "production_patched":False, "no_solver_algorithm_change":True}
    (evidence/"d4-p8-preproc-only-source.json").write_text(json.dumps(data,indent=2)+"\n")
    return data

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--evidence",type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(patch(a.root,a.evidence)))
