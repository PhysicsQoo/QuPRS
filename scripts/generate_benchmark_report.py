# scripts/generate_benchmark_report.py
# This script generates a markdown report for benchmark comparison.
import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple


def load_benchmark_data(file_path: Path) -> Dict[str, Dict]:
    """Loads benchmark data and converts it into a dictionary keyed by test name."""
    if not file_path.exists():
        print(f"INFO: Data file not found: {file_path}. Returning empty data.")
        return {}

    try:
        if file_path.stat().st_size == 0:
            return {}
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not data or "benchmarks" not in data:
            return {}
    except (json.JSONDecodeError, OSError):
        print(f"WARNING: Could not decode JSON from {file_path}. Returning empty data.")
        return {}
    benchmark_map = {
        (bench.get("fullname") or bench.get("name")): bench["stats"]
        for bench in data.get("benchmarks", [])
    }
    return benchmark_map


def read_machine_summary(file_path: Path) -> dict:
    """Read bounded provenance fields without treating CPU IDs as comparable."""
    try:
        with file_path.open("r", encoding="utf-8") as stream:
            info = json.load(stream).get("machine_info", {})
            cpu = info.get("cpu", {})
            return {
                "cpu": cpu.get("brand_raw"),
                "python": info.get("python_version"),
                "system": info.get("system"),
                "machine": info.get("machine"),
            }
    except (OSError, ValueError, AttributeError):
        return {}



def assess_provenance(baseline_file: Path, pr_file: Path, expected_main_sha: str):
    """Return all material differences; an incomplete comparison is never a pass."""
    problems = []

    def read_record(path, label):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, ValueError):
            pass
        problems.append(f"{label} provenance missing, invalid or not a JSON object")
        return {}

    baseline = read_record(baseline_file, "Baseline")
    current = read_record(pr_file, "PR")
    if not expected_main_sha:
        problems.append("Expected current main SHA is unavailable")
    elif baseline.get("source_sha") != expected_main_sha:
        problems.append("Baseline source SHA is absent or differs from current main")
    if not current.get("source_sha") or not current.get("checkout_sha"):
        problems.append("PR source or checkout SHA is missing")

    for solver in ("ganak", "gpmc"):
        baseline_tools = baseline.get("solver_binaries")
        pr_tools = current.get("solver_binaries")
        base_entry = baseline_tools.get(solver) if isinstance(baseline_tools, dict) else None
        pr_entry = pr_tools.get(solver) if isinstance(pr_tools, dict) else None
        old_sha = base_entry.get("sha256") if isinstance(base_entry, dict) else None
        new_sha = pr_entry.get("sha256") if isinstance(pr_entry, dict) else None
        if not old_sha or not new_sha:
            problems.append(f"{solver} binary SHA256 missing; solver identity unverified")
        elif old_sha != new_sha:
            problems.append(f"{solver} binary SHA256 differs between baseline and PR")

    for field, label in (
        ("gpmc_submodule_sha", "GPMC submodule"),
        ("cpu_model", "CPU model"),
        ("runner_os", "Runner OS"),
        ("runner_arch", "Runner architecture"),
        ("runner_image", "Runner image"),
        ("runner_image_version", "Runner image version"),
        ("python_version", "Python version"),
        ("rustc", "Rust compiler"),
    ):
        previous = baseline.get(field)
        actual = current.get(field)
        if not previous or not actual:
            problems.append(f"{label} identity missing")
        elif previous != actual:
            problems.append(f"{label} differs between baseline and PR")
    return problems

def generate_report(main_file: Path, pr_file: Path, report_file: Path, status: str,
                    baseline_provenance: Path = Path("main_baseline.provenance.json"),
                    pr_provenance: Path = Path("pr_benchmark.provenance.json"),
                    expected_main_sha: str = "",
                    benchmark_outcome: str = "unknown"):
    """
    Generates a markdown report.
    If main_file is empty/missing, it treats all tests as new.
    """
    # --- Step 1: Load data from both files ---
    main_benchmarks = load_benchmark_data(main_file)
    pr_benchmarks = load_benchmark_data(pr_file)
    if not pr_benchmarks:
        with report_file.open("w", encoding="utf-8") as f:
            f.write("### ❌ Error Generating Report\n\n")
            f.write("> **Performance interpretation: UNVERIFIED — NOT A PASS.**\n\n")
            f.write("Could not find or load benchmark data from the PR run.\n")
        print(f"❌ Error: Could not load data from {pr_file}")
        exit(1)

    # --- Step 2: Prepare Header Info ---
    has_baseline = bool(main_benchmarks) and (
        str(status).lower() not in ["false", "0", "no"]
    )

    markdown_lines = [
        "### 🔬 Benchmark Report\n",
        "> **Informational performance comparison:** the 10% line flags"
        " possible regressions for review but does not fail PR correctness"
        " CI on shared GitHub-hosted runners. A red percentage is not"
        " independently confirmed evidence of a code regression.\n",
    ]

    if has_baseline:
        current_machine = read_machine_summary(pr_file)
        baseline_machine = read_machine_summary(main_file)
        if not current_machine or not baseline_machine:
            markdown_lines.append(
                "> ⚠️ **Runner provenance incomplete** in one or both benchmark"
                " files. Do not interpret the baseline as a matched-hardware"
                " comparison without independent verification.\n"
            )
        else:
            changed = [
                key for key in ("cpu", "python", "system", "machine")
                if baseline_machine.get(key) != current_machine.get(key)
            ]
            if changed:
                fields = ", ".join(changed)
                markdown_lines.append(
                    f"> ⚠️ **Benchmark environment differs:** {fields}."
                    " CPU and toolchain-dependent wall times are not directly"
                    " comparable across unmatched runners.\n"
                )
            else:
                markdown_lines.append(
                    "> Runner CPU/Python/system fields match, but shared-runner"
                    " load and baseline source provenance still require"
                    " independent verification.\n"
                )

    # The benchmark result and provenance must be included in the posted Markdown,
    # not merely printed to the Actions log.
    problems = assess_provenance(baseline_provenance, pr_provenance, expected_main_sha)
    if not has_baseline:
        problems.append("A comparable baseline is absent or comparison was not performed")
    if benchmark_outcome != "success":
        problems.append(f"Benchmark job outcome was {benchmark_outcome!r}; results may be partial")
    if has_baseline:
        missing = set(main_benchmarks) - set(pr_benchmarks)
        extra = set(pr_benchmarks) - set(main_benchmarks)
        if missing or extra:
            problems.append(
                f"Benchmark case coverage differs (baseline-only={len(missing)}, PR-only={len(extra)})"
            )
    if problems:
        markdown_lines.append(
            "> ⚠️ **Performance interpretation: UNVERIFIED — NOT A PASS.**"
            " The following source, environment or execution conditions prevent"
            " an authenticated like-for-like performance conclusion.\n"
        )
        for problem in problems:
            markdown_lines.append(f"> - {problem}")
    else:
        markdown_lines.append(
            "> **Performance interpretation: report-only.** Recorded source and"
            " environment identifiers match, but shared-runner load can still differ."
        )

    if not has_baseline:
        markdown_lines.append(
            "> ⚠️ **No comparable baseline:** Displaying PR results only.\n"
        )

    # --- Step 3: Process data and compare ---
    DEGRADATION_THRESHOLD = 10.0
    processed_results: List[Tuple[float, List[str]]] = []
    regressions = 0
    improvements = 0

    for name, pr_stats in pr_benchmarks.items():
        pr_mean = pr_stats.get("mean", 0.0)
        main_stats = main_benchmarks.get(name)

        main_mean = 0.0
        if has_baseline and main_stats:
            main_mean = main_stats.get("mean", 0.0)
        pr_mean_ms = f"{pr_mean * 1000:.3f} ms"

        if has_baseline and main_stats:
            main_mean_ms = f"{main_mean * 1000:.3f} ms"
        else:
            main_mean_ms = "-"

        pr_stddev_ms = f"{pr_stats.get('stddev', 0.0) * 1000:.3f} ms"

        emoji = ""
        delta_pct = 0.0

        if not has_baseline or not main_stats or main_mean == 0:
            delta_pct = float("inf")
            change_str = "**New ✨**"
        else:
            delta_pct = ((pr_mean - main_mean) / main_mean) * 100
            change_str = f"**{delta_pct:+.2f}%**"

            if delta_pct > DEGRADATION_THRESHOLD:
                emoji = "🔴"
                regressions += 1
            elif delta_pct < -DEGRADATION_THRESHOLD:
                emoji = "🟢"
                improvements += 1

        row_data = [
            f"`{name}`",
            pr_mean_ms,
            main_mean_ms,
            f"{change_str} {emoji}".strip(),
            pr_stddev_ms,
        ]

        sort_key = abs(delta_pct) if delta_pct != float("inf") else 999999.0
        processed_results.append((sort_key, row_data))

    processed_results.sort(key=lambda x: x[0], reverse=True)

    if has_baseline:
        markdown_lines.append(f"#### 📈 Executive Summary")
        if regressions == 0 and improvements == 0:
            if problems:
                markdown_lines.append(
                    "No >10% mean change among available cases; **NOT a validated performance pass**."
                )
            else:
                markdown_lines.append(
                    "No >10% change in recorded means (informational only, not a performance gate)."
                )
        else:
            if regressions > 0:
                markdown_lines.append(
                    f"* **Regressions (> {DEGRADATION_THRESHOLD}%): {regressions}** 🔴"
                )
            if improvements > 0:
                markdown_lines.append(
                    f"* **Improvements (> {DEGRADATION_THRESHOLD}%): {improvements}** 🟢"
                )
        markdown_lines.append("\n")

    headers = ["Benchmark Name", "PR (Mean)", "Baseline", "Change", "StdDev"]
    separator = "|:---|---:|---:|---:|---:|"
    table = [f"| {' | '.join(headers)} |", separator]

    for _, row_data in processed_results:
        table.append(f"| {' | '.join(row_data)} |")

    markdown_lines.append("#### 📊 Detailed Comparison")
    markdown_lines.extend(table)

    report_file.write_text("\n".join(markdown_lines), encoding="utf-8")
    print(f"✅ Benchmark report successfully generated at {report_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a markdown report for benchmark comparison."
    )
    parser.add_argument("--main-file", type=Path, default=Path("main_baseline.json"))
    parser.add_argument("--pr-file", type=Path, default=Path("pr_benchmark.json"))
    parser.add_argument("--report-file", type=Path, default=Path("benchmark_report.md"))
    parser.add_argument("--comparison-status", type=str, default="false")
    parser.add_argument("--baseline-provenance", type=Path, default=Path("main_baseline.provenance.json"))
    parser.add_argument("--pr-provenance", type=Path, default=Path("pr_benchmark.provenance.json"))
    parser.add_argument("--expected-main-sha", type=str, default="")
    parser.add_argument("--benchmark-outcome", type=str, default="unknown")
    args = parser.parse_args()

    generate_report(
        main_file=args.main_file,
        pr_file=args.pr_file,
        report_file=args.report_file,
        status=args.comparison_status,
        baseline_provenance=args.baseline_provenance,
        pr_provenance=args.pr_provenance,
        expected_main_sha=args.expected_main_sha,
        benchmark_outcome=args.benchmark_outcome,
    )
