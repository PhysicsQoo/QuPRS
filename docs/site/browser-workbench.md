# Browser Playground

The optional QuPRS Browser Playground compares supported unitary OpenQASM circuits without installing Python or Rust. Its public entry point is [Browser Playground](https://physicsqoo.github.io/QuPRS/playground/). The stable publication policy uses immutable versioned links such as `/playground/v0.17.0/` and keeps the separately validated development preview at `/playground/dev/`. The default URL is promoted to the latest stable only after a signed release, browser/native validation and live asset checks; consult `/playground/stable-release.json` and `/playground/versions.json` to distinguish verified stable publication from the initial dev-backed route.

See the [Browser Playground build and deployment guide](https://github.com/PhysicsQoo/QuPRS/blob/dev/docs/browser-workbench.md) for exact-source checks and availability requirements.

## How it works

The application downloads static HTML, JavaScript and WebAssembly (WASM) assets from GitHub Pages. The verification itself runs **locally on the user's CPU**:

1. Load or paste two restricted unitary OpenQASM 2/3 circuits.
2. QuPRS Rust, compiled to WASM, parses the circuits and applies Path-sum reduction.
3. If the selected method requires weighted counting, the browser sends the prepared CNF to a disposable Web Worker running the original GPMC counter compiled with Emscripten, GMP and MPFR.
4. The count is replayed into the Rust verifier, which produces the result and the optional projective-distance estimate.

The application does not upload the QASM source to a remote verification service. Downloading site assets still requires network access. GPU acceleration and a remote compute backend are not part of this interface.

## Methods and result interpretation

The interface supports **Hybrid (reduction + WMC)**, **Reduction rules**, and **WMC-only** modes for its supported circuit subset. Measurements and arbitrary OpenQASM programs are not supported.

When available, the displayed estimate uses the projective Hilbert–Schmidt metric:

\[
D_{\mathrm{proj}}(U,V)=\sqrt{1-\frac{|\mathrm{Tr}(U^\dagger V)|^2}{4^n}}.
\]

This metric ignores a common global phase. An approximate numerical distance, including a displayed zero, is **not** a certified distance interval or independent proof of exact equality. A reduction-tolerance decision can be returned without a numerical distance; an inconclusive result must not be presented as equivalence.

## Execution limits and reproducibility

- The page applies a **200-second wall-clock watchdog** and can stop the verification and counter Workers. This is a browser-side termination mechanism, not a guarantee that every computation will finish.
- Each compiled WASM module has a maximum **512 MiB linear memory** bound. That is **not a cap on total browser memory**: JavaScript heaps, multiple Workers and browser overhead need additional RAM.
- MPFR/GPMC precision settings improve numerical evaluation but are not an end-to-end rigorous error certificate.
- Native and browser verification should be compared using the same QASM source, method, strategy and tolerances. Browser WASM timings are not interchangeable with native benchmark timings.

For build dependencies, source licenses, testing and optional deployment, consult the [workbench build guide](https://github.com/PhysicsQoo/QuPRS/blob/dev/docs/browser-workbench.md).
