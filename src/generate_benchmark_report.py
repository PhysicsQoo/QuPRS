import json
from pathlib import Path

BENCHMARK_DIR = Path("./benchmarks")
OUTPUT_FILE = Path("benchmark_report.md")
DEGRADATION_THRESHOLD = 10.0  # percent


def find_latest_benchmark_file(pattern: str) -> Path | None:
    """Find the latest file matching the pattern in the benchmarks directory"""
    try:
        files = sorted(BENCHMARK_DIR.rglob(pattern))
        if files:
            print(f"🔍 Found benchmark file: {files[-1]}")
            return files[-1]
    except FileNotFoundError:
        return None
    return None


def load_data(file_path: Path):
    """Load JSON data from the given path"""
    if not file_path or not file_path.exists():
        raise FileNotFoundError(f"Cannot find input file: {file_path}")
    with open(file_path, "r") as f:
        return json.load(f)


def create_benchmark_map(benchmarks: list) -> dict:
    """Convert benchmark list to a dict keyed by test name for fast lookup"""
    return {bench["name"]: bench for bench in benchmarks}


def format_row(pr_bench, main_bench_map):
    """Format a single row of the table"""
    name = pr_bench.get("name", "n/a")

    pr_stats = pr_bench.get("stats", {})
    pr_mean = pr_stats.get("mean", 0.0)
    rounds = pr_stats.get("rounds", 0)
    stddev = pr_stats.get("stddev", 0.0)

    main_bench = main_bench_map.get(name, {})
    main_stats = main_bench.get("stats", {})
    main_mean = main_stats.get("mean", 0.0)

    delta_pct = ((pr_mean - main_mean) / main_mean * 100) if main_mean else 0.0

    if main_mean == 0.0:
        emoji = "✨"
    elif delta_pct > DEGRADATION_THRESHOLD:
        emoji = "🔴"
    elif delta_pct < -DEGRADATION_THRESHOLD:
        emoji = "🟢"
    else:
        emoji = "🟡"

    return (
        [
            f"{emoji} {name}",
            f"{pr_mean * 1000:.3f} ms",
            f"{main_mean * 1000:.3f} ms",
            f"{delta_pct:+.2f}%",
            f"{stddev * 1000:.3f} ms",
            str(rounds),
        ],
        delta_pct,
        emoji,
    )


def generate_markdown_table(pr_data, main_data):
    """Generate Markdown table and warning messages"""
    pr_benchmarks = pr_data.get("benchmarks", [])
    main_benchmarks = main_data.get("benchmarks", [])

    if not pr_benchmarks:
        return "⚠️ No PR benchmark data found.", []

    main_bench_map = create_benchmark_map(main_benchmarks)

    headers = ["Test", "Mean (PR)", "Mean (Main)", "Δ %", "StdDev", "Rounds"]
    table = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]

    warnings = []
    for bench in pr_benchmarks:
        row, delta_pct, emoji = format_row(bench, main_bench_map)
        table.append("| " + " | ".join(row) + " |")

        if emoji == "🔴":
            warnings.append(
                f"⚠️ `{bench.get('name')}` is {delta_pct:.2f}% slower than `main`"
            )

    return "\n".join(table), warnings


def main():
    try:
        main_file = find_latest_benchmark_file("*main.json")
        pr_file = find_latest_benchmark_file("*pr.json")

        if not main_file or not pr_file:
            raise FileNotFoundError("Could not find both main and PR benchmark files.")

        main_data = load_data(main_file)
        pr_data = load_data(pr_file)

        python_version = pr_data.get("machine_info", {}).get(
            "python_version", "Unknown Python"
        )

        header = f"## 🔬 Benchmark Report\n\n**Python version:** `{python_version}`\n\n"
        table, warnings = generate_markdown_table(pr_data, main_data)

        summary = ""
        if warnings:
            summary += "\n### ⚠️ Performance Regressions Detected\n"
            summary += "\n".join(warnings) + "\n"

        content = header + summary + "\n### 📊 Detailed Comparison\n" + table + "\n"
        OUTPUT_FILE.write_text(content)

        print(f"✅ Benchmark report written to {OUTPUT_FILE}")

    except Exception as e:
        error_message = (
            f"⚠️ Failed to generate benchmark report.\n\n**Error:**\n```\n{e}\n```"
        )
        OUTPUT_FILE.write_text(error_message)
        print(f"❌ Error generating report: {e}")
        # In CI environment, return non-zero exit code to indicate failure
        exit(1)


if __name__ == "__main__":
    main()
