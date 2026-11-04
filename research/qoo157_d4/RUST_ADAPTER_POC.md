# QOO-157 Rust d4 opt-in proof-of-concept

Research-only independent branch. Experimental-d4 is an off-by-default Cargo feature: no changes to default GPMC/Ganak choices or their printed-count parser, no bundled executable or public release support.

When enabled, the d4 adapter uses QuPRS' existing Rust WMC generator and process supervisor, requires explicit QUPRS_D4_PATH, QUPRS_D4_SHA256, QUPRS_D4_UPSTREAM_SHA, QUPRS_D4_SOURCE_PATCH_ACK=1 and QUPRS_D4_PREPARSE_BITS (128–2048). Missing or stale provenance fails closed; operator-supplied metadata is not a trusted arithmetic certificate. The native counter is built from pinned upstream be15f91f3e9769e1f5cb175fa27e3eca3a1ea690 and receives an ephemeral GMP-before-parser patch only in CI scratch space.

Feature-only tests guard strict d4 arb float/int decimal parsing, zero/nonzero, malformed counts, and incumbent adapter behavior. The native example exercises actual WmcOnly EQ/NEQ via the external subprocess; default-feature compilation guards nonexperimental behavior. No timings in CI are CodSpeed performance evidence.

**License blocker:** upstream root LICENSE contains LGPL-2.1 text, while specific counter sources (Main.cpp, Counter.cpp and MpzComplexSemiring.hpp) explicitly say GPL-3.0-or-later. Do not bundle or statically link d4 into wheels before source-specific copyright and distribution obligations are resolved.

Remaining: exact same-CNF Python/Rust verdict parity including near thresholds, proof of source f64/MPFR input precision, CI timeout/cleanup, upstream-maintained precision configuration, cross-platform support and same-SHA CodSpeed comparisons. All count observations remain uncertified for internal GMP arithmetic error.

Scoped workflow: .github/workflows/qoo157-d4-rust-optin.yml.
