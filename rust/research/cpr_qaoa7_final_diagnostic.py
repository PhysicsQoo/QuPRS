"""One-shot diagnostic for the contradictory PR #319 QAOA7 WallTime observations.
Uses the original historical qaoa7_gpmc case and unmodified measured verifier
revisions. Fresh subprocesses, fixed ABBA/BAAB blocks; never repeat-to-pass.
Monotonic native-host outer elapsed time, NOT CodSpeed Macro or statistical proof.
"""
import hashlib
import json
import os
import statistics
import time
from pathlib import Path
from benchmarks.codspeed.test_pr_solver_walltime import CASES, execute_source_pinned_case

case, = [c for c in CASES if c[0] == "qaoa7_gpmc"]
assert case == ("qaoa7_gpmc", "qaoa_nativegates_ibm_qiskit_opt0_7.qasm", "proportional", "gpmc", False, "rust")
root = Path(os.environ["GITHUB_WORKSPACE"])
fixtures = root / "benchmarks/MQTBench"
for p in (fixtures / case[1], fixtures / "h,ry,rz,cx" / case[1]):
    print("CPR_QAOA7_FIXTURE", p.relative_to(root), hashlib.sha256(p.read_bytes()).hexdigest(), flush=True)
keys = ("verdict", "solver_invoked", "solver", "method", "pair_variant", "qasm_corpus",
        "precision_contract", "effective_rr_tolerance", "effective_distance_tolerance",
        "effective_phase_tolerance", "effective_gpmc_digits", "rr_approximate",
        "wmc_printed_verdict", "wmc_precision_reason", "wmc_numerical_verdict")
rows = []
reference = None
def sample(arm, block, pos, warmup=False):
    global reference
    start = time.perf_counter_ns()
    observation = execute_source_pinned_case(arm, case)
    elapsed = (time.perf_counter_ns() - start) / 1e9
    assert observation["verdict"] == "equivalent" and observation["solver_invoked"] is True
    assert observation["solver"] == "gpmc" and observation["method"] == "hybrid"
    assert observation["pair_variant"] == "transpiled" and observation["qasm_corpus"] == "historical"
    contract = {k: observation.get(k) for k in keys}
    if reference is None:
        reference = contract
    assert contract == reference, (reference, contract)
    row = dict(arm=arm, block=block, position=pos, warmup=warmup, elapsed_s=elapsed, observation=observation)
    print("CPR_QAOA7_TRIAL " + json.dumps(row, sort_keys=True), flush=True)
    if not warmup:
        rows.append(row)
    return elapsed

# Two explicitly unmeasured prewarms; no sample replacement or adaptive stopping.
sample("base", -1, 0, True)
sample("head", -1, 1, True)
pairs = []
for b, order in enumerate(("ABBA", "BAAB", "BAAB", "ABBA")):
    for i in range(0, 4, 2):
        times = {}
        for pos in (i, i+1):
            arm = "base" if order[pos] == "A" else "head"
            times[arm] = sample(arm, b, pos)
        pairs.append(times)
assert len(rows) == 16 and len(pairs) == 8
a = statistics.median(p["base"] for p in pairs)
b = statistics.median(p["head"] for p in pairs)
d = statistics.median(p["head"]-p["base"] for p in pairs)
allowed = max(.05*a, .010)
passed = d <= allowed and b-a <= allowed
result = dict(attempted=16, complete=len(rows), pairs=8, baseline_median_s=a, candidate_median_s=b,
              median_change_pct=100*(b/a-1), paired_delta_median_s=d, allowed_delta_s=allowed,
              pair_deltas_s=[p["head"]-p["base"] for p in pairs],
              status="WITHIN_BUDGET_OBSERVED" if passed else "PERF_BLOCKED",
              prior_negative_observation_retained=True)
print("CPR_QAOA7_DIAGNOSTIC_GATE " + json.dumps(result, sort_keys=True), flush=True)
assert passed, "Frozen QAOA7 screen exceeded; investigate rather than rerun"
