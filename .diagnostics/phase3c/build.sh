#!/bin/bash
set -euo pipefail
cd "${QUPRS_ATTR_ROOT:-/work}"
root="$PWD"
python harness/prepare.py
export CARGO_TARGET_DIR=${root}/target
export CARGO_BUILD_JOBS=4
export RUSTFLAGS='-C debuginfo=0'
for variant in A B1 B3 B5 B10 B20; do
  cargo build --locked --release --manifest-path ${root}/work/$variant/rust/Cargo.toml -p pathsum --example attribution_probe > ${root}/results/build-$variant.log 2>&1
  cp ${root}/target/release/examples/attribution_probe ${root}/results/bin/$variant
  if [ "$variant" = A ]; then
    mkdir -p ${root}/solvers
    cp ${root}/work/A/src/QuPRS/utils/wmc_tools/{ganak,gpmc} ${root}/solvers/
  fi
  echo "built plain $variant"
done
for variant in A B1 B3 B5 B10 B20; do
  python harness/instrument.py ${root}/work/$variant
  cargo build --locked --release --manifest-path ${root}/work/$variant/rust/Cargo.toml -p pathsum --example attribution_probe > ${root}/results/build-diag-$variant.log 2>&1
  cp ${root}/target/release/examples/attribution_probe ${root}/results/bin/diag-$variant
  echo "built diagnostic $variant"
done
sha256sum ${root}/results/bin/* ${root}/solvers/* > ${root}/results/binary-SHA256SUMS
