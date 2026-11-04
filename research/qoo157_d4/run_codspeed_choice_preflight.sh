#!/usr/bin/env bash
# QOO-157 science-first CodSpeed choice pilot. Invoked by branch-only Actions.
# Never treat timeout or source-generation failure as a measured speedup.
set -euo pipefail
mkdir -p evidence/cnfs
git rev-parse HEAD > evidence/quprs-head.txt
git rev-parse 'HEAD^{tree}' > evidence/quprs-tree.txt
git rev-parse HEAD:GPMC > evidence/gpmc-submodule.txt
sudo apt-get update
sudo apt-get install -y cmake libgmp-dev libmpfr-dev zlib1g-dev
python -m pip install 'maturin>=1.5,<2' pytest-codspeed==5.0.3
export VIRTUAL_ENV="$(dirname "$(dirname "$(command -v python)")")"
maturin develop --release -E dev

cargo build --manifest-path rust/Cargo.toml --locked --release -p pathsum \
  --example qoo157_export_paper_cnf 2>&1 | tee evidence/exporter-build.log
while IFS='|' read -r case filename pair; do
  if test -z "$case"; then continue; fi
  timeout --signal=TERM --kill-after=5s 90s \
    rust/target/release/examples/qoo157_export_paper_cnf \
    "$case" "benchmarks/MQTBench/$filename" \
    "benchmarks/MQTBench/$pair/$filename" evidence/cnfs \
    > "evidence/$case-export.log" 2>&1 || {
      echo "QOO157_GENERATION_CENSORED=$case" | tee -a evidence/censored.log
    }
done <<'CASES'
grover4_eq|grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm|h,ry,rz,cx
qaoa7_neq|qaoa_nativegates_ibm_qiskit_opt0_7.qasm|qiskit-2.6.1-opt0/Random_Rotation
qpeexact8_eq|qpeexact_nativegates_ibm_qiskit_opt0_8.qasm|h,ry,rz,cx
qft16_eq|qft_nativegates_ibm_qiskit_opt0_16.qasm|h,ry,rz,cx
CASES
find evidence/cnfs -maxdepth 1 -name '*.cnf' -print -exec sha256sum {} \; \
  > evidence/generated-cnf-provenance.txt

git clone --filter=blob:none https://github.com/jm62300/d4.git "$RUNNER_TEMP/qoo157-d4"
git -C "$RUNNER_TEMP/qoo157-d4" checkout --detach \
  be15f91f3e9769e1f5cb175fa27e3eca3a1ea690
test "$(git -C "$RUNNER_TEMP/qoo157-d4" rev-parse HEAD)" = \
  be15f91f3e9769e1f5cb175fa27e3eca3a1ea690
python research/qoo157_d4/precision_variant.py \
  --upstream "$RUNNER_TEMP/qoo157-d4" --evidence evidence
git -C "$RUNNER_TEMP/qoo157-d4" diff --check
git -C "$RUNNER_TEMP/qoo157-d4" diff -- c++/counter/src/Main.cpp \
  > evidence/d4-only-GMP-research.patch
(cd "$RUNNER_TEMP/qoo157-d4/c++/counter" && ./build.sh -j) \
  2>&1 | tee evidence/d4-build.log
test -x "$QOO157_D4_BINARY"
sha256sum "$QOO157_D4_BINARY" > evidence/d4-binary-sha256.txt
python - <<'PY'
import hashlib,json,os,pathlib
binary=pathlib.Path(os.environ["QOO157_D4_BINARY"])
pathlib.Path(os.environ["QOO157_D4_PROVENANCE"]).write_text(json.dumps({
    "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
    "d4_upstream_commit": "be15f91f3e9769e1f5cb175fa27e3eca3a1ea690",
    "gmp_preparse_bits": 426,
    "source_patch_approved_for_research": True,
    "arithmetic_certified": False
},indent=2)+"\n")
PY
python research/qoo157_d4/codspeed_choice_preflight.py \
  --cnf-dir "$QOO157_CNF_DIR" --binary "$QOO157_D4_BINARY" \
  --manifest "$QOO157_D4_PROVENANCE" --source-dir benchmarks/MQTBench \
  --out "$QOO157_PREFLIGHT" --timeout 15 \
  2>&1 | tee evidence/science-preflight.log
