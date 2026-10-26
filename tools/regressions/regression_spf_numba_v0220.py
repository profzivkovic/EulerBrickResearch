"""Read-only integration regression: v0.21.0 SPF vs Numba SPF, same original kernel.

Usage:
  python tools/regressions/regression_spf_numba_v0220.py --max-edge 100000
  python tools/regressions/regression_spf_numba_v0220.py --max-edge 1000000
  python tools/regressions/regression_spf_numba_v0220.py --max-edge 10000000
"""
from __future__ import annotations

import argparse
import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np
from numba import njit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

# Standard imports: avoid dynamic module names in Numba's cached dependencies.
import segmented_factorization as factor
import odd_leg_numba_1000b_experimental as engine


@njit(cache=False)
def spf_numba_core(lo, hi, primes):
    count = (hi - lo) // 2 + 1
    spf = np.zeros(count, dtype=np.uint32)
    for j in range(primes.size):
        p = np.int64(primes[j])
        if p == 2:
            continue
        if p * p > hi:
            break
        start = ((lo + p - 1) // p) * p
        if start < p * p:
            start = p * p
        if start % 2 == 0:
            start += p
        for n in range(start, hi + 1, 2 * p):
            idx = (n - lo) // 2
            if spf[idx] == 0:
                spf[idx] = np.uint32(p)
    return spf


def execute(bound, segment_odds, primes_list, primes_np, use_numba):
    bricks = set()
    tested = rejected = 0
    spf_seconds = kernel_seconds = 0.0
    segments = 0
    for lo in range(3, bound + 1, 2 * segment_odds):
        hi = min(bound, lo + 2 * (segment_odds - 1))
        t0 = time.perf_counter()
        if use_numba:
            spf = spf_numba_core(np.int64(lo), np.int64(hi), primes_np)
        else:
            spf = np.asarray(factor.odd_spf_segment(lo, hi, primes_list), dtype=np.uint32)
        spf_seconds += time.perf_counter() - t0
        t0 = time.perf_counter()
        triples, t, r = engine.fused_segment_kernel(lo, hi, bound, spf, primes_np)
        kernel_seconds += time.perf_counter() - t0
        tested += int(t)
        rejected += int(r)
        for odd, e1, e2 in triples:
            bricks.add(tuple(sorted((int(odd), int(e1), int(e2)))))
        segments += 1
    return bricks, tested, rejected, spf_seconds, kernel_seconds, segments


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-edge", type=int, default=100_000)
    ap.add_argument("--segment-odds", type=int, default=10_000)
    ap.add_argument("--repeats", type=int, default=3)
    args = ap.parse_args()
    if not 3 <= args.max_edge <= 10_000_000:
        ap.error("--max-edge must be in 3..10,000,000")
    if args.segment_odds < 1 or args.repeats < 1:
        ap.error("--segment-odds and --repeats must be positive")

    primes_list = factor.primes_upto(math.isqrt(args.max_edge))
    primes_np = np.asarray(primes_list, dtype=np.int64)

    # Warm both JIT paths before timing; no modifications to project files.
    spf_numba_core(np.int64(3), np.int64(101), primes_np)
    warm_spf = np.asarray(factor.odd_spf_segment(3, 101, primes_list), dtype=np.uint32)
    engine.fused_segment_kernel(3, 101, 100, warm_spf, primes_np)

    reference_times = []
    candidate_times = []
    for rep in range(args.repeats):
        # Alternate execution order to reduce order-dependent measurement bias.
        order = (False, True) if rep % 2 == 0 else (True, False)
        results = {}
        for use_numba in order:
            results[use_numba] = execute(
                args.max_edge, args.segment_odds, primes_list, primes_np, use_numba
            )
        old, new = results[False], results[True]
        if old[:3] != new[:3]:
            missing = sorted(old[0] - new[0])[:10]
            extra = sorted(new[0] - old[0])[:10]
            raise SystemExit(
                f"FAIL repeat={rep + 1}: sets/counters differ "
                f"missing={missing} extra={extra} "
                f"old_counts={old[1:3]} new_counts={new[1:3]}"
            )
        reference_times.append((old[3], old[4]))
        candidate_times.append((new[3], new[4]))
        print(
            f"repeat={rep + 1} PASS exact sets/counters "
            f"bricks={len(old[0])} tested={old[1]} rejected={old[2]} "
            f"segments={old[5]}"
        )
    old_spf = statistics.median(x[0] for x in reference_times)
    new_spf = statistics.median(x[0] for x in candidate_times)
    old_kernel = statistics.median(x[1] for x in reference_times)
    new_kernel = statistics.median(x[1] for x in candidate_times)
    print(
        f"Bound={args.max_edge:,}; segment_odds={args.segment_odds:,}; "
        f"repeats={args.repeats}"
    )
    print(f"Reference median SPF={old_spf:.6f}s kernel={old_kernel:.6f}s")
    print(f"Candidate median SPF={new_spf:.6f}s kernel={new_kernel:.6f}s")
    print(f"SPF speedup={old_spf / new_spf:.3f}x")
    print(f"Compute speedup={(old_spf + old_kernel) / (new_spf + new_kernel):.3f}x")
    print("PASS: integration regression; not checkpoint, 50B overflow or completeness approval")


if __name__ == "__main__":
    main()

