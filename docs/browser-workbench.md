# Browser workbench

The optional static workbench compares restricted unitary QASM2/3 circuits locally using the Rust verifier and the real MPFR GPMC counter, both compiled to WebAssembly. It accepts uploads, supports Hybrid/WMC/reduction modes, shows the projective Hilbert–Schmidt distance `sqrt(1 - |Tr(U†V)|² / 4^n)` (global phase ignored), and downloads a JSON result. Smaller distances mean closer circuits. Numerical acceptance and a displayed zero are not exact-equivalence certificates; reduction may accept within tolerance without computing a distance.

## Build and validate

**Website CI → Browser WASM** runs the reusable **Browser workbench** tests, building both components from source and checking native arithmetic and real Chromium behavior. PR jobs have read-only repository permissions and cannot publish. No binary artifact or workflow run from a personal fork is required. GNU sources are fetched from their original project hosts with pinned SHA256 values; GPMC is pinned at 93cae8dbf2da967e34fea8b7f40bc8f98362e2e0.

To inspect a build, download the `tested-browser-site` artifact and serve it over HTTP (not file URLs). All runtime URLs are relative, so the same files work at a repository root or under `playground/`. The build includes complete corresponding solver/GNU sources, original notices and [dependency rebuild instructions](../scripts/web/REBUILD.md). Browser requests are limited to200seconds and512MiB linear memory per WASM module; this is not a cap on total browser memory.

For a local source build, install Rust with the wasm32-unknown-unknown target, wasm-bindgen-cli0.2.100, Emscripten4.0.23, CMake, GMP/MPFR development libraries, Python and Node. Use `QUPRS_SOLVER_PROVISION=external` for the Rust build. The workflow records the exact `cargo`, `wasm-bindgen`, counter build and artifact assembly commands; `scripts/web/build-counter.sh` builds both native and WASM counters. Tests additionally use the checksum-pinned native GANAK fixture and Playwright1.65.1. Generated binaries belong in build artifacts, not source control.

## Publish on the repository owner's GitHub Pages

After the dedicated publisher is available on the default branch, an owner can run **Actions → Browser Playground Publish → Run workflow** and select **publish=true**. Pull requests are validation-only through Website CI, and publishing is isolated in this separate manual workflow. Publishing is limited to explicit manual runs on `main`/`dev` and requires all source and browser build/test jobs to pass. The source publishing job does **not** select an Actions deployment Environment: it updates only the existing `gh-pages` branch, then requests GitHub's legacy Pages build. The existing `github-pages` Environment branch restrictions stay unchanged; no new Environment, readiness variable or expanded deployment-branch allowlist is needed. Manual dispatch is the publication authorization and does not provide a separate Environment reviewer-approval step.

The existing repository Pages source must be the `gh-pages` branch, root directory, as used by the documentation publisher. The publication job stages **only `playground/`**. It preserves root index, `docs/`, previews, CNAME and every other existing Pages path. A concurrent docs update makes the ordinary push fail rather than overwrite that update; rerun after it finishes. The workflow explicitly requests a Pages build using its narrowly scoped Pages permission, waits for completion and verifies the public source SHA and key JS/WASM hashes. A GITHUB_TOKEN branch push alone does not trigger a Pages build. There is no force push or change to package/release workflows.

For PhysicsQoo/QuPRS, the resulting URL is:

<https://physicsqoo.github.io/QuPRS/playground/>

Other forks use `https://OWNER.github.io/REPOSITORY/playground/`. If a repository uses GitHub Actions artifact-based Pages instead of a gh-pages branch, merge the validated `playground/` directory into that existing Pages artifact; do not replace the owner's complete site. The workflow does not change repository Pages settings.

Native entry points retain their default subprocess behavior. Browser support is additive through the non-published `quprs-web` workspace member and `browser-transport` feature. Native clocks resolve to the standard Instant implementation. The browser transports exact rational phase descriptors to the original C MPFR input-weight bridge inside GPMC (upstream96–1024-bit policy), then replays the upstream numerical classifier against the matching prepared problem. Counting uses30 decimal digits. These are working precisions, not interval error bounds.
