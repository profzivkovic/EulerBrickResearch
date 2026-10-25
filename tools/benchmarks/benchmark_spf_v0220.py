"""Isolated segmented-SPF experiment; does not modify the search or checkpoints."""
from __future__ import annotations
import argparse
import importlib.util
import math
from pathlib import Path
import statistics
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
FACTOR_PATH = ROOT / 'src' / 'segmented_factorization.py'
spec = importlib.util.spec_from_file_location('spf_reference_v0220', FACTOR_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f'Cannot load {FACTOR_PATH}')
factor = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = factor
spec.loader.exec_module(factor)


def odd_spf_numpy(lo: int, hi: int, base_primes: list[int]) -> np.ndarray:
    """Same SPF encoding as reference: zero means prime, first/smallest prime otherwise."""
    if lo < 3 or lo % 2 == 0 or hi < lo:
        raise ValueError('Require odd lo >= 3 and hi >= lo')
    spf = np.zeros((hi - lo) // 2 + 1, dtype=np.uint32)
    for p in base_primes:
        if p == 2:
            continue
        if p * p > hi:
            break
        start = max(p * p, ((lo + p - 1) // p) * p)
        if start % 2 == 0:
            start += p
        idx = (start - lo) // 2
        view = spf[idx::p]
        # Mark only previously unmarked multiples to preserve the smallest factor.
        np.copyto(view, np.uint32(p), where=(view == 0))
    return spf


def best_time(fn, repeats: int):
    samples = []
    result = None
    for _ in range(repeats):
        t0 = time.perf_counter()
        result = fn()
        samples.append(time.perf_counter() - t0)
    return min(samples), statistics.median(samples), result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--sizes', type=int, nargs='+', default=[1000, 10000, 100000])
    args = parser.parse_args()
    if args.repeats < 1 or any(x < 1 for x in args.sizes):
        parser.error('repeats and sizes must be positive')
    centers = [1_000_001, 20_000_000_001, 45_000_000_001]
    max_hi = max(centers) + 2 * (max(args.sizes) - 1)
    primes = factor.primes_upto(math.isqrt(max_hi))
    print(f'Prime count={len(primes):,}; repeats={args.repeats}; times in ms (best, median)')
    print('Reference returns array(I); candidate returns uint32 ndarray; both consumed as uint32 ndarray.')
    for center in centers:
        for count in args.sizes:
            lo = center
            hi = lo + 2 * (count - 1)
            def baseline():
                return np.asarray(factor.odd_spf_segment(lo, hi, primes), dtype=np.uint32)
            def candidate():
                return odd_spf_numpy(lo, hi, primes)
            a = baseline()
            b = candidate()
            if a.dtype != b.dtype or a.shape != b.shape or not np.array_equal(a, b):
                mismatches = np.flatnonzero(a != b)
                raise AssertionError(f'SPF MISMATCH center={center} size={count} indices={mismatches[:10]}')
            # Warm both functions outside timing; no Numba or disk cache involved.
            candidate()
            base_best, base_med, _ = best_time(baseline, args.repeats)
            cand_best, cand_med, _ = best_time(candidate, args.repeats)
            print(f'center={center:,} odds={count:,} '
                  f'baseline={base_best*1000:.3f}/{base_med*1000:.3f} '
                  f'candidate={cand_best*1000:.3f}/{cand_med*1000:.3f} '
                  f'speedup={base_best/cand_best:.3f}x '
                  f'array_bytes={a.nbytes:,} PASS exact SPF')
    print('PASS: all tested SPF arrays identical. Isolated benchmark, not end-to-end or 50B approval.')


if __name__ == '__main__':
    main()
