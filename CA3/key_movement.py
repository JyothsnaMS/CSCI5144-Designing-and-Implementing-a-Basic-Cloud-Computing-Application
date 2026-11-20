"""Shows how keys are spread over the stores, and how many keys "move" after the ring changes.

It asks every store which keys it holds (GET /admin/keys), then asks the ROUTER for each key.
  found (200)     the router still sends this key to the store that holds it
  moved (404)     the router now sends this key to a different store, which doesn't have it,
                  because consistent hashing changes ownership but does not copy the data

Usage (from your Mac, while the containers run):
  python key_movement.py --router http://localhost:8000 --stores http://localhost:8081,http://localhost:8082
"""
import argparse
import time

import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--router", default="http://localhost:8000")
    parser.add_argument("--stores", required=True, help="comma-separated store URLs to inspect")
    args = parser.parse_args()

    session = requests.Session()
    holder = {}
    print("Keys held by each store:")
    for url in [u.strip().rstrip("/") for u in args.stores.split(",") if u.strip()]:
        try:
            data = session.get(f"{url}/admin/keys", timeout=10).json()
        except requests.RequestException:
            print(f"  {url}: not reachable (stopped?)")
            continue
        print(f"  {data['node']:<10} {data['count']:>6} keys")
        for key in data["keys"]:
            holder[key] = data["node"]

    total = len(holder)
    if total == 0:
        raise SystemExit("No keys found. Write some first, e.g. with benchmark.py --keep.")

    moved, unreachable = {}, 0
    router = args.router.rstrip("/")
    for key, node in holder.items():
        status = None
        for attempt in range(3):          # retry a dropped connection up to 3 times
            try:
                status = session.get(f"{router}/{key}", timeout=10).status_code
                break
            except requests.RequestException:
                time.sleep(1)
        if status is None:
            unreachable += 1
        elif status != 200:
            moved[node] = moved.get(node, 0) + 1
    if unreachable == total:
        raise SystemExit(f"The router at {router} could not be reached. Is it running? Try: curl {router}/")
    moved_total = sum(moved.values())
    if unreachable:
        print(f"\nWarning: {unreachable} keys could not be checked (router unreachable).")

    print(f"\nKeys checked through the router: {total}")
    print(f"  still found: {total - moved_total} ({(total - moved_total) / total:.1%})")
    print(f"  moved (router now looks in another store): {moved_total} ({moved_total / total:.1%})")
    for node, count in sorted(moved.items()):
        print(f"    of those, previously on {node}: {count}")


if __name__ == "__main__":
    main()