#!/usr/bin/env bash
# Runs the same benchmark with 1, 2 and 3 stores, under identical conditions.
#
# Usage:   ./run_benchmarks.sh
# Options: REPEATS=5 OPS=3000 THREADS=8 ./run_benchmarks.sh
#
# For every number of stores it: starts fresh containers with empty volumes, waits until
# everything is up, runs the benchmark REPEATS times inside the Docker network, then
# removes the containers and their data. Results go to benchmark_results/summary.csv.
set -euo pipefail

REPEATS=${REPEATS:-3}
OPS=${OPS:-2000}
THREADS=${THREADS:-8}

mkdir -p benchmark_results
if [ -f benchmark_results/summary.csv ]; then        # keep old results, start a clean file
  mv benchmark_results/summary.csv "benchmark_results/summary_old_$(date +%Y%m%d_%H%M%S).csv"
fi

docker compose build store1

for N in 1 2 3; do
  services="router"
  urls=""
  for i in $(seq 1 "$N"); do
    services="store$i $services"
    urls="${urls:+$urls,}http://store$i:8080"
  done
  echo
  echo "=== $N store(s): $urls ==="

  docker compose down -v --remove-orphans >/dev/null 2>&1 || true
  STORE_URLS="$urls" docker compose up -d --wait $services

  for t in $(seq 1 30); do                            # wait until the router answers
    if curl -sf http://localhost:8000/ >/dev/null; then break; fi
    sleep 1
  done

  for r in $(seq 1 "$REPEATS"); do
    docker compose run --rm bench --url http://router:8000 --stores "$N" --run "$r" \
      --ops "$OPS" --threads "$THREADS"
  done

  docker compose down -v
done

echo
echo "Done. Now run: python plot_results.py"