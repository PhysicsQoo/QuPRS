#!/usr/bin/env bash
# Shared source-bound native Rustdoc build for preview, dev and signed release.
set -euo pipefail
cd "$(dirname "$0")/.."
cargo rustdoc --locked --manifest-path rust/Cargo.toml -p quprs --lib -- \
  --html-in-header scripts/rustdoc_quprs_head.html \
  --extend-css scripts/rustdoc_navigation.css
test -s rust/target/doc/quprs/index.html
grep -Fq 'data-quprs-version-selector="true"' rust/target/doc/quprs/index.html
