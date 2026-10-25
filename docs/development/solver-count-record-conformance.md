# Contradictory native weighted counts

Both Ganak and GPMC have independent selected adapters. A normal single
finite count continues to parse identically, and repeated *identical* count
records are accepted. If stdout contains two different valid count records,
both Python and Rust now reject the observation as ambiguous instead of
silently selecting the first or last record. Invalid/nonfinite counts, missing
counts, process failure and timeouts retain their existing fail-closed
supervision paths.

This is an input-validation conformance hardening step, not a modification to
native solver arithmetic, PathSum encoding, source angles, Reduction-first
Hybrid, or any WMC classification tolerance. A disagreement or ambiguous
stdout is not proof of quantum circuit equivalence.
