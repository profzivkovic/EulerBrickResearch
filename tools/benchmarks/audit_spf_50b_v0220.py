"""Read-only high-bound SPF audit for 50B; no kernel or checkpoint approval."""
from __future__ import annotations
import math
import sys
import time
from pathlib import Path
import numpy as np
from numba import njit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import segmented_factorization as factor

BOUND = 50_000_000_000

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

def main():
    primes = factor.primes_upto(math.isqrt(BOUND))
    primes_np = np.asarray(primes, dtype=np.int64)
    spf_numba_core(np.int64(3), np.int64(101), primes_np)

    # Prime-square crossing: largest odd prime <= sqrt(50B).
    p = next(x for x in reversed(primes) if x != 2)
    square = p * p
    cases = [
        ("20B+1", 20_000_000_001, 100_000),
        ("45B", 45_000_000_001, 100_000),
        ("50B-final-full", BOUND - 199_999, 100_000),
        ("50B-final-short", BOUND - 1_999, 1_000),
        ("50B-last-odd", BOUND - 1, 1),
        ("prime-square-crossing", square - 999, 1_000),
        ("tiny-start", 3, 7),
    ]
    print(f"50B SPF audit; primes={len(primes):,}; prime_square={p}^2={square:,}")
    for label, lo, count in cases:
        if lo % 2 == 0:
            lo += 1
        hi = lo + 2 * (count - 1)
        if hi >= BOUND:
            raise AssertionError(f"Invalid audit interval: {label}")
        t0 = time.perf_counter()
        ref = np.asarray(factor.odd_spf_segment(lo, hi, primes), dtype=np.uint32)
        ref_s = time.perf_counter() - t0
        t0 = time.perf_counter()
        got = spf_numba_core(np.int64(lo), np.int64(hi), primes_np)
        jit_s = time.perf_counter() - t0
        if ref.shape != got.shape or ref.dtype != got.dtype or not np.array_equal(ref, got):
            bad = np.flatnonzero(ref != got)[:10]
            raise AssertionError(f"FAIL {label} indices={bad.tolist()}")
        # Independently verify the prime-square entry if present.
        if lo <= square <= hi:
            idx = (square - lo) // 2
            if int(got[idx]) != p:
                raise AssertionError(f"FAIL prime square: SPF({square})={got[idx]}, expected {p}")
        print(f"PASS {label}: [{lo:,}..{hi:,}] odds={count:,} "
              f"ref={ref_s:.4f}s numba={jit_s:.4f}s")
    print("PASS: sampled high-bound SPF arrays identical.")
    print("NOT a 50B kernel overflow, search completeness, checkpoint, or resume audit.")

if __name__ == "__main__":
    main()
