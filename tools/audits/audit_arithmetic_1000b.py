#!/usr/bin/env python3
"""Independent arithmetic audit for experimental v0.20.0; no full search or writes.
Run from repository root: python tools/audits/audit_arithmetic_1000b.py
"""
import argparse
import math
import random
import sys
from pathlib import Path

import numpy as np


def python_legs(odd, bound, primes):
    n = odd
    factors = []
    for p in primes:
        p = int(p)
        if p * p > n:
            break
        if n % p == 0:
            exp = 0
            while n % p == 0:
                n //= p
                exp += 1
            factors.append((p, exp))
    if n > 1:
        factors.append((n, 1))
    ds = [1]
    for p, exp in factors:
        ds = [d * p**k for d in ds for k in range(2 * exp + 1) if d * p**k < odd]
    return sorted((odd * odd // d - d) // 2 for d in ds
                  if 0 < (odd * odd // d - d) // 2 <= bound)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--src-dir', type=Path, default=Path('src'))
    parser.add_argument('--random-pairs', type=int, default=2000)
    args = parser.parse_args()
    if args.random_pairs < 0:
        parser.error('--random-pairs must be nonnegative')
    src = args.src_dir.resolve()
    if not all((src / x).is_file() for x in ('safe_arithmetic_1000b.py',
            'odd_leg_numba_1000b_experimental.py', 'segmented_factorization.py')):
        parser.error('Missing v0.20.0 source files in --src-dir')
    sys.path.insert(0, str(src))
    from safe_arithmetic_1000b import checked_square_sum, square_u128, MAX_EDGE
    from odd_leg_numba_1000b_experimental import _leg_from_divisor, compatible_even_legs_jit
    from segmented_factorization import primes_upto, odd_spf_segment

    rng = random.Random(20261024)
    boundaries = [10**10, 10**11, 10**12]
    pairs = [(0, 0), (3, 4), (6*10**9, 8*10**9),
             (6*10**10, 8*10**10), (6*10**11, 8*10**11),
             (MAX_EDGE, MAX_EDGE), (MAX_EDGE, 1)]
    for bound in boundaries:
        for a in [0, 1, 2_147_483_647, 2_147_483_648, bound-2, bound-1, bound]:
            for b in [0, 1, bound-1, bound]:
                if a <= MAX_EDGE:
                    pairs.append((a, b))
        for _ in range(args.random_pairs):
            pairs.append((rng.randrange(bound+1), rng.randrange(bound+1)))
    for a, b in pairs:
        exact = a*a + b*b
        r = math.isqrt(exact)
        expected = r*r == exact
        got = checked_square_sum(a, b)
        assert got == expected, ('square mismatch', a, b, got, expected)
        for x in (a, b):
            hi, lo = square_u128(np.int64(x))
            assert (int(hi) << 64) + int(lo) == x*x, ('u128 mismatch', x)
    print(f'PASS: {len(pairs):,} exact square checks and {2*len(pairs):,} u128 squares')

    primes = np.asarray(primes_upto(math.isqrt(MAX_EDGE)), dtype=np.int64)
    odds = [3, 5, 9, 15, 45, 315, 999999937,
            10**10-1, 10**10-3, 10**10-9,
            10**11-1, 10**11-3, 10**11-9,
            10**12-1, 10**12-3, 10**12-9,
            999999999989, 999999999999, 999999999997,
            3**25, 5**16, 7**14]
    odds = sorted(set(o for o in odds if 3 <= o <= MAX_EDGE and o % 2))
    checks = 0
    for odd in odds:
        # One-element SPF segment exercises the same first-factor logic as full segments.
        spf = np.asarray(odd_spf_segment(odd, odd, primes), dtype=np.uint32)
        for bound in (10**10, 10**11, 10**12):
            got = sorted(int(e) for e in compatible_even_legs_jit(odd, bound, spf, odd, primes))
            expected = python_legs(odd, bound, primes)
            assert got == expected, ('legs mismatch', odd, bound, got[:8], expected[:8])
            checks += 1
        # Check every divisor that produces a leg (plus the divisor 1).
        for d in [1, odd]:
            got = int(_leg_from_divisor(odd, d, MAX_EDGE))
            expected = (odd*odd//d-d)//2 if d < odd else 0
            if expected > MAX_EDGE:
                expected = 0
            assert got == expected, ('divisor mismatch', odd, d)
    print(f'PASS: {checks} exact leg-set comparisons across 10B / 100B / 1000B')
    print('PASS: selected divisor boundaries; no full search performed')
    print('RUNNER AUDIT: NOT PASSED / NOT PERFORMED')
    print('  Existing v0.18.0 checkpoint runner remains capped at 2B.')
    print('  Per-segment Numba int64 counters and checkpoint aggregation need overflow analysis.')
    print('  1000B full search remains BLOCKED pending runner and scalability audit.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
