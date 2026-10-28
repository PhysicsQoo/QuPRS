#!/usr/bin/env bash
set -euo pipefail

root="$(pwd)"
out="$root/ganak-ab-evidence"
mkdir -p "$out"
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT

repo_dir="$scratch/ganak"
git clone -q --depth 1 --branch release/v2.8.0 \
  https://github.com/meelgroup/ganak.git "$repo_dir"
release_sha="b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281"
actual_sha="$(git -C "$repo_dir" rev-parse HEAD)"
test "$actual_sha" = "$release_sha"

printf 'ganak_upstream=%s\n' "$actual_sha" > "$out/provenance.txt"

# Use detached, SHA-pinned siblings, avoiding Ganak CMake's moving-branch
# FetchContent fallback for these four dependencies.
while read -r dir url revision; do
  git init -q "$scratch/$dir"
  git -C "$scratch/$dir" remote add origin "$url"
  git -C "$scratch/$dir" fetch -q --depth 1 origin "$revision"
  git -C "$scratch/$dir" -c advice.detachedHead=false checkout -q --detach FETCH_HEAD
  observed="$(git -C "$scratch/$dir" rev-parse HEAD)"
  test "$observed" = "$revision"
  printf '%s=%s\n' "$dir" "$observed" >> "$out/provenance.txt"
done <<'DEPENDENCIES'
cryptominisat https://github.com/msoos/cryptominisat.git ed61e2170ab8d86a69c7cd99ae09059414fa0e0a
arjun https://github.com/meelgroup/arjun.git 6055b495309714240f3ac85e60df10d1f93f8017
approxmc https://github.com/meelgroup/ApproxMC.git ccbadb1cc2a365d98b6844dcbb1c00efa2f81470
treedecomp https://github.com/meelgroup/treedecomp.git 0495b40c220b0b97a0d7c8e8d86480b4060476a8
DEPENDENCIES

flint_url="https://github.com/flintlib/flint/releases/download/v3.2.0-rc1/flint-3.2.0-rc1.tar.gz"
curl -fsSL --retry 3 "$flint_url" -o "$scratch/flint.tar.gz"
sha256sum "$scratch/flint.tar.gz" >> "$out/flint-archive-sha256.txt"
tar -xzf "$scratch/flint.tar.gz" -C "$scratch"
(
  cd "$scratch/flint-3.2.0-rc1"
  ./configure --enable-static --enable-shared
  make -j4
  sudo make install
)
sudo ldconfig
pkg-config --modversion flint >> "$out/provenance.txt"
printf 'cmake_version=%s\n' "$(cmake --version | head -n 1)" >> "$out/provenance.txt"
printf 'compiler_version=%s\n' "$(c++ --version | head -n 1)" >> "$out/provenance.txt"

cmake -S "$repo_dir" -B "$repo_dir/build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=ON \
  -DSTATIC_BINARY=OFF \
  -DENABLE_TESTING=OFF
cmake --build "$repo_dir/build" --target ganak-bin --parallel 4
# The Ganak executable is the ganak-bin CMake target; ganak is libganak.
export LD_LIBRARY_PATH="$repo_dir/build/lib:/usr/local/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
test -x "$repo_dir/build/ganak"
cp "$repo_dir/build/ganak" "$out/ganak-baseline"
sha256sum "$out/ganak-baseline" >> "$out/binary-sha256.txt"
"$out/ganak-baseline" --version > "$out/baseline-version.txt"
ldd "$out/ganak-baseline" > "$out/baseline-ldd.txt"

# This is the ONLY intentional source change from the compiled baseline.
# Dynamic decimal precision: 128 bits => 41 significant digits;
# 256 bits => 80 significant digits. Preserve original result markers.
python3 - "$repo_dir/src/main.cpp" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
source = path.read_text()
old_complex = r'mpfr_printf("c s exact %s %.8Re + %.8Rei\n", mpfr_prec_name(mpfr_precision), od->real, od->imag);'
old_real = r'mpfr_printf("c s exact %s %.8Re\n", mpfr_prec_name(mpfr_precision), od->val);'
assert source.count(old_complex) == 1, "Unexpected Ganak complex count printer source"
assert source.count(old_real) == 1, "Unexpected Ganak real count printer source"
complex_replacement = (
    'const int output_digits = (mpfr_precision * 30103 + 99999) / 100000 + 2;\n'
    '        mpfr_printf("c s exact %s %.*Re + %.*Rei\\n", '
    'mpfr_prec_name(mpfr_precision), output_digits - 1, od->real, '
    'output_digits - 1, od->imag);'
)
real_replacement = (
    'const int output_digits = (mpfr_precision * 30103 + 99999) / 100000 + 2;\n'
    '        mpfr_printf("c s exact %s %.*Re\\n", '
    'mpfr_prec_name(mpfr_precision), output_digits - 1, od->val);'
)
path.write_text(source.replace(old_complex, complex_replacement).replace(old_real, real_replacement))
PY
git -C "$repo_dir" diff --check
git -C "$repo_dir" diff -- src/main.cpp > "$out/ganak-printer.patch"
test "$(git -C "$repo_dir" diff --name-only)" = "src/main.cpp"
test -s "$out/ganak-printer.patch"
sha256sum "$out/ganak-printer.patch" >> "$out/provenance-sha256.txt"

cmake --build "$repo_dir/build" --target ganak-bin --parallel 4
cp "$repo_dir/build/ganak" "$out/ganak-candidate"
sha256sum "$out/ganak-candidate" >> "$out/binary-sha256.txt"
"$out/ganak-candidate" --version > "$out/candidate-version.txt"
ldd "$out/ganak-candidate" > "$out/candidate-ldd.txt"
python3 .diagnostics/tolerance_calibration/ganak_printer_ab.py \
  --baseline "$out/ganak-baseline" --candidate "$out/ganak-candidate" \
  --output "$out/observations.json"
python3 - "$out/observations.json" <<'PY'
import json
import sys
data = json.load(open(sys.argv[1]))
print("Gan ak paired observations:", len(data["observations"]))
print("Summary:", json.dumps(data["summary"], sort_keys=True))
PY
