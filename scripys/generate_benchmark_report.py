# scripts/generate_benchmark_report.py
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
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"WARNING: Could not decode JSON from {file_path}. Returning empty data.")
        return {}

    # Create a simple lookup map: { 'test_name': {stats} }
    benchmark_map = {
        (bench.get("group") or bench.get("name")): bench["stats"]
        for bench in data.get("benchmarks", [])
    }
    return benchmark_map


def generate_report(main_file: Path, pr_file: Path, report_file: Path, status: str):
    """
    Generates a markdown report by directly comparing the main and PR benchmark files.
    """
    # --- Step 1: Handle skipped comparison ---
    if status == "false":
        with report_file.open("w", encoding="utf-8") as f:
            f.write("### ⚠️ Benchmark Comparison Skipped\n\n")
            f.write(
                "Could not find a baseline artifact from the `main` branch to compare against.\n"
            )
            f.write(
                "Please ensure the `build-and-save-baseline` job has run successfully on the `main` branch.\n"
            )
        print("✅ Report generated for skipped comparison.")
        return

    # --- Step 2: Load data from both files ---
    main_benchmarks = load_benchmark_data(main_file)
    pr_benchmarks = load_benchmark_data(pr_file)

    if not pr_benchmarks:
        with report_file.open("w", encoding="utf-8") as f:
            f.write("### ❌ Error Generating Report\n\n")
            f.write("Could not find or load benchmark data from the PR run.\n")
        print(f"❌ Error: Could not load data from {pr_file}")
        exit(1)

    # --- Step 3: Process data and prepare for sorting ---
    DEGRADATION_THRESHOLD = 10.0
    processed_results: List[Tuple[float, List[str]]] = []
    regressions = 0
    improvements = 0

    for name, pr_stats in pr_benchmarks.items():
        pr_mean = pr_stats.get("mean", 0.0)
        main_stats = main_benchmarks.get(name)

        main_mean = 0.0
        if main_stats:
            main_mean = main_stats.get("mean", 0.0)

        pr_mean_ms = f"{pr_mean * 1000:.3f} ms"
        main_mean_ms = f"{main_mean * 1000:.3f} ms" if main_stats else "N/A"
        pr_stddev_ms = f"{pr_stats.get('stddev', 0.0) * 1000:.3f} ms"

        emoji = ""
        # Handle new vs. existing benchmarks
        if not main_stats or main_mean == 0:
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

        row_data = [
            f"`{name}`",
            pr_mean_ms,
            main_mean_ms,
            f"{change_str} {emoji}".strip(),
            pr_stddev_ms,
        ]
        # Store absolute change for sorting, handle 'inf' for new tests
        processed_results.append(
            (abs(delta_pct if delta_pct != float("inf") else 0), row_data)
        )

    # --- Step 4: Sort and assemble the final report ---
    processed_results.sort(key=lambda x: x[0], reverse=True)

    markdown_lines = [
        f"### 🔬 Benchmark Report\n\n",
        # Simplified header, as machine info might differ between runs.
        f"### 📈 Executive Summary\n",
        f"* **Significant Regressions (> {DEGRADATION_THRESHOLD}%): {regressions}** 🔴",
        f"* **Significant Improvements (> {DEGRADATION_THRESHOLD}%): {improvements}** 🟢\n",
    ]

    headers = ["Benchmark Name", "PR (Mean)", "Main (Mean)", "Change", "StdDev (PR)"]
    separator = "|:---|---:|---:|---:|---:|"
    table = [f"| {' | '.join(headers)} |", separator]

    if not processed_results:
        table.append("| *No benchmark data found* | | | | |")
    else:
        for _, row_data in processed_results:
            table.append(f"| {' | '.join(row_data)} |")

    markdown_lines.append(
        "### 📊 Detailed Comparison (Sorted by Magnitude of Change)\n"
    )
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
    parser.add_argument("--comparison-status", type=str, required=True)
    args = parser.parse_args()

    generate_report(
        main_file=args.main_file,
        pr_file=args.pr_file,
        report_file=args.report_file,
        status=args.comparison_status,
    )
