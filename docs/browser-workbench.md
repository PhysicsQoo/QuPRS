# Browser workbench

The optional static workbench compares restricted unitary QASM2/3 circuits locally using the Rust verifier and the real MPFR GPMC counter, both compiled to WebAssembly. It accepts uploads, supports Hybrid/WMC/reduction modes, shows the projective Hilbert–Schmidt distance `sqrt(1 - |Tr(U†V)|² / 4^n)` (global phase ignored), and downloads a JSON result. Smaller distances mean closer circuits. Numerical acceptance and a displayed zero are not exact-equivalence certificates; reduction may accept within tolerance without computing a distance.

## Build and validate

**Website CI → Browser WASM** runs the reusable **Browser workbench** tests, building both components from source and checking native arithmetic and real Chromium behavior. PR jobs have read-only repository permissions and cannot publish. No binary artifact or workflow run from a personal fork is required. GNU sources are fetched from their original project hosts with pinned SHA256 values; GPMC is pinned at 93cae8dbf2da967e34fea8b7f40bc8f98362e2e0.

To inspect a build, download the `tested-browser-site` artifact and serve it over HTTP (not file URLs). All runtime URLs are relative, so the same files work at a repository root or under `playground/`. The build includes complete corresponding solver/GNU sources, original notices and [dependency rebuild instructions](../scripts/web/REBUILD.md). Browser requests are limited to200seconds and512MiB linear memory per WASM module; this is not a cap on total browser memory.

For a local source build, install Rust with the wasm32-unknown-unknown target, wasm-bindgen-cli0.2.100, Emscripten4.0.23, CMake, GMP/MPFR development libraries, Python and Node. Use `QUPRS_SOLVER_PROVISION=external` for the Rust build. The workflow records the exact `cargo`, `wasm-bindgen`, counter build and artifact assembly commands; `scripts/web/build-counter.sh` builds both native and WASM counters. Tests additionally use the checksum-pinned native GANAK fixture and Playwright1.65.1. Generated binaries belong in build artifacts, not source control.

## How Rust source changes reach the Playground

The browser **does not run Rust source files directly**: `quprs-web` compiles the current native `rust/quprs/` core and `rust/web/` adapter to `quprs_web_bg.wasm`; the separate original GPMC counter is also built as WASM. There are **two separate update tracks**:

| Changed source / event | Automatic result | Public route |
| --- | --- | --- |
| Reviewed `dev` push touching `rust/quprs/**`, `rust/web/**`, `rust/Cargo.toml`, `rust/Cargo.lock`, `web/**` or `scripts/web/**` | Build from the exact `dev` commit, rerun Rust native tests, core+GPMC WASM and Chromium/native differential checks, then publish **only on success** | `/playground/dev/` |
| A successfully published and verified **signed stable release tag** | Rebuild from that immutable tag commit, check the release/registry provenance and public JS/Worker/WASM hashes, stage a new immutable version, then promote the stable alias | `/playground/vX.Y.Z/` and `/playground/` |
| PR without merge, failed CI/build/Pages validation, or unrelated Rust-only CLI/Python changes | No validated Playground version is promoted | Previous published content remains usable |

The workflow boundary is source-controlled in `.github/workflows/website-deploy.yml` (single trusted `dev` push routing for all site subtrees), `browser-workbench.yml` (actual native and WASM rebuild), and `website-publish.yml` (source SHA, live hash and isolated Pages write). `scripts/site/test_website_impact.py` contains a regression check ensuring those Rust paths and build/publish links remain connected. `source-sha.txt` in each published version identifies the exact Rust checkout used; `/playground/versions.json` records the signed-stable snapshot identities.

**Why not update stable on every Rust change?** Stable means the result of the full signed-release admission and must remain reproducible. Development Rust fixes appear on `/playground/dev/` after verified merges; they reach stable only on the next signed published version. This prevents mixing newly compiled Rust with older certified version assets and prevents a failing experiment from replacing the public default.

## Publish on the repository owner's GitHub Pages

After a **reviewed merge to protected `dev`**, the shared `Website Dev Deploy` workflow routes changed source paths to the applicable Homepage, Playground and `/docs/dev` publishers. Changes affecting Rust/WebAssembly source, web assets, or their build scripts trigger actual Rust WASM, GMP/MPFR GPMC WASM and browser/native differential tests before Playground publication. Homepage and Docs/Rustdoc use their own validated reusable jobs within the same dev-push workflow. Pull-request Website CI remains read-only and cannot publish. A manual `workflow_dispatch` remains available solely for recovery and validation, not as a routine release step.

The publish jobs do **not** select an Actions deployment Environment: the verified source updates only the existing `gh-pages` branch, then explicitly requests and validates GitHub's legacy Pages build. Existing `github-pages` Environment branch restrictions remain unchanged; no new Environment, readiness variable, expanded branch allowlist, or manual approval is required for normal publication. A stale run whose source SHA no longer matches the current trusted branch head cannot publish. This assumes changes have already passed the repository's protected `dev` merge gate; automation does not substitute for that review.

The versioned Playground publication policy separates stable releases from development previews:

- `/playground/` is the **latest successfully published and verified stable** release after its first stable-alias promotion; `stable-release.json` records its signed release tag and exact source SHA.
- `/playground/vX.Y.Z/` is an immutable, source-pinned stable release snapshot; `/playground/versions.json` lists the qualified versions. Existing snapshots cannot be replaced by another build with differing bytes.
- `/playground/dev/` is the latest successfully validated protected-`dev` build. It is not an official release; dev pushes cannot overwrite stable aliases or historical snapshots.
- A signed official stable tag, successful PyPI/crates.io GitHub release workflow, independent Browser/native/Chromium validation and public asset-hash checks are required before automatic stable promotion. Snapshot staging and stable-alias promotion are separate GitHub Pages revisions; the older working alias is retained unless the new version has passed the staging gate. An unsuccessful post-promotion Pages deployment triggers a guarded rollback attempt.

No new GitHub Environment or authorized publishing branch is added. The existing `gh-pages` serialization and legacy Pages build continue to be used. The first historical `v0.17.0` snapshot must be rebuilt and independently admitted from its original signed release; prior dev publication does not establish its provenance. The older unversioned route may remain dev-backed until that first verified promotion occurs.

The existing repository Pages source must be the `gh-pages` branch, root directory, as used by the documentation publisher. The publication job stages **only `playground/`**. It preserves root index, `docs/`, previews, CNAME and every other existing Pages path. The shared Pages write lock serializes cooperating publishers; an unexpected concurrent update makes the non-force push fail without overwriting unrelated changes. The workflow explicitly requests a Pages build using its narrowly scoped Pages permission, waits for completion and verifies the public source SHA and key JS/WASM hashes. A GITHUB_TOKEN branch push alone does not trigger a Pages build. There is no force push or change to package/release workflows.

For PhysicsQoo/QuPRS, the resulting URL is:

<https://physicsqoo.github.io/QuPRS/playground/>

Other forks use `https://OWNER.github.io/REPOSITORY/playground/`. If a repository uses GitHub Actions artifact-based Pages instead of a gh-pages branch, merge the validated `playground/` directory into that existing Pages artifact; do not replace the owner's complete site. The workflow does not change repository Pages settings.

Native entry points retain their default subprocess behavior. Browser support is additive through the non-published `quprs-web` workspace member and `browser-transport` feature. Native clocks resolve to the standard Instant implementation. The browser transports exact rational phase descriptors to the original C MPFR input-weight bridge inside GPMC (upstream96–1024-bit policy), then replays the upstream numerical classifier against the matching prepared problem. Counting uses30 decimal digits. These are working precisions, not interval error bounds.
