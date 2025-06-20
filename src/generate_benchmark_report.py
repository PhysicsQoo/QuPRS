import json
import argparse
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any, Tuple

def generate_report(comparison_file: Path, report_file: Path, status: str):
    """
    Generates a markdown report from a pytest-benchmark comparison JSON file.
    This version correctly handles the flat data structure produced by
    'pytest --benchmark-compare' and safely checks for 'None' type parameters.
    """
    # --- Step 1: Handle the case where the comparison was skipped ---
    if status == 'false':
        with report_file.open('w', encoding='utf-8') as f:
            f.write("### ⚠️ Benchmark Comparison Skipped\n\n")
            f.write("Could not find a baseline artifact from the `main` branch to compare against.\n")
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

    # --- Step 3: Group benchmark runs by name (★ KEY FIX HERE ★) ---
    grouped_benchmarks = defaultdict(dict)
    for bench in data.get("benchmarks", []):
        name = bench.get("group") or bench.get("name")
        param = bench.get("param") # This can be a string, or it can be None

        # Safely check if 'param' is a string before doing the 'in' operation.
        if param and "main_baseline" in param:
            grouped_benchmarks[name]["main"] = bench
        else:
            # This handles both PR runs with no params (param is None)
            # and PR runs that might have their own params.
            grouped_benchmarks[name]["pr"] = bench
    
    # --- Step 4: Process the grouped data and prepare for sorting ---
    DEGRADATION_THRESHOLD = 10.0
    processed_benchmarks: List[Tuple[float, List[str]]] = []
    regressions = 0
    improvements = 0

    for name, runs in grouped_benchmarks.items():
        pr_run = runs.get("pr")
        main_run = runs.get("main")

        if not pr_run:
            continue
        
        pr_stats = pr_run.get("stats", {})
        pr_mean = pr_stats.get("mean", 0.0)
        
        main_mean = 0.0
        if main_run and "stats" in main_run:
            main_mean = main_run["stats"].get("mean", 0.0)

        pr_mean_ms = f"{pr_mean * 1000:.3f} ms"
        main_mean_ms = f"{main_mean * 1000:.3f} ms" if main_run else "N/A"
        pr_stddev_ms = f"{pr_stats.get('stddev', 0.0) * 1000:.3f} ms"

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
        
        row_data = [f"`{name}`", pr_mean_ms, main_mean_ms, f"{change_str} {emoji}".strip(), pr_stddev_ms]
        processed_benchmarks.append((abs(delta_pct if delta_pct != float('inf') else 0), row_data))

    # --- Step 5: Sort and assemble the final report ---
    processed_benchmarks.sort(key=lambda x: x[0], reverse=True)
    
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
    parser.add_argument("--comparison-file", type=Path, default=Path("comparison_results.json"))
    parser.add_argument("--report-file", type=Path, default=Path("benchmark_report.md"))
    parser.add_argument("--comparison-status", type=str, required=True)
    args = parser.parse_args()
    
    generate_report(
        comparison_file=args.comparison_file,
        report_file=args.report_file,
        status=args.comparison_status
    )