#!/usr/bin/env python3
"""EulerBrickResearch experimental v0.22.0 (mod16): 1000B-safe arithmetic, fast int64 path.
Preserves the v0.18.0 search logic; uses 128-bit pair-square comparisons.
Experimental 1000B arithmetic; full searches above 2B not yet approved.
Does not modify the verified catalog.
"""
import argparse
import csv
import importlib.util
import math
import time
import sys
from pathlib import Path

import numpy as np
from numba import njit
from safe_arithmetic_1000b import is_square_sum

# v0.22.0 experimental exact necessary filter: squares mod 16 are 0,1,4,9.
SQUARE_MASK_16 = 0x0213


@njit(cache=True)
def filtered_square_sum(a, b):
    a4 = a & 15
    b4 = b & 15
    residue = (a4 * a4 + b4 * b4) & 15
    if ((SQUARE_MASK_16 >> residue) & 1) == 0:
        return False
    return is_square_sum(a, b)

MAX_SAFE_BOUND = 1_000_000_000_000  # audited through 2B: pair sums fit int64; three-square tests use Python ints


@njit(cache=True)
def _leg_from_divisor(odd, d, bound):
    """Exact odd**2 // d for d | odd**2, without overflow or 128-bit division.

    Let g=gcd(odd,d), k=d/g. Because d divides odd**2, k divides odd.
    Then odd**2/d = (odd/g)*(odd/k). Test against cap before multiply.
    """
    g = math.gcd(odd, d)
    k = d // g
    q1 = odd // g
    q2 = odd // k
    cap = d + 2*bound  # <= 3e12 for 1000B, fits int64
    if q1 > cap // q2:
        return np.int64(0)
    quotient = q1*q2
    if quotient <= d:
        return np.int64(0)
    return (quotient - d)//2


@njit(cache=True)
def compatible_even_legs_jit(odd, bound, spf, segment_lo, base_primes):
    """Generate every e<=bound from divisors d<odd of odd**2 (Numba int64)."""
    if odd <= 1:
        return np.empty(0, dtype=np.int64)
    n = odd
    primes = []
    exponents = []
    # Segment SPF supplies the first factor; remaining factors are obtained
    # from the small prime table. Unlike a global SPF, segment SPF cannot
    # index the shrinking remainder, which may lie outside this segment.
    first = int(spf[(odd - segment_lo) // 2])
    if first == 0:
        primes.append(odd)
        exponents.append(1)
        n = 1
    else:
        # The segment already supplies the smallest prime factor of odd.
        # Extract it immediately, then skip all smaller primes in trial division.
        exponent = 0
        while n % first == 0:
            n //= first
            exponent += 1
        primes.append(first)
        exponents.append(exponent)
        for p in base_primes:
            if p <= first:
                continue
            if p * p > n:
                break
            if n % p == 0:
                exponent = 0
                while n % p == 0:
                    n //= p
                    exponent += 1
                primes.append(int(p))
                exponents.append(exponent)
        if n > 1:
            primes.append(n)
            exponents.append(1)
    divisors = [1]
    for index in range(len(primes)):
        prime = primes[index]
        exponent = exponents[index]
        last = index == len(primes) - 1
        if last:
            legs = []
            for d in divisors:
                value = d
                for _ in range(2 * exponent + 1):
                    if value >= odd:
                        break
                    e = _leg_from_divisor(odd, value, bound)
                    if 0 < e <= bound:
                        legs.append(e)
                    if value > (odd - 1) // prime:
                        break
                    value *= prime
            return np.asarray(legs, dtype=np.int64)
        next_divisors = []
        for d in divisors:
            value = d
            for _ in range(2 * exponent + 1):
                if value >= odd:
                    break
                next_divisors.append(value)
                if value > (odd - 1) // prime:
                    break
                value *= prime
        divisors = next_divisors
    return np.empty(0, dtype=np.int64)


@njit(cache=True)
def integer_sqrt64(n):
    """Exact floor sqrt of nonnegative int64 using overflow-safe divisions."""
    if n <= 0:
        return 0
    r = int(math.sqrt(n))
    if r < 1:
        r = 1
    while r + 1 <= n // (r + 1):
        r += 1
    while r > n // r:
        r -= 1
    return r


@njit(cache=True)
def fused_odd_kernel(odd, bound, spf, segment_lo, base_primes):
    """Generate legs, partition, and check all admissible primitive pairs in JIT."""
    legs = compatible_even_legs_jit(odd, bound, spf, segment_lo, base_primes)
    div = []
    nondiv = []
    for e in legs:
        if e % 3 == 0:
            div.append(e)
        elif odd % 3 == 0:
            nondiv.append(e)
    matches = []
    tested = 0
    rejected = 0
    if odd % 3 == 0:
        for e1 in div:
            g1 = math.gcd(odd, e1)
            for e2 in nondiv:
                if math.gcd(g1, e2) != 1:
                    rejected += 1
                    continue
                tested += 1
                if filtered_square_sum(e1, e2):
                    matches.append((e1, e2))
    else:
        for i in range(len(div)):
            e1 = div[i]
            g1 = math.gcd(odd, e1)
            for j in range(i + 1, len(div)):
                e2 = div[j]
                if math.gcd(g1, e2) != 1:
                    rejected += 1
                    continue
                tested += 1
                if filtered_square_sum(e1, e2):
                    matches.append((e1, e2))
    return matches, tested, rejected


@njit(cache=True)
def fused_segment_kernel(lo, hi, bound, spf, base_primes):
    """Run the unchanged per-odd kernel inside one Numba segment call."""
    all_matches = []
    tested_total = 0
    rejected_total = 0
    for odd in range(lo, hi + 1, 2):
        pairs, tested, rejected = fused_odd_kernel(
            odd, bound, spf, lo, base_primes
        )
        tested_total += tested
        rejected_total += rejected
        for e1, e2 in pairs:
            all_matches.append((odd, e1, e2))
    return all_matches, tested_total, rejected_total


def load_stable(path):
    spec = importlib.util.spec_from_file_location('stable_odd_leg_v099', path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Cannot import stable source: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.VERSION != '0.9.9':
        raise RuntimeError(f'Expected stable v0.9.9, found {module.VERSION}')
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('src/odd_leg_search.py'))
    parser.add_argument('--max-edge', type=int, required=True)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--progress-every', type=int, default=0)
    parser.add_argument('--segment-odds', type=int, default=100_000)
    parser.add_argument('--confirm-2b', action='store_true',
                        help='Explicitly permit an experimental run above 1B')
    args = parser.parse_args()
    if not 1 <= args.max_edge <= MAX_SAFE_BOUND:
        parser.error(f'--max-edge must be in 1..{MAX_SAFE_BOUND} for int64 safety')
    if args.max_edge > 2_000_000_000:
        parser.error('Full searches above 2B require audited checkpoint/parallel runner; arithmetic alone is ready for testing')
    if args.segment_odds < 1:
        parser.error('--segment-odds must be positive')
    if args.progress_every < 0:
        parser.error('--progress-every must be nonnegative')

    if args.output.resolve() == args.source.resolve():
        parser.error('--output must not overwrite the stable source')
    if args.reference and args.output.resolve() == args.reference.resolve():
        parser.error('--output must not overwrite the reference catalog')
    stable = load_stable(args.source)
    print('ODD-LEG experimental v0.22.0 / 1000B arithmetic (full search capped at 2B pending runner audit)', flush=True)
    print(f'Bound={args.max_edge:,}; stable source={args.source}', flush=True)
    t0 = time.perf_counter()
    # Import the already-tested segmented SPF implementation from the active src directory without requiring package installation.
    from segmented_factorization import odd_spf_segment, primes_upto
    ts = time.perf_counter()
    base_primes = np.asarray(primes_upto(math.isqrt(args.max_edge)), dtype=np.int64)
    print(f'Base primes: {len(base_primes):,}; setup: {time.perf_counter()-ts:.3f}s', flush=True)
    # Compile with a real SPF segment containing odd=3.
    warm_spf = np.asarray(odd_spf_segment(3, 101, base_primes), dtype=np.uint32)
    tc = time.perf_counter()
    fused_segment_kernel(3, 101, 100, warm_spf, base_primes)
    print(f'Numba compilation: {time.perf_counter()-tc:.3f}s', flush=True)

    bricks = set()
    tested_total = rejected_total = 0
    kernel_seconds = verification_seconds = 0.0
    kernel_calls = 0
    tsearch = time.perf_counter()
    segment_seconds = 0.0
    segments = 0
    # odd=1 has no compatible legs. Start at 3, preserving all candidates.
    for lo in range(3, args.max_edge + 1, 2 * args.segment_odds):
        hi = min(args.max_edge, lo + 2 * (args.segment_odds - 1))
        ts = time.perf_counter()
        spf_view = np.asarray(odd_spf_segment(lo, hi, base_primes), dtype=np.uint32)
        segment_seconds += time.perf_counter() - ts
        segments += 1
        if args.progress_every:
            # Preserve v0.17.0's exact odd-level progress semantics.
            # Progress-enabled runs intentionally use the original per-odd
            # dispatch; normal benchmark runs use the segment-level kernel.
            for odd in range(lo, hi + 1, 2):
                t = time.perf_counter()
                pairs, tested, rejected = fused_odd_kernel(
                    odd, args.max_edge, spf_view, lo, base_primes
                )
                kernel_seconds += time.perf_counter() - t
                kernel_calls += 1
                tested_total += tested
                rejected_total += rejected
                if pairs:
                    t = time.perf_counter()
                    for e1, e2 in pairs:
                        triple = tuple(sorted((int(odd), int(e1), int(e2))))
                        if not stable.verify_brick(triple, args.max_edge):
                            raise AssertionError(f'Invalid Numba candidate: {triple}')
                        bricks.add(triple)
                    verification_seconds += time.perf_counter() - t
                if odd % args.progress_every == 1:
                    print(f'odd={odd:,}; bricks={len(bricks)}', flush=True)
        else:
            t = time.perf_counter()
            matches, tested, rejected = fused_segment_kernel(
                lo, hi, args.max_edge, spf_view, base_primes
            )
            kernel_seconds += time.perf_counter() - t
            kernel_calls += 1
            tested_total += tested
            rejected_total += rejected
            if matches:
                t = time.perf_counter()
                for odd, e1, e2 in matches:
                    triple = tuple(sorted((int(odd), int(e1), int(e2))))
                    if not stable.verify_brick(triple, args.max_edge):
                        raise AssertionError(f'Invalid Numba candidate: {triple}')
                    bricks.add(triple)
                verification_seconds += time.perf_counter() - t

    search_seconds = time.perf_counter() - tsearch
    print(f'Search time: {search_seconds:.3f}s', flush=True)
    print(f'Segment construction: {segment_seconds:.3f}s; segments={segments:,}')
    print(f'Segment SPF peak allocation: <= {4*args.segment_odds:,} bytes (excluding overhead)')
    print('Memory note: SPF bound excludes Numba match lists, arrays, and runtime overhead.')
    print(f'Fused Numba kernel: {kernel_seconds:.3f}s; calls={kernel_calls:,}')
    if args.progress_every:
        print('Progress mode: original per-odd dispatch (not a segment benchmark).')
    print(f'Candidate verification: {verification_seconds:.3f}s')
    print('Timing categories exclude Python loop/accounting overhead.')
    print(f'Primitive Euler bricks: {len(bricks)}')
    print(f'Primitive candidate pairs: {tested_total:,}')
    print(f'Rejected nonprimitive: {rejected_total:,}')
    perfect = sum(stable.is_square(a*a+b*b+c*c) for a,b,c in bricks)
    print(f'Perfect cuboids: {perfect}')

    if args.reference:
        reference = stable.load_reference(args.reference, args.max_edge)
        missing, extra = reference - bricks, bricks - reference
        print(f'REFERENCE expected={len(reference)} missing={len(missing)} extra={len(extra)}')
        if missing or extra:
            print(f'Missing examples: {sorted(missing)[:5]}')
            print(f'Extra examples: {sorted(extra)[:5]}')
            print('REFERENCE MISMATCH - output not written')
            return 1
        print('EXACT SET MATCH')

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(('a', 'b', 'c'))
        writer.writerows(sorted(bricks, key=lambda t: (t[2], t[0], t[1])))
    print(f'Output: {args.output}')
    print(f'Total elapsed (including compilation): {time.perf_counter()-t0:.3f}s')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
