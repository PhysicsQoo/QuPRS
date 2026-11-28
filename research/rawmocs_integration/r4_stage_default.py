"""Modify only the disposable R3b source tree, never the production default."""
from pathlib import Path
import sys,re
e=Path(sys.argv[1])
for name in ("wasm-tree.txt","no-feature-tree.txt"):
    s=(e/name).read_text()
    assert not re.search(r"\b(rawmocs|rug|gmp-mpfr-sys) v",s),name
print("R4_FEATURE_ISOLATION_TREE_PASS")
p=Path("src/QuPRS/interface/load_qiskit.py")
s=p.read_text()
old='    backend: str = "python",'
assert s.count(old)==1
p.write_text(s.replace(old,'    backend: str = "rust",',1))
