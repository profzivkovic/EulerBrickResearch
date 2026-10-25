"""Compare reference, NumPy, and Numba segmented odd-SPF implementations.
Read-only benchmark; no changes to production code, catalogs or checkpoints.
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
sys.path.insert(0, str(ROOT / 'src'))
import segmented_factorization as factor


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


def spf_numpy(lo, hi, primes):
    spf = np.zeros((hi - lo) // 2 + 1, dtype=np.uint32)
    for p in primes:
        p = int(p)
        if p == 2:
            continue
        if p * p > hi:
            break
        start = max(p * p, ((lo + p - 1) // p) * p)
        if start % 2 == 0:
            start += p
        view = spf[(start - lo) // 2::p]
        np.copyto(view, np.uint32(p), where=(view == 0))
    return spf


def timing(fn, repeats):
    samples = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000)
    return min(samples), statistics.median(samples)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--sizes', type=int, nargs='+', default=[1000, 10000, 100000])
    args = parser.parse_args()
    if args.repeats < 1 or not args.sizes or any(n < 1 for n in args.sizes):
        parser.error('repeats and sizes must be positive')
    centers = (1_000_001, 20_000_000_001, 45_000_000_001)
    max_hi = max(centers) + 2 * (max(args.sizes) - 1)
    primes_list = factor.primes_upto(math.isqrt(max_hi))
    primes_np = np.asarray(primes_list, dtype=np.int64)
    # Warm up compilation OUTSIDE measured timings; no disk cache.
    spf_numba_core(np.int64(3), np.int64(101), primes_np)
    print(f'primes={len(primes_list):,}; repeats={args.repeats}; times=best/median ms')
    for lo in centers:
        for count in args.sizes:
            hi = lo + 2 * (count - 1)
            def reference():
                return np.asarray(factor.odd_spf_segment(lo, hi, primes_list), dtype=np.uint32)
            def numpy_version():
                return spf_numpy(lo, hi, primes_np)
            def numba_version():
                return spf_numba_core(np.int64(lo), np.int64(hi), primes_np)
            expected = reference()
            for name, fn in (('numpy', numpy_version), ('numba', numba_version)):
                actual = fn()
                if actual.dtype != np.uint32 or actual.shape != expected.shape or not np.array_equal(actual, expected):
                    bad = np.flatnonzero(actual != expected)[:10] if actual.shape == expected.shape else []
                    raise AssertionError(f'{name} SPF MISMATCH lo={lo} count={count} indices={bad}')
            # Warm individual paths before each set of measurements.
            reference(); numpy_version(); numba_version()
            rb, rm = timing(reference, args.repeats)
            pb, pm = timing(numpy_version, args.repeats)
            nb, nm = timing(numba_version, args.repeats)
            print(f'center={lo:,} odds={count:,} '
                  f'ref={rb:.3f}/{rm:.3f} numpy={pb:.3f}/{pm:.3f} '
                  f'numba={nb:.3f}/{nm:.3f} '
                  f'numba_speedup={rb/nb:.3f}x bytes={expected.nbytes:,} PASS exact SPF')
    print('PASS: all SPF arrays identical; benchmark only, NOT 50B runner approval.')


if __name__ == '__main__':
    main()
