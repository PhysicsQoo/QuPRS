#!/usr/bin/env bash
# Shared source-bound native Rustdoc build for preview, dev and signed release.
set -euo pipefail
cd "$(dirname "$0")/.."
root="$(pwd -P)"
# Cargo invokes rustdoc with a package-local cwd, so extension files must
# use absolute paths; every artifact still originates from this checked-out SHA.
cargo rustdoc --locked --manifest-path rust/Cargo.toml -p quprs --lib -- \
  --html-in-header "$root/scripts/rustdoc_quprs_head.html" \
  --extend-css "$root/scripts/rustdoc_navigation.css"
test -s rust/target/doc/quprs/index.html
grep -Fq 'data-quprs-version-selector="true"' rust/target/doc/quprs/index.html
