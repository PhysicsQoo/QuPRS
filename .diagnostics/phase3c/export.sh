#!/bin/bash
set -euo pipefail
root="$QUPRS_ATTR_ROOT"
mkdir -p "$root"/{work,results}
git fetch origin cc9c53768ef2f69e9b0e5174efddbc5fd97d221a c8336071cc0b731c4ddf966ed1d401653a2d1a17
git submodule update --init GPMC
for variant in A B; do
 sha=cc9c53768ef2f69e9b0e5174efddbc5fd97d221a
 if [ "$variant" = B ]; then sha=c8336071cc0b731c4ddf966ed1d401653a2d1a17; fi
 mkdir -p "$root/work/$variant"
 git archive "$sha" | tar xf - -C "$root/work/$variant"
 git -C GPMC archive a1bda3489e959d3695b6798d327c5a1fc1bed305 | tar xf - -C "$root/work/$variant/GPMC"
done
