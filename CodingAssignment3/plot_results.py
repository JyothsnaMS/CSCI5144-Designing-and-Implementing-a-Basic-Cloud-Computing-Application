"""Turns benchmark_results/summary.csv into a table and two graphs for the report.

Usage: python plot_results.py            (needs: pip install matplotlib)

For every number of stores and every phase it takes the MEDIAN over the repeated runs,
so one unlucky run doesn't decide the result. Writes:
  benchmark_results/results_table.md   table to paste into the README / report
  benchmark_results/throughput.png     throughput by number of stores
  benchmark_results/latency_p95.png    p95 latency by number of stores
"""
import csv
import os
import statistics
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RESULTS_DIR = "benchmark_results"
PHASES = ["PUT", "GET", "DELETE"]
COLORS = {"PUT": "#2C6FBB", "GET": "#F28E2B", "DELETE": "#7A7A7A"}


def load(path):
    with open(path) as f:
        rows = [r for r in csv.DictReader(f) if int(r["stores"]) > 0]
    if not rows:
        sys.exit(f"No rows with --stores 1, 2 or 3 in {path}. Run the benchmarks first.")
    return rows


def medians(rows):
    """{(stores, phase): {metric: median over runs, 'runs': count}}"""
    groups = {}
    for r in rows:
        groups.setdefault((int(r["stores"]), r["phase"]), []).append(r)
    table = {}
    for key, group in groups.items():
        table[key] = {m: statistics.median(float(r[m]) for r in group)
                      for m in ("throughput_ops_s", "avg_ms", "p50_ms", "p95_ms", "p99_ms")}
        table[key]["runs"] = len(group)
        table[key]["errors"] = sum(int(r["errors"]) + int(r["mismatches"]) for r in group)
    return table


def write_table(table, stores, path):
    lines = ["| Stores | Phase | Runs | Throughput (ops/s) | Avg (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |",
             "|---:|---|---:|---:|---:|---:|---:|---:|---:|"]
    for n in stores:
        for phase in PHASES:
            if (n, phase) in table:
                t = table[(n, phase)]
                lines.append(f"| {n} | {phase} | {t['runs']} | {t['throughput_ops_s']:.1f} | {t['avg_ms']:.2f} | "
                             f"{t['p50_ms']:.2f} | {t['p95_ms']:.2f} | {t['p99_ms']:.2f} | {t['errors']} |")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


def bar_chart(table, stores, metric, ylabel, title, path):
    fig, ax = plt.subplots(figsize=(7, 4))
    width = 0.25
    for j, phase in enumerate(PHASES):
        values = [table.get((n, phase), {}).get(metric, 0) for n in stores]
        xs = [i + (j - 1) * width for i in range(len(stores))]
        bars = ax.bar(xs, values, width, label=phase, color=COLORS[phase])
        ax.bar_label(bars, fmt="%.0f" if metric == "throughput_ops_s" else "%.1f", fontsize=8, padding=2)
    ax.set_xticks(range(len(stores)), [f"{n} store{'s' if n > 1 else ''}" for n in stores])
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left", pad=28)
    ax.spines[["top", "right"]].set_visible(False)
    ax.margins(y=0.15)
    ax.legend(frameon=False, ncols=3, loc="lower right", bbox_to_anchor=(1, 1))
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def main():
    path = os.path.join(RESULTS_DIR, "summary.csv")
    table = medians(load(path))
    stores = sorted({n for n, _ in table})
    write_table(table, stores, os.path.join(RESULTS_DIR, "results_table.md"))
    bar_chart(table, stores, "throughput_ops_s", "Throughput (operations per second)",
              "Throughput by number of stores (median of runs)",
              os.path.join(RESULTS_DIR, "throughput.png"))
    bar_chart(table, stores, "p95_ms", "p95 latency (ms)",
              "95th-percentile latency by number of stores (median of runs)",
              os.path.join(RESULTS_DIR, "latency_p95.png"))
    print(f"\nSaved results_table.md, throughput.png and latency_p95.png in {RESULTS_DIR}/")


if __name__ == "__main__":
    main()