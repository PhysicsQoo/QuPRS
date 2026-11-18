#!/usr/bin/env bash
set -euo pipefail
ROOT=$(pwd)
BUILD="${RUNNER_TEMP:-$ROOT/.browser-build}/quprs-counter"
PREFIX="$ROOT/.browser-prefix"
OUT="$ROOT/web/engines"
mkdir -p "$BUILD" "$PREFIX" "$OUT/sources"
# Fetch original, checksum-pinned GNU sources independently of any fork.
mkdir -p "$BUILD/downloads"
curl --fail --location --retry 3 https://ftp.gnu.org/gnu/gmp/gmp-6.3.0.tar.xz --output "$BUILD/downloads/gmp-6.3.0.tar.xz"
curl --fail --location --retry 3 https://www.mpfr.org/mpfr-4.2.1/mpfr-4.2.1.tar.xz --output "$BUILD/downloads/mpfr-4.2.1.tar.xz"
python3 - "$BUILD" <<'PYCODE'
import hashlib,pathlib,sys
p=pathlib.Path(sys.argv[1])/'downloads'
for name,sha in [('gmp-6.3.0.tar.xz','a3c2b80201b89e68616f4ad30bc66aee4927c3ce50e33929ca819d5c43538898'),('mpfr-4.2.1.tar.xz','277807353a6726978996945af13e52829e3abd7a9a5b7fb2793894e18f1fcbb2')]:
 assert hashlib.sha256((p/name).read_bytes()).hexdigest()==sha,(name,'GNU source checksum mismatch')
PYCODE
cp "$BUILD/downloads/gmp-6.3.0.tar.xz" "$BUILD/downloads/mpfr-4.2.1.tar.xz" "$OUT/sources/"
cd "$BUILD"
if [ ! -f "$PREFIX/lib/libgmp.a" ]; then
 tar xf downloads/gmp-6.3.0.tar.xz
 (cd gmp-6.3.0 && emconfigure ./configure --disable-assembly --disable-shared --enable-cxx --host=wasm32 --prefix="$PREFIX" CFLAGS=-O2 CXXFLAGS=-O2 && emmake make -j2 && emmake make install)
fi
if [ ! -f "$PREFIX/lib/libmpfr.a" ]; then
 tar xf downloads/mpfr-4.2.1.tar.xz
 (cd mpfr-4.2.1 && emconfigure ./configure --host=wasm32 --disable-shared --with-gmp="$PREFIX" --prefix="$PREFIX" CFLAGS='-O2 -fPIC' && emmake make -j2 && emmake make install)
fi
git clone https://github.com/PhysicsQoo/GPMC.git gpmc
git -C gpmc checkout 93cae8dbf2da967e34fea8b7f40bc8f98362e2e0
cp "$ROOT/scripts/web/BrowserTime.cc" gpmc/utils/BrowserTime.cc
cp "$ROOT/scripts/web/PhaseWeights.hpp" gpmc/utils/PhaseWeights.hpp
cp "$ROOT/rust/quprs/native/mpfr_weight_bridge.c" gpmc/utils/QuPRSPhaseBridge.c
python3 - "$BUILD/gpmc" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);f=p/'core/Main.cc';s=f.read_text().replace('#include <errno.h>','#include <errno.h>\n#include \"utils/PhaseWeights.hpp\"').replace('string filename = (argc == 1) ? \"\" : argv[1];','string filename = (argc == 1) ? \"\" : argv[1];\n        if (!filename.empty()) filename=quprs_source_weights(filename);').replace('\t\tSetSigAct();','\t\t#ifndef __EMSCRIPTEN__\n\t\tSetSigAct();\n\t\t#endif').replace('#if defined(_WIN32)\n','#if defined(_WIN32) || defined(__EMSCRIPTEN__)\n');f.write_text(s)
f=p/'CMakeLists.txt';s=f.read_text()+'''\nenable_language(C)
target_sources(gpmc-bin PRIVATE utils/QuPRSPhaseBridge.c)
if(CMAKE_SYSTEM_NAME STREQUAL "Emscripten")
 target_sources(gpmc-bin PRIVATE utils/BrowserTime.cc)
 set_target_properties(gpmc-bin PROPERTIES SUFFIX ".js")
endif()\n''';f.write_text(s)
PY
embuilder build zlib
SYSROOT="$(em-config CACHE)/sysroot"
emcmake cmake -S gpmc -B wasm-build -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_BUILD_TYPE=Release -DGPMC_STATIC_BUILD=ON -DGPMC_GMP_INCLUDE_DIR="$PREFIX/include" -DGPMC_GMPXX_INCLUDE_DIR="$PREFIX/include" -DGPMC_MPFR_INCLUDE_DIR="$PREFIX/include" -DGPMC_GMP_LIBRARY="$PREFIX/lib/libgmp.a" -DGPMC_GMPXX_LIBRARY="$PREFIX/lib/libgmpxx.a" -DGPMC_MPFR_LIBRARY="$PREFIX/lib/libmpfr.a" -DZLIB_INCLUDE_DIR="$SYSROOT/include" -DZLIB_LIBRARY="$SYSROOT/lib/wasm32-emscripten/libz.a" -DCMAKE_CXX_FLAGS='-sUSE_ZLIB=1' -DCMAKE_EXE_LINKER_FLAGS='-sUSE_ZLIB=1 -sALLOW_MEMORY_GROWTH=1 -sMAXIMUM_MEMORY=536870912 -sINITIAL_MEMORY=33554432 -sSTACK_SIZE=16777216 -sSTACK_OVERFLOW_CHECK=2 -sENVIRONMENT=worker -sEXPORTED_RUNTIME_METHODS=FS,callMain -sEXIT_RUNTIME=1'
cmake --build wasm-build -j2
cp wasm-build/gpmc.js wasm-build/gpmc.wasm "$OUT/"
cmake -S gpmc -B native-build -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_BUILD_TYPE=Release
cmake --build native-build -j2
cp native-build/gpmc "$OUT/native-gpmc"
git -C gpmc diff > "$OUT/sources/GPMC-browser.patch"
mkdir -p source-bundle/scripts/web
cp "$ROOT/scripts/web/build-counter.sh" "$ROOT/scripts/web/BrowserTime.cc" "$ROOT/scripts/web/PhaseWeights.hpp" source-bundle/scripts/web/
cp -R gpmc source-bundle/gpmc-patched
rm -rf source-bundle/gpmc-patched/.git
cp downloads/gmp-6.3.0.tar.xz downloads/mpfr-4.2.1.tar.xz source-bundle/
cp "$ROOT/LICENSE.md" source-bundle/QuPRS-LICENSE.md
tar czf "$OUT/sources/gpmc-mpfr-browser-source.tar.gz" source-bundle
python3 - "$OUT" <<'PY'
import pathlib,hashlib,json,sys
p=pathlib.Path(sys.argv[1]);files=[p/'gpmc.js',p/'gpmc.wasm',p/'native-gpmc',*sorted((p/'sources').iterdir())]
manifest={'repository':'https://github.com/PhysicsQoo/GPMC','revision':'93cae8dbf2da967e34fea8b7f40bc8f98362e2e0','version':'v1.0.2','arithmetic':'Original QuPRS source-phase bridge (96–1024-bit selected input weights) and MPFR complex counting; numeric estimate, not an end-to-end certificate','emscripten':'4.0.23','wasm_memory_max_mib':512,'cpp_stack_mib':16,'resource_clock':'worker-local elapsed wall time and linear-memory proxy; not OS CPU/RSS','sha256':{str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}}
(p/'PROVENANCE.json').write_text(json.dumps(manifest,indent=2)+'\n')
PY
