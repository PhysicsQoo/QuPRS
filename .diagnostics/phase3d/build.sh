#!/usr/bin/env bash
set -euo pipefail
cd "$QUPRS_ATTR_ROOT"
root="$PWD"
python harness/prepare.py
export CARGO_TARGET_DIR="$root/target"
export CARGO_BUILD_JOBS=4
export RUSTFLAGS="-C debuginfo=0"
mkdir -p "$root/results/bin" "$root/solvers"
for v in A AH B10 BH; do
  cargo build --locked --release --manifest-path "$root/work/$v/rust/Cargo.toml" -p pathsum --example attribution_probe > "$root/results/build-$v.log" 2>&1
  cp "$root/target/release/examples/attribution_probe" "$root/results/bin/$v"
  echo "built plain $v"
done
cp "$root/work/A/src/QuPRS/utils/wmc_tools/ganak" "$root/solvers/ganak"
cp "$root/work/A/src/QuPRS/utils/wmc_tools/gpmc" "$root/solvers/gpmc"
for v in AH BH; do
  cargo test --locked --manifest-path "$root/work/$v/rust/Cargo.toml" --workspace > "$root/results/cargo-test-$v.log" 2>&1
  echo "workspace tests passed $v"
done
for v in A AH B10 BH; do
  python harness/instrument.py "$root/work/$v"
  cargo build --locked --release --manifest-path "$root/work/$v/rust/Cargo.toml" -p pathsum --example attribution_probe > "$root/results/build-diag-$v.log" 2>&1
  cp "$root/target/release/examples/attribution_probe" "$root/results/bin/diag-$v"
  echo "built diagnostic $v"
done
sha256sum "$root"/results/bin/* "$root"/solvers/* "$root"/work/{A,AH,B10,BH}/rust/pathsum/src/reduction.rs > "$root/results/binary-and-source-SHA256SUMS.txt"
