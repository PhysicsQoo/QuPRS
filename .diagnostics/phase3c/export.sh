#!/bin/bash
set -euo pipefail
root="$QUPRS_ATTR_ROOT"
mkdir -p "$root"/{work,results}
git fetch origin 006821e8cd93cceaee703512047d330194386275 a58210fe957673b0aaeb8a64c418142b085e1817
git submodule update --init GPMC
for variant in A AH; do
  if [ "$variant" = A ]; then sha=006821e8cd93cceaee703512047d330194386275; else sha=a58210fe957673b0aaeb8a64c418142b085e1817; fi
  mkdir -p "$root/work/$variant/GPMC"
  git archive "$sha" | tar xf - -C "$root/work/$variant"
  gpmc_sha="$(git ls-tree "$sha" GPMC | awk '{print $3}')"
  test -n "$gpmc_sha"
  git -C GPMC archive "$gpmc_sha" | tar xf - -C "$root/work/$variant/GPMC"
  printf '%s %s %s\n' "$variant" "$sha" "$gpmc_sha" | tee -a "$root/results/source-commits.txt"
done
