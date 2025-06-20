import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple

def generate_report(comparison_file: Path, report_file: Path, status: str):
    """
    Generates a markdown report from a pytest-benchmark comparison JSON file.

    This enhanced version includes an executive summary and sorts the results
    by the magnitude of performance change to highlight the most significant differences.
    """
    # --- Step 1: Handle the case where the comparison was skipped ---
    if status == 'false':
        with report_file.open('w', encoding='utf-8') as f:
            f.write("### ⚠️ Benchmark Comparison Skipped\n\n")
            f.write("Could not find a baseline artifact from the `main` branch to compare against.\n")
            f.write("Please ensure the `build-and-save-baseline` job has run successfully on the `main` branch.\n")
        print("✅ Report generated for skipped comparison.")
        return

    # --- Step 2: Load the comparison data ---
    try:
        with comparison_file.open('r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        with report_file.open('w', encoding='utf-8') as f:
            f.write("### ❌ Error Generating Report\n\n")
            f.write(f"Could not read or parse the comparison file: `{comparison_file}`.\n\n")
            f.write(f"**Error details:**\n```\n{e}\n```")
        print(f"❌ Error: Could not read or parse {comparison_file}")
        exit(1)

    # --- Step 3: Process data and prepare for sorting ---
    DEGRADATION_THRESHOLD = 10.0
    processed_benchmarks: List[Tuple[float, List[str]]] = []
    regressions = 0
    improvements = 0

    if data.get("benchmarks"):
        for bench in data["benchmarks"]:
            name = bench["group"] if bench.get("group") else bench["name"]
            
            main_run = next((r for r in bench["runs"] if r["name"].endswith("main_baseline]")), None)
            pr_run = next((r for r in bench["runs"] if not r["name"].endswith("main_baseline]")), None)

            if not main_run or not pr_run:
                main_run = bench["runs"][0]
                pr_run = bench["runs"][1]

            main_mean = main_run["stats"]["mean"]
            pr_mean = pr_run["stats"]["mean"]

            pr_mean_ms = f"{pr_mean * 1000:.3f} ms"
            main_mean_ms = f"{main_mean * 1000:.3f} ms"
            pr_stddev_ms = f"{pr_run['stats']['stddev'] * 1000:.3f} ms"

            if main_mean > 0:
                delta_pct = ((pr_mean - main_mean) / main_mean) * 100
                change_str = f"**{delta_pct:+.2f}%**"
            else:
                delta_pct = float('inf')
                change_str = "**New ✨**"

            emoji = ""
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
            # Store the absolute change for sorting, along with the formatted row
            processed_benchmarks.append((abs(delta_pct), row_data))

    # --- Step 4: Sort benchmarks by the magnitude of change (descending) ---
    processed_benchmarks.sort(key=lambda x: x[0], reverse=True)

    # --- Step 5: Assemble the final markdown report ---
    machine_info = data.get("machine_info", {})
    python_version = machine_info.get("python_version", "N/A")
    
    markdown_lines = [
        f"### 🔬 Benchmark Report\n",
        f"**Python version:** `{python_version}`\n",
        f"### 📈 Executive Summary\n",
        f"* **Significant Regressions (> {DEGRADATION_THRESHOLD}%): {regressions}** 🔴",
        f"* **Significant Improvements (> {DEGRADATION_THRESHOLD}%): {improvements}** 🟢\n"
    ]
    
    headers = ["Benchmark Name", "PR (Mean)", "Main (Mean)", "Change", "StdDev (PR)"]
    separator = "|:---|---:|---:|---:|---:|"
    table = [f"| {' | '.join(headers)} |", separator]

    if not processed_benchmarks:
        table.append("| *No benchmark data found* | | | | |")
    else:
        for _, row_data in processed_benchmarks:
            table.append(f"| {' | '.join(row_data)} |")
    
    markdown_lines.append("### 📊 Detailed Comparison (Sorted by Magnitude of Change)\n")
    markdown_lines.extend(table)
    
    report_file.write_text("\n".join(markdown_lines), encoding='utf-8')
    print(f"✅ Benchmark report successfully generated at {report_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a markdown report for benchmark comparison.")
    parser.add_argument(
        "--comparison-file", type=Path, default=Path("comparison_results.json"),
        help="Path to the pytest-benchmark JSON comparison output file."
    )
    parser.add_argument(
        "--report-file", type=Path, default=Path("benchmark_report.md"),
        help="Path to the output markdown report file."
    )
    parser.add_argument(
        "--comparison-status", type=str, required=True,
        help="Status of the comparison step ('true' or 'false')."
    )
    args = parser.parse_args()
    
    generate_report(
        comparison_file=args.comparison_file,
        report_file=args.report_file,
        status=args.comparison_status
    )