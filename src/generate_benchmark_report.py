import json
import argparse
from pathlib import Path

def generate_report(comparison_file: Path, report_file: Path, status: str):
    """
    Generates a markdown report from a pytest-benchmark comparison JSON file.

    This script reads a single, pre-compared JSON file and formats it into
    a human-readable markdown table. It also handles cases where the
    comparison was skipped.
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
        exit(1) # Exit with an error code to make the CI step fail

    # --- Step 3: Create the markdown report from the data ---
    machine_info = data.get("machine_info", {})
    python_version = machine_info.get("python_version", "N/A")
    
    markdown_lines = [
        f"### 🔬 Benchmark Report\n",
        f"**Python version:** `{python_version}`\n"
    ]
    
    # Create the table header
    headers = ["Benchmark Name", "PR (Mean)", "Main (Mean)", "Change (%)", "StdDev (PR)"]
    separator = "|:---|---:|---:|---:|---:|"
    table = [header, separator]
    
    warnings = []

    if not data.get("benchmarks"):
        table.append("| *No benchmark data found* | | | | |")
    else:
        # Populate the table rows
        for bench in data["benchmarks"]:
            name = bench["group"] if bench.get("group") else bench["name"]
            
            # pytest-benchmark conveniently provides both runs in the "runs" list
            # The baseline run is the one used in the `--benchmark-compare` argument
            main_stats = bench["runs"][0]["stats"]
            pr_stats = bench["runs"][1]["stats"]

            main_mean = main_stats["mean"]
            pr_mean = pr_stats["mean"]

            # Format numbers in milliseconds for readability
            pr_mean_ms = f"{pr_mean * 1000:.3f} ms"
            main_mean_ms = f"{main_mean * 1000:.3f} ms"
            pr_stddev_ms = f"{pr_stats['stddev'] * 1000:.3f} ms"

            # Calculate and format the percentage change
            if main_mean > 0:
                delta_pct = ((pr_mean - main_mean) / main_mean) * 100
                change_str = f"**{delta_pct:+.2f}%**"
            else: # Handle new benchmarks where main_mean is 0
                delta_pct = float('inf')
                change_str = "**New ✨**"

            # Add color for visual indication
            DEGRADATION_THRESHOLD = 10.0
            if delta_pct > DEGRADATION_THRESHOLD:
                change_str += " 🔴"
                warnings.append(f"⚠️ `{name}` is {delta_pct:.2f}% slower than `main`.")
            elif delta_pct < -DEGRADATION_THRESHOLD:
                change_str += " 🟢"

            # Add a row to the table
            row = f"| `{name}` | {pr_mean_ms} | {main_mean_ms} | {change_str} | {pr_stddev_ms} |"
            table.append(row)
            
    # Assemble the final report content
    if warnings:
        markdown_lines.append("\n### ⚠️ Performance Regressions Detected\n")
        markdown_lines.extend(warnings)

    markdown_lines.append("\n### 📊 Detailed Comparison\n")
    markdown_lines.extend(table)
    
    # Write the report to the markdown file
    report_file.write_text("\n".join(markdown_lines), encoding='utf-8')

    print(f"✅ Benchmark report successfully generated at {report_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a markdown report for benchmark comparison.")
    parser.add_argument(
        "--comparison-file",
        type=Path,
        default=Path("comparison_results.json"),
        help="Path to the pytest-benchmark JSON comparison output file."
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        default=Path("benchmark_report.md"),
        help="Path to the output markdown report file."
    )
    parser.add_argument(
        "--comparison-status",
        type=str,
        required=True,
        help="Status of the comparison step ('true' or 'false')."
    )
    args = parser.parse_args()
    
    generate_report(
        comparison_file=args.comparison_file,
        report_file=args.report_file,
        status=args.comparison_status
    )