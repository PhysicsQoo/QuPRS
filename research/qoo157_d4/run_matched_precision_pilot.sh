#!/usr/bin/env bash
# QOO-157: isolated same-decimal precision GPMC-vs-d4 CodSpeed admission.
# Leaves dev/main and the upstream d4 source permanently unchanged.
set -euo pipefail
mkdir -p "$QOO157_EVIDENCE_DIR" "$QOO157_CNF_DIR"
git rev-parse HEAD > "$QOO157_EVIDENCE_DIR/quprs-head.txt"
git rev-parse 'HEAD^{tree}' > "$QOO157_EVIDENCE_DIR/quprs-tree.txt"
git rev-parse HEAD:GPMC > "$QOO157_EVIDENCE_DIR/gpmc-source-submodule.txt"

python -m py_compile \
  research/qoo157_d4/matched_precision_variant.py \
  research/qoo157_d4/matched_precision_adapter.py \
  research/qoo157_d4/matched_precision_preflight.py \
  research/qoo157_d4/test_codspeed_matched_decimal.py

sudo apt-get update
sudo apt-get install -y cmake libgmp-dev libmpfr-dev zlib1g-dev
python -m pip install 'maturin>=1.5,<2' 'pytest-codspeed==5.0.3'
export VIRTUAL_ENV="$(dirname "$(dirname "$(command -v python)")")"
maturin develop --release -E dev

cargo build --manifest-path rust/Cargo.toml --locked --release -p pathsum \
  --example qoo157_export_paper_cnf 2>&1 \
  | tee "$QOO157_EVIDENCE_DIR/quprs-cnf-exporter-build.log"

while IFS='|' read -r case filename pair; do
  if test -z "$case"; then continue; fi
  timeout --signal=TERM --kill-after=5s 90s \
    rust/target/release/examples/qoo157_export_paper_cnf \
    "$case" "benchmarks/MQTBench/$filename" \
    "benchmarks/MQTBench/$pair/$filename" "$QOO157_CNF_DIR" \
    > "$QOO157_EVIDENCE_DIR/$case-export.log" 2>&1 || {
      echo "QOO157_SOURCE_CENSORED=$case" \
        | tee -a "$QOO157_EVIDENCE_DIR/source-generation-censored.log"
    }
done <<'CASES'
grover4_eq|grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm|h,ry,rz,cx
qaoa7_neq|qaoa_nativegates_ibm_qiskit_opt0_7.qasm|qiskit-2.6.1-opt0/Random_Rotation
qpeexact8_eq|qpeexact_nativegates_ibm_qiskit_opt0_8.qasm|h,ry,rz,cx
qft16_eq|qft_nativegates_ibm_qiskit_opt0_16.qasm|h,ry,rz,cx
CASES

find "$QOO157_CNF_DIR" -maxdepth 1 -name '*.cnf' -print -exec sha256sum {} \; \
  > "$QOO157_EVIDENCE_DIR/source-cnf-sha256.txt"

source_root="$RUNNER_TEMP/qoo157-d4-upstream-pinned"
git clone --filter=blob:none https://github.com/jm62300/d4.git "$source_root"
git -C "$source_root" checkout --detach be15f91f3e9769e1f5cb175fa27e3eca3a1ea690
test "$(git -C "$source_root" rev-parse HEAD)" = be15f91f3e9769e1f5cb175fa27e3eca3a1ea690

for d in 30 90; do
  worktree="$RUNNER_TEMP/qoo157-matched-$d-source"
  git -C "$source_root" worktree add --detach "$worktree" \
    be15f91f3e9769e1f5cb175fa27e3eca3a1ea690
  python research/qoo157_d4/matched_precision_variant.py \
    --upstream "$worktree" --evidence "$QOO157_EVIDENCE_DIR" --digits "$d"
  git -C "$worktree" diff --check
  git -C "$worktree" diff -- c++/counter/src/Main.cpp c++/counter/src/Counter.cpp \
    > "$QOO157_EVIDENCE_DIR/d4-matched-$d.patch"
  (
    cd "$worktree/c++/counter"
    ./build.sh -j
  ) > "$QOO157_EVIDENCE_DIR/d4-$d-build.log" 2>&1
  binary="$worktree/c++/counter/build/counter"
  test -x "$binary"
  mkdir -p "$QOO157_BIN_DIR/$d"
  # The executable stays entirely inside $RUNNER_TEMP. Only its SHA,
  # source patch, native output and scientific evidence enter artifacts.
  cp "$binary" "$QOO157_BIN_DIR/$d/counter"
  sha256sum "$QOO157_BIN_DIR/$d/counter" \
    > "$QOO157_EVIDENCE_DIR/d4-$d-binary.sha256"
  "$QOO157_BIN_DIR/$d/counter" -h \
    > "$QOO157_EVIDENCE_DIR/d4-$d-help-precision.log"
  python - "$d" <<'PY'
import hashlib,json,math,os,pathlib,re,sys
d=int(sys.argv[1])
evidence=pathlib.Path(os.environ["QOO157_EVIDENCE_DIR"])
binpath=pathlib.Path(os.environ["QOO157_BIN_DIR"])/str(d)/"counter"
log=(evidence/f"d4-{d}-help-precision.log").read_text()
def get_one(label):
    matches=re.findall(rf"^c o {re.escape(label)} ([0-9]+)$",log,re.MULTILINE)
    if len(matches)!=1: raise SystemExit(f"Missing/duplicate d4 runtime {label}: {log[:1200]}")
    return int(matches[0])
reported=get_one("requested-precision-digits")
actual=get_one("actual-gmp-precision-bits")
target=math.ceil(d*math.log2(10))
if reported!=d or actual<target or actual>target+128:
    raise SystemExit(f"INVALID_GMP_BIT_PROVENANCE digits={d} mpfr={target} actual_gmp={actual}")
v={
    "upstream_commit":"be15f91f3e9769e1f5cb175fa27e3eca3a1ea690",
    "source_patch_isolated":True,
    "binary_sha256":hashlib.sha256(binpath.read_bytes()).hexdigest(),
    "target_decimal_digits":d,
    "gmp_requested_bits":target,
    "gmp_actual_bits":actual,
    "mpfr_reference_bits":target,
    "output_significant_digits":d,
    "precision_certified":False,
    "same_exact_effective_bits":actual==target,
}
(evidence/f"d4-matched-{d}.json").write_text(json.dumps(v,indent=2)+"\n")
print("QOO157_D4_MATCHED_RUNTIME",json.dumps(v))
PY
done

python research/qoo157_d4/matched_precision_preflight.py \
  --cnf-dir "$QOO157_CNF_DIR" \
  --source-dir benchmarks/MQTBench \
  --binary-dir "$QOO157_BIN_DIR" \
  --provenance-dir "$QOO157_EVIDENCE_DIR" \
  --out "$QOO157_MATCHED_REPORT" \
  --timeout 25 2>&1 | tee "$QOO157_EVIDENCE_DIR/matched-scientific-preflight.log"
