"""Benchmark for the distributed key-value store.

Sends the same workload every time, in three timed phases:
  PUT     write N new keys
  GET     read the same N keys back and check every value
  DELETE  delete the same N keys
and reports, per phase, throughput (ops/s) and latency (average, p50, p95, p99 in ms).

It talks to whatever URL you give it: the router (normal use) or a single store (for testing).

Examples:
  python benchmark.py --url http://127.0.0.1:8081              # one store, directly
  python benchmark.py --url http://127.0.0.1:8000 --stores 3    # through the router
  python benchmark.py --url http://router:8000 --stores 2 --run 1   # inside Docker Compose

Every run adds one line per phase to benchmark_results/summary.csv,
and saves the full result to benchmark_results/<label>.json.
"""
import argparse
import csv
import json
import os
import statistics
import threading
import time
import uuid
from datetime import datetime

import requests

SUMMARY_FIELDS = [
    "timestamp", "label", "stores", "run", "phase", "ops", "threads", "value_size",
    "successes", "errors", "mismatches", "seconds", "throughput_ops_s",
    "avg_ms", "p50_ms", "p95_ms", "p99_ms",
]


def percentile(sorted_values, p):
    """The p-th percentile (0-100) of an already sorted list."""
    if not sorted_values:
        return float("nan")
    index = min(len(sorted_values) - 1, max(0, round(p / 100 * len(sorted_values)) - 1))
    return sorted_values[index]


def make_value(i, size):
    """A value of exactly `size` characters that is different for every key."""
    text = f"value-{i}-"
    return (text * (size // len(text) + 1))[:size]


def one_request(session, base_url, phase, key, value):
    """Sends one request. Returns (ok, mismatch)."""
    if phase == "PUT":
        r = session.put(f"{base_url}/{key}", json={"value": value}, timeout=10)
        return r.status_code in (200, 201), False
    if phase == "GET":
        r = session.get(f"{base_url}/{key}", timeout=10)
        if r.status_code != 200:
            return False, False
        return True, r.json().get("value") != value
    if phase == "DELETE":
        r = session.delete(f"{base_url}/{key}", timeout=10)
        return r.status_code == 200, False
    raise ValueError(phase)


def run_phase(base_url, phase, keys, values, threads):
    """Runs one phase with `threads` client threads. Each thread handles its own share of keys
    and keeps one connection open (requests.Session), like a real client would."""
    latencies, errors, mismatches = [], [0], [0]
    lock = threading.Lock()
    start_line = threading.Barrier(threads + 1)

    def worker(indices):
        session = requests.Session()
        mine = []
        my_errors = my_mismatches = 0
        start_line.wait()
        for i in indices:
            started = time.perf_counter()
            try:
                ok, mismatch = one_request(session, base_url, phase, keys[i], values[i])
            except requests.RequestException:
                ok, mismatch = False, False
            elapsed_ms = (time.perf_counter() - started) * 1000
            if ok:
                mine.append(elapsed_ms)
            else:
                my_errors += 1
            if mismatch:
                my_mismatches += 1
        session.close()
        with lock:
            latencies.extend(mine)
            errors[0] += my_errors
            mismatches[0] += my_mismatches

    workers = [threading.Thread(target=worker, args=(range(t, len(keys), threads),))
               for t in range(threads)]
    for w in workers:
        w.start()
    start_line.wait()                      # all threads start at the same moment
    phase_start = time.perf_counter()
    for w in workers:
        w.join()
    seconds = time.perf_counter() - phase_start

    latencies.sort()
    return {
        "phase": phase,
        "successes": len(latencies),
        "errors": errors[0],
        "mismatches": mismatches[0],
        "seconds": round(seconds, 3),
        "throughput_ops_s": round(len(latencies) / seconds, 1) if seconds > 0 else 0.0,
        "avg_ms": round(statistics.mean(latencies), 2) if latencies else float("nan"),
        "p50_ms": round(percentile(latencies, 50), 2),
        "p95_ms": round(percentile(latencies, 95), 2),
        "p99_ms": round(percentile(latencies, 99), 2),
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark the key-value store")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="router or store URL")
    parser.add_argument("--ops", type=int, default=2000, help="keys per phase")
    parser.add_argument("--threads", type=int, default=8, help="concurrent client threads")
    parser.add_argument("--value-size", type=int, default=100, help="characters per value")
    parser.add_argument("--warmup", type=int, default=200, help="untimed requests before measuring")
    parser.add_argument("--stores", type=int, default=0, help="number of stores behind the URL (for the results file)")
    parser.add_argument("--run", type=int, default=1, help="repeat number (for the results file)")
    parser.add_argument("--keep", action="store_true", help="skip DELETE, so the keys stay in the stores")
    parser.add_argument("--out-dir", default="benchmark_results")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    try:
        health = requests.get(base_url + "/", timeout=5)
        health.raise_for_status()
    except requests.RequestException as error:
        raise SystemExit(f"Cannot reach {base_url}: {error}")

    tag = uuid.uuid4().hex[:6]             # different keys in every run
    keys = [f"bench-{tag}-{i:06d}" for i in range(args.ops)]
    values = [make_value(i, args.value_size) for i in range(args.ops)]

    if args.warmup > 0:                    # open connections and warm caches; not measured
        warm_keys = [f"warmup-{tag}-{i}" for i in range(args.warmup)]
        warm_values = [make_value(i, args.value_size) for i in range(args.warmup)]
        for phase in ("PUT", "GET", "DELETE"):
            run_phase(base_url, phase, warm_keys, warm_values, args.threads)

    phases = ("PUT", "GET") if args.keep else ("PUT", "GET", "DELETE")
    results = [run_phase(base_url, phase, keys, values, args.threads) for phase in phases]

    label = f"stores{args.stores}_run{args.run}_{tag}"
    stamp = datetime.now().isoformat(timespec="seconds")
    print(f"\nTarget {base_url}  stores={args.stores}  run={args.run}  ops={args.ops}  "
          f"threads={args.threads}  value_size={args.value_size}")
    print(f"{'phase':<8}{'ok':>7}{'errors':>8}{'mismatch':>10}{'ops/s':>10}"
          f"{'avg ms':>9}{'p50 ms':>9}{'p95 ms':>9}{'p99 ms':>9}")
    for r in results:
        print(f"{r['phase']:<8}{r['successes']:>7}{r['errors']:>8}{r['mismatches']:>10}"
              f"{r['throughput_ops_s']:>10}{r['avg_ms']:>9}{r['p50_ms']:>9}{r['p95_ms']:>9}{r['p99_ms']:>9}")

    os.makedirs(args.out_dir, exist_ok=True)
    summary_path = os.path.join(args.out_dir, "summary.csv")
    new_file = not os.path.exists(summary_path)
    with open(summary_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        if new_file:
            writer.writeheader()
        for r in results:
            writer.writerow({"timestamp": stamp, "label": label, "stores": args.stores,
                             "run": args.run, "ops": args.ops, "threads": args.threads,
                             "value_size": args.value_size, **r})
    with open(os.path.join(args.out_dir, f"{label}.json"), "w") as f:
        json.dump({"timestamp": stamp, "url": base_url, "settings": vars(args),
                   "results": results}, f, indent=2)
    print(f"\nSaved to {summary_path} and {label}.json")

    if any(r["errors"] or r["mismatches"] for r in results):
        raise SystemExit("Some requests failed or returned wrong values (see table above).")


if __name__ == "__main__":
    main()