# Independent six-family Elim cost model comparison (research)

This script accepts the **original PR #60 research Artifact**, independently
checks its archived SHA256SUMS and all timed samples, then evaluates five
models using the full circuit-family as the held-out unit. It deliberately
does not tune a solver, change Reduction behavior or declare speedup.

Usage:

```bash
python -m pip install numpy
python .diagnostics/cost_model_lofo/validate.py \
  --artifact github-actions-artifact-12314136336.zip
```

The source artifact belongs to
[Actions run #39528135089](https://github.com/PhysicsQoo/QuPRS/actions/runs/39528135089)
and is available from GitHub while its original 30-day retention lasts.
The script outputs `model_summary.json`, `model_summary.md` and
`event_medians.jsonl`. SHA256 pinning and family labels make later
comparisons auditable.

**Protocol:** six original families; per-Elim event target is the median
of eight `elapsed_ns` values; 555 event positions, all with
`success=false`. In each fold hold out **every event from one entire
circuit family**, standardize predictors using train-only means and
variances, weight training families equally, use fixed weighted Ridge
regularization (`alpha=0.02`), then score MAE in log nanoseconds. Models:

- constant intercept,
- phase scan size `log1p(L)`,
- simple candidate-plus-scan `log1p(K), log1p(L)`,
- full `log1p(K,L,V,D)`,
- historical `log1p(W_redundant_estimated)`.

This evaluation was designed **after examining earlier pilot statistics**.
It is an exploratory family-grouped comparison, not a prospectively
preregistered external test. Six families (GHZ only 3 events), strongly
collinear counters, clock perturbation and zero successful Elim samples
preclude deploying an adaptive scheduler on these results.

Successful Elim synthetic fixtures from PR #61 are a **different
population** and are never silently mixed with the six real-circuit
failed-Elim examples. They should be analyzed separately and eventually
validated on real workloads that exercise both rule outcomes.
