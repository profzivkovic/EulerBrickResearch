#!/usr/bin/env python3
"""Read-only v0.21.0 timing probe for SPF, leg generation, and fused kernel.

Run from repository root. Times are diagnostic; leg and fused times overlap,
so do NOT add them or interpret their difference as an exact pair-loop time.
"""
import argparse
import importlib.util
import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def measure(call, repeats):
    results = []
    value = None
    for _ in range(repeats):
        start = time.perf_counter()
        value = call()
        results.append(time.perf_counter() - start)
    return value, results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bound', type=int, default=50_000_000_000)
    parser.add_argument('--sample-odds', type=int, default=1000)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--positions', type=int, nargs='+', default=[1_000_001, 20_000_000_001, 45_000_000_001])
    args = parser.parse_args()
    if not (3 <= args.bound <= 1_000_000_000_000):
        parser.error('bound must be in 3..1e12')
    if args.sample_odds < 1 or args.repeats < 1:
        parser.error('sample-odds and repeats must be positive')

    root = Path(__file__).resolve().parents[2]
    src = root / 'src'
    sys.path.insert(0, str(src))
    factor = load_module('profile_v0220_factor', src / 'segmented_factorization.py')
    engine = load_module('profile_v0220_engine', src / 'odd_leg_numba_1000b_experimental.py')
    primes = np.asarray(factor.primes_upto(math.isqrt(args.bound)), dtype=np.int64)

    # Compile both JIT entry points before timing; matches runner input types.
    warm_spf = np.asarray(factor.odd_spf_segment(3, 101, primes), dtype=np.uint32)
    engine.compatible_even_legs_jit(3, 101, warm_spf, 3, primes)
    engine.fused_segment_kernel(3, 101, 101, warm_spf, primes)
    print(f'Bound={args.bound:,}; sample_odds={args.sample_odds}; repeats={args.repeats}; primes={len(primes)}')
    print('Times are best-of-N wall seconds; single process; JIT warm; no Drive I/O.')

    for requested in args.positions:
        lo = max(3, requested | 1)
        if lo > args.bound:
            print(f'SKIP position {requested:,}: above bound')
            continue
        hi = min(args.bound if args.bound % 2 else args.bound - 1,
                 lo + 2 * (args.sample_odds - 1))
        if hi < lo:
            continue
        spf_raw, spf_times = measure(lambda: factor.odd_spf_segment(lo, hi, primes), args.repeats)
        spf = np.asarray(spf_raw, dtype=np.uint32)
        _, convert_times = measure(lambda: np.asarray(spf_raw, dtype=np.uint32), args.repeats)
        odds = range(lo, hi + 1, 2)

        def legs_only():
            total = 0
            for odd in odds:
                total += len(engine.compatible_even_legs_jit(odd, args.bound, spf, lo, primes))
            return total

        leg_count, legs_times = measure(legs_only, args.repeats)
        def fused():
            return engine.fused_segment_kernel(lo, hi, args.bound, spf, primes)
        result, kernel_times = measure(fused, args.repeats)
        # Check repeatability; this is NOT a cross-version regression.
        second = fused()
        if result[1:] != second[1:] or sorted(result[0]) != sorted(second[0]):
            raise AssertionError(f'Non-deterministic kernel result at {lo}')
        best = lambda xs: min(xs)
        print(f'[{lo:,}..{hi:,}] odds={len(odds)} legs={leg_count:,} '
              f'bricks={len(result[0])} tested={result[1]:,} rejected={result[2]:,}')
        print(f'  SPF={best(spf_times):.6f}s  array->numpy={best(convert_times):.6f}s  '
              f'legs_only={best(legs_times):.6f}s  fused_kernel={best(kernel_times):.6f}s')
        if best(kernel_times) > 0:
            print(f'  legs_only/fused={best(legs_times)/best(kernel_times):.3f} '
                  '(indicative only; includes different call overhead)')
    print('PASS: deterministic repeated kernel results. No catalog/checkpoint changes.')
    print('NOTE: sampled timing only; not 50B safety, completeness, or performance proof.')


if __name__ == '__main__':
    main()
