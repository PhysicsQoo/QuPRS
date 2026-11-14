# Rebuilding the browser counter with modified dependencies

The source bundle contains `gpmc-patched/`, the original GMP 6.3.0 and MPFR 4.2.1 source tarballs, original copyright/license texts inside those sources, and the browser build script. The script records the clean automated CI recipe. To rebuild with local modifications without downloading/resetting sources, use the supplied source trees directly as below.

Use Emscripten 4.0.23, CMake, Python and make. Choose a new writable scratch directory and an absolute numerical-library installation prefix. Extract the GNU tarballs and edit the desired sources before compiling. Build GMP with:

```sh
emconfigure ./configure --host=wasm32 --disable-assembly --disable-shared --enable-cxx --prefix=/absolute/prefix CFLAGS=-O2 CXXFLAGS=-O2
emmake make -j2
emmake make install
```

Build MPFR against that prefix:

```sh
emconfigure ./configure --host=wasm32 --disable-shared --with-gmp=/absolute/prefix --prefix=/absolute/prefix CFLAGS='-O2 -fPIC'
emmake make -j2
emmake make install
```

Build zlib with `embuilder build zlib`; `em-config CACHE` identifies the Emscripten cache. Configure the supplied `gpmc-patched` tree with `emcmake cmake`, Release mode and `GPMC_STATIC_BUILD=ON`. Set `GPMC_GMP_INCLUDE_DIR`, `GPMC_GMPXX_INCLUDE_DIR`, `GPMC_MPFR_INCLUDE_DIR` to the chosen prefix's `include/`, and the corresponding `GPMC_GMP_LIBRARY`, `GPMC_GMPXX_LIBRARY`, `GPMC_MPFR_LIBRARY` to its `lib/libgmp.a`, `lib/libgmpxx.a`, `lib/libmpfr.a`. Set `ZLIB_INCLUDE_DIR` to the Emscripten cache's `sysroot/include` and `ZLIB_LIBRARY` to `sysroot/lib/wasm32-emscripten/libz.a`. Set `CMAKE_CXX_FLAGS=-sUSE_ZLIB=1` and the executable linker flags:

```text
-sUSE_ZLIB=1 -sALLOW_MEMORY_GROWTH=1 -sMAXIMUM_MEMORY=536870912
-sINITIAL_MEMORY=33554432 -sSTACK_SIZE=16777216 -sSTACK_OVERFLOW_CHECK=2
-sENVIRONMENT=worker -sEXPORTED_RUNTIME_METHODS=FS,callMain -sEXIT_RUNTIME=1
```

Then run `cmake --build /your/build-directory -j2`. The patched project already adds BrowserTime.cc only for Emscripten and emits gpmc.js/gpmc.wasm. Rebuilding/relinking modified numerical libraries is supported; do not run the clean-source cloning/checksum recipe over an intentionally modified tree. GPMC's MPFR complex arithmetic and search are upstream code. The resource shim uses monotonic elapsed wall time and a linear-memory proxy; it is not OS CPU/RSS measurement. Numerical outputs are not certified end-to-end error bounds.
