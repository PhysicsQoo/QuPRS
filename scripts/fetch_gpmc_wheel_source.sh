#!/bin/sh
# Fetch the exact independently released GPMC source for manylinux wheel builds.
# No QuPRS gitlink or nested submodule is required.
set -eu
expected=93cae8dbf2da967e34fea8b7f40bc8f98362e2e0
source_dir=rust/target/gpmc-wheel-source
if ! command -v git >/dev/null 2>&1; then
    if command -v yum >/dev/null 2>&1; then
        yum install -y git
    else
        echo 'git is required to verify GPMC source identity' >&2
        exit 1
    fi
fi
if [ -d "$source_dir/.git" ]; then
    existing=$(git -C "$source_dir" rev-parse HEAD)
    if [ "$existing" = "$expected" ]; then
        echo "PINNED_GPMC_WHEEL_SOURCE_CACHE_PASS source=$expected"
        exit 0
    fi
    echo "Refusing wrong cached GPMC source commit: $existing" >&2
    exit 1
fi
if [ -e "$source_dir" ]; then
    echo 'Unexpected existing GPMC wheel source directory' >&2
    exit 1
fi
mkdir -p rust/target
git clone --depth 1 --branch v1.0.2 --single-branch \
    https://github.com/PhysicsQoo/GPMC.git "$source_dir"
actual=$(git -C "$source_dir" rev-parse HEAD)
test "$actual" = "$expected" || {
    echo "Pinned GPMC source mismatch: $actual != $expected" >&2
    exit 1
}
test -f "$source_dir/CMakeLists.txt"
test -f "$source_dir/flow-cutter-pace17/CMakeLists.txt"
echo "PINNED_GPMC_WHEEL_SOURCE_PASS source=$expected"
