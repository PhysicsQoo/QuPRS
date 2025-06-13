import json
from pathlib import Path

INPUT_FILE = Path("comparison_results.json")
OUTPUT_FILE = Path("benchmark_report.md")
DEGRADATION_THRESHOLD = 10.0  # percent

def load_data():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Cannot find input: {INPUT_FILE}")
    with open(INPUT_FILE, "r") as f:
        return json.load(f)

def format_row(bench):
    name = bench.get("name", "n/a")
    pr_stats = bench.get("stats", {})
    ref_stats = bench.get("reference_stats", {})

    pr_mean = pr_stats.get("mean", 0.0)
    ref_mean = ref_stats.get("mean", 0.0)
    delta_pct = ((pr_mean - ref_mean) / ref_mean * 100) if ref_mean else 0.0
    rounds = pr_stats.get("rounds", 0)
    stddev = pr_stats.get("stddev", 0.0)

    # Performance emoji indicator
    if delta_pct > DEGRADATION_THRESHOLD:
        emoji = "🔴"
    elif delta_pct < 0:
        emoji = "🟢"
    else:
        emoji = "🟡"

    return [
        f"{emoji} {name}",
        f"{pr_mean * 1000:.3f} ms",
        f"{ref_mean * 1000:.3f} ms",
        f"{delta_pct:+.2f}%",
        f"{stddev * 1000:.3f} ms",
        str(rounds)
    ], delta_pct, emoji

def generate_markdown_table(data):
    benchmarks = data.get("benchmarks", [])
    if not benchmarks:
        return "⚠️ No benchmark data found."

    headers = ["Test", "Mean (PR)", "Mean (Main)", "Δ %", "StdDev", "Rounds"]
    table = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]

    warnings = []
    for bench in benchmarks:
        row, delta_pct, emoji = format_row(bench)
        table.append("| " + " | ".join(row) + " |")

        if emoji == "🔴":
            warnings.append(f"⚠️ `{bench.get('name')}` is {delta_pct:.2f}% slower than `main`")

    return "\n".join(table), warnings

def main():
    try:
        data = load_data()
        python_version = data.get("machine_info", {}).get("python_version", "Unknown Python")

        header = f"## 🔬 Benchmark Report\n\n**Python version:** `{python_version}`\n\n"
        table, warnings = generate_markdown_table(data)

        summary = ""
        if warnings:
            summary += "\n### ⚠️ Performance Regressions Detected\n"
            summary += "\n".join(warnings) + "\n"

        content = header + summary + "\n### 📊 Detailed Comparison\n" + table + "\n"
        OUTPUT_FILE.write_text(content)

        print(f"✅ Benchmark report written to {OUTPUT_FILE}")

    except Exception as e:
        OUTPUT_FILE.write_text("⚠️ Failed to generate benchmark report.\n")
        print(f"❌ Error generating report: {e}")

if __name__ == "__main__":
    main()
