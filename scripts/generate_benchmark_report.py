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


def generate_report(main_file: Path, pr_file: Path, report_file: Path, status: str):
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
            f.write("Could not find or load benchmark data from the PR run.\n")
        print(f"❌ Error: Could not load data from {pr_file}")
        exit(1)

    # --- Step 2: Prepare Header Info ---
    has_baseline = bool(main_benchmarks) and (
        str(status).lower() not in ["false", "0", "no"]
    )

    markdown_lines = [
        "### 🔬 Benchmark Report\n",
    ]

    if not has_baseline:
        markdown_lines.append(
            "> ⚠️ **Note:** No baseline found (first run or branch mismatch). Displaying PR results only.\n"
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
            markdown_lines.append("No significant performance changes detected.")
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
    args = parser.parse_args()

    generate_report(
        main_file=args.main_file,
        pr_file=args.pr_file,
        report_file=args.report_file,
        status=args.comparison_status,
    )
