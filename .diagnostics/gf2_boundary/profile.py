"""Exploratory same-process GF(2) boundary cost, never a release benchmark.

Run from an installed QuPRS development checkout:
    python .diagnostics/gf2_boundary/profile.py --rounds 7 --iterations 200

This compares the unchanged F.sub() against a *test-only* candidate that
parses SymPy expressions, computes canonical GF(2) ANF, and reconstructs the
public SymPy representation. It deliberately includes conversion costs.
Do not infer QuPRS end-to-end performance or numerical correctness from
this microprofile; the official CodSpeed case identities remain unchanged.
"""

import argparse
import gc
import importlib
import importlib.util
import json
import platform
import statistics
import subprocess
import sys
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from benchmarks.codspeed.test_python_core import _anf_absent, _anf_replace


def _test_boundary_bridge():
    """Load a test-only bridge without importing the repository's test package."""
    file_path = ROOT / "test" / "test_gf2_anf_candidate.py"
    module_name = "_quprs_gf2_boundary_experiment"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load isolated GF(2) candidate")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module  # Required by dataclasses for type metadata.
    spec.loader.exec_module(module)
    return module._candidate_public_substitute


def _package_version(name):
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _git_revision(selector):
    return subprocess.check_output(
        ["git", "rev-parse", selector],
        cwd=ROOT,
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def _measure(call, iterations):
    was_enabled = gc.isenabled()
    if was_enabled:
        gc.disable()
    try:
        before = time.perf_counter_ns()
        for _ in range(iterations):
            call()
        return (time.perf_counter_ns() - before) / iterations
    finally:
        if was_enabled:
            gc.enable()


def _case(name, fixture, candidate_bridge, rounds, iterations):
    public_map, target, replacement = fixture()

    def baseline():
        return public_map.sub(target, replacement)

    def candidate():
        return public_map.update_data({
            key: candidate_bridge(value, target, replacement)
            for key, value in public_map.items()
        })

    baseline_result = baseline()
    candidate_result = candidate()
    if baseline_result.bits != candidate_result.bits:
        raise AssertionError(f"{name}: register ordering mismatch")
    for key in baseline_result.bits:
        if (baseline_result[key] != candidate_result[key]
                or type(baseline_result[key]) is not type(candidate_result[key])):
            raise AssertionError(f"{name}: public F value/type mismatch on {key}")
    if repr(baseline_result) != repr(candidate_result):
        raise AssertionError(f"{name}: public F repr differs")

    # Warm both, so parsing/import and first-use effects do not count as CPU hot path.
    for _ in range(12):
        baseline()
        candidate()

    times = {"baseline": [], "gf2_boundary": []}
    operations = {"baseline": baseline, "gf2_boundary": candidate}
    for round_index in range(rounds):
        # Paired ABBA / BAAB balance to mitigate monotonic machine drift.
        order = ("baseline", "gf2_boundary", "gf2_boundary", "baseline")
        if round_index % 2:
            order = tuple(reversed(order))
        for method in order:
            times[method].append(_measure(operations[method], iterations))

    baseline_median = statistics.median(times["baseline"])
    candidate_median = statistics.median(times["gf2_boundary"])
    return {
        "fixture_id": name,
        "iterations_per_sample": iterations,
        "paired_rounds": rounds,
        "baseline_median_ns": round(baseline_median),
        "candidate_median_ns": round(candidate_median),
        "candidate_over_baseline_ratio": round(
            candidate_median / baseline_median, 3
        ),
        "baseline_samples_ns": [round(v) for v in times["baseline"]],
        "candidate_samples_ns": [round(v) for v in times["gf2_boundary"]],
        "public_semantics": "value/type/order/repr parity passed",
        "interpretation": "Exploratory only; no production GF(2) use, no CodSpeed claim",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=7)
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not (1 <= args.rounds <= 100 and 1 <= args.iterations <= 10000):
        parser.error("rounds must be 1..100; iterations must be 1..10000")

    bridge = _test_boundary_bridge()
    results = [
        _case("anf_target_absent", _anf_absent, bridge,
              args.rounds, args.iterations),
        _case("anf_target_present", _anf_replace, bridge,
              args.rounds, args.iterations),
    ]
    payload = {
        "schema": 1,
        "scope": "Python F.sub test-only GF2 public-boundary microprofile",
        "source_sha": _git_revision("HEAD"),
        "tree_sha": _git_revision("HEAD^{tree}"),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "sympy_version": _package_version("sympy"),
        "symengine_version": _package_version("symengine"),
        "quprs_version": _package_version("QuPRS"),
        "measured_using": "sequential same-process ABBA/BAAB perf_counter_ns",
        "solver_invoked": False,
        "production_path_modified": False,
        "claim": "No proven end-to-end acceleration; no numerical solver evidence",
        "cases": results,
    }
    serialized = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")


if __name__ == "__main__":
    main()
