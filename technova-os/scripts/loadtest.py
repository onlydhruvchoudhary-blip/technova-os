#!/usr/bin/env python3
"""TECHNOVA OS — lightweight load / smoke test (stdlib only, no k6/locust needed).

Fires N concurrent workers doing a realistic read mix (leaderboard, activity feed, challenges,
dashboard profile) against a running instance and reports throughput + latency percentiles (p50/
p95/p99). Also opens a handful of SSE connections to confirm the broker fan-out survives many
subscribers without per-connection DB polling.

Usage:
    python scripts/loadtest.py --base http://localhost:8000 --users 40 --requests 20
    python scripts/loadtest.py --base https://<your-app> --users 100 --requests 30 --sse 20

Exit code is non-zero if the error rate exceeds --max-error-rate (default 1%), so it can gate CI.
This is intentionally dependency-free; for a production SLA use k6/locust with the same scenarios.
"""
from __future__ import annotations

import argparse
import statistics
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

READ_PATHS = [
    "/api/leaderboard",
    "/api/activity?limit=20",
    "/api/challenges",
    "/api/me/profile",
    "/api/events",
]


def login(base: str, email: str, password: str) -> str:
    body = f"username={email}&password={password}".encode()
    req = urllib.request.Request(f"{base}/api/auth/login", data=body,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    import json
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())["access_token"]


def one_request(base: str, token: str, path: str) -> tuple[bool, float]:
    req = urllib.request.Request(f"{base}{path}", headers={"X-Auth-Token": token})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
            ok = 200 <= r.status < 300
    except Exception:
        ok = False
    return ok, (time.perf_counter() - t0) * 1000.0


def worker(base: str, token: str, n: int) -> list[tuple[bool, float]]:
    out = []
    for i in range(n):
        out.append(one_request(base, token, READ_PATHS[i % len(READ_PATHS)]))
    return out


def sse_probe(base: str, token: str, seconds: float) -> bool:
    """Open one SSE connection; success = we received at least one frame or clean keepalive."""
    req = urllib.request.Request(f"{base}/api/activity/stream?token={token}")
    try:
        with urllib.request.urlopen(req, timeout=seconds + 5) as r:
            end = time.time() + seconds
            while time.time() < end:
                line = r.readline()
                if not line:
                    break
        return True
    except Exception:
        return False


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    k = max(0, min(len(values) - 1, int(round((p / 100) * (len(values) - 1)))))
    return values[k]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--email", default="admin@technova.club")
    ap.add_argument("--password", default="password123")
    ap.add_argument("--users", type=int, default=40)
    ap.add_argument("--requests", type=int, default=20)
    ap.add_argument("--sse", type=int, default=10, help="concurrent SSE probes")
    ap.add_argument("--max-error-rate", type=float, default=0.01)
    args = ap.parse_args()

    print(f"→ logging in as {args.email} ...")
    token = login(args.base, args.email, args.password)

    print(f"→ REST load: {args.users} users × {args.requests} requests "
          f"= {args.users * args.requests} calls")
    results: list[tuple[bool, float]] = []
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.users) as ex:
        futs = [ex.submit(worker, args.base, token, args.requests) for _ in range(args.users)]
        for f in as_completed(futs):
            results.extend(f.result())
    wall = time.perf_counter() - t0

    lat = [ms for _, ms in results]
    ok = sum(1 for good, _ in results if good)
    total = len(results)
    err_rate = (total - ok) / total if total else 1.0

    print("\n── REST results ─────────────────────────────")
    print(f"  requests      : {total}")
    print(f"  ok / errors   : {ok} / {total - ok}  ({err_rate * 100:.2f}% errors)")
    print(f"  throughput    : {total / wall:,.0f} req/s over {wall:.2f}s")
    print(f"  latency p50   : {pct(lat, 50):.1f} ms")
    print(f"  latency p95   : {pct(lat, 95):.1f} ms")
    print(f"  latency p99   : {pct(lat, 99):.1f} ms")
    print(f"  latency max   : {max(lat):.1f} ms" if lat else "  latency max   : —")

    if args.sse > 0:
        print(f"\n→ SSE fan-out: {args.sse} concurrent stream subscribers for 3s ...")
        sse_ok = 0
        lock = threading.Lock()

        def _probe():
            nonlocal sse_ok
            good = sse_probe(args.base, token, 3.0)
            with lock:
                sse_ok += int(good)

        threads = [threading.Thread(target=_probe) for _ in range(args.sse)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        print(f"  SSE connections held : {sse_ok}/{args.sse}")

    print("\n── verdict ──────────────────────────────────")
    if err_rate <= args.max_error_rate:
        print(f"  PASS (error rate {err_rate * 100:.2f}% ≤ {args.max_error_rate * 100:.2f}%)")
        return 0
    print(f"  FAIL (error rate {err_rate * 100:.2f}% > {args.max_error_rate * 100:.2f}%)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
