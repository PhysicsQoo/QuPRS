# QOO-157 — d4 GMP precision initialization A/B

Research-only precision subexperiment. It derives from the active QOO-157
complex-WMC PoC but uses an independent branch and scoped CI. No QuPRS
production or solver default changes, no GPMC/Ganak source changes.

Root-cause hypothesis: pinned upstream d4 C++ Counter.cpp sets default
GMP precision to 426 bits AFTER the model count has completed. This is
too late to improve weights or arithmetic allocated during counting.

Experiment:
1. Build original pinned d4, preserve binary SHA.
2. Patch only temporary source checkout to set GMP precision at the start
   of counter(), before semiring and counter construction.
3. Recompile only the C++ counter, preserve exact source diff and binary SHA.
4. Compare the original with experimental 64/128/256/426-bit modes under
   identical near-cancellation CNFs and a Fraction arithmetic oracle.
5. Preserve raw output and report if 1e-16 through 1e-60 residuals survive.

A recovered 1e-40 residual is evidence about the root cause, not an
arithmetic certificate. Report still says NOT_CERTIFIED regardless of A/B
outcome. No CodSpeed inference is allowed from native CI duration.

Key source: research/qoo157_d4/d4_mpf_init_ab.py
Scoped workflow: .github/workflows/qoo157-mpf-init-ab.yml

Before any product integration: real QuPRS f64/MPFR256 source-CNF parity,
EQ/NEQ near-boundary cases, license, platform packaging and paired CodSpeed.
