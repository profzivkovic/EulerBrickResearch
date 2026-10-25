"""Isolated v0.22.0 experiment; does not change search/checkpoints."""
import argparse
import math
import sys
import time
from pathlib import Path

import numpy as np
from numba import njit

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from safe_arithmetic_1000b import is_square_sum

# Exact necessary condition: any perfect square has residue 0, 1, 4, or 9 mod 16.
SQUARE_MASK_16 = sum(1 << r for r in (0, 1, 4, 9))

@njit(cache=True)
def filtered_square_sum(a, b):
    # Mask before multiplying: no risk of 64-bit overflow.
    a4 = a & 15
    b4 = b & 15
    residue = (a4 * a4 + b4 * b4) & 15
    if ((SQUARE_MASK_16 >> residue) & 1) == 0:
        return False
    return is_square_sum(a, b)

@njit(cache=True)
def compare_batch(a, b):
    old_count = 0
    new_count = 0
    mismatches = 0
    for i in range(len(a)):
        x = is_square_sum(a[i], b[i])
        y = filtered_square_sum(a[i], b[i])
        old_count += x
        new_count += y
        mismatches += x != y
    return old_count, new_count, mismatches

@njit(cache=True)
def time_old(a, b):
    count = 0
    for i in range(len(a)):
        count += is_square_sum(a[i], b[i])
    return count

@njit(cache=True)
def time_new(a, b):
    count = 0
    for i in range(len(a)):
        count += filtered_square_sum(a[i], b[i])
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pairs', type=int, default=200_000)
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    if args.pairs < 10 or args.repeats < 1:
        parser.error('pairs must be >= 10 and repeats >= 1')
    rng = np.random.default_rng(220)
    # Mix short and long edges; include genuine Pythagorean pairs.
    a = rng.integers(1, 50_000_000_001, size=args.pairs, dtype=np.int64)
    b = rng.integers(1, 50_000_000_001, size=args.pairs, dtype=np.int64)
    for i in range(0, args.pairs, 100):
        scale = int(rng.integers(1, 10_000_000_001))
        a[i] = 3 * scale
        b[i] = 4 * scale
    # Warm up JIT before timing.
    time_old(a[:10], b[:10]); time_new(a[:10], b[:10])
    old, new, mismatch = compare_batch(a, b)
    print(f'Pairs={len(a):,}  old_true={old}  new_true={new}  mismatches={mismatch}')
    if mismatch or old != new:
        raise SystemExit('FAIL: differing square-test results')
    times = []
    for name, fn in [('original', time_old), ('mod16', time_new)]:
        measurements = []
        for _ in range(args.repeats):
            start = time.perf_counter()
            result = fn(a, b)
            measurements.append(time.perf_counter() - start)
            assert result == old
        best = min(measurements)
        times.append(best)
        print(f'{name}: best={best:.6f}s  all={[round(x, 6) for x in measurements]}')
    print(f'Speedup (isolated test): {times[0] / times[1]:.3f}x')
    print('PASS: exact agreement on sampled inputs; not a full-search regression')

if __name__ == '__main__':
    main()
