"""EulerBrickResearch v0.15.0: independent segmented odd SPF prototype.

No changes to stable search or verified catalog.
"""
from __future__ import annotations

import argparse
import math
import random
import time
from array import array


def primes_upto(limit: int) -> list[int]:
    if limit < 2:
        return []
    sieve = bytearray(b'\x01') * (limit + 1)
    sieve[0:2] = b'\x00\x00'
    for p in range(2, math.isqrt(limit) + 1):
        if sieve[p]:
            sieve[p * p :: p] = b'\x00' * (((limit - p * p) // p) + 1)
    return [p for p in range(2, limit + 1) if sieve[p]]


def odd_spf_segment(lo: int, hi: int, base_primes: list[int]) -> array:
    """Return SPF for odd integers in inclusive [lo, hi]; lo must be odd >= 3.

    Entry i corresponds to lo+2*i. Zero means that integer is prime.
    """
    if lo < 3 or lo % 2 == 0 or hi < lo:
        raise ValueError('Require odd lo >= 3 and hi >= lo')
    count = ((hi - lo) // 2) + 1
    spf = array('I', [0]) * count
    for p in base_primes:
        if p == 2:
            continue
        if p * p > hi:
            break
        start = max(p * p, ((lo + p - 1) // p) * p)
        if start % 2 == 0:
            start += p
        for n in range(start, hi + 1, 2 * p):
            idx = (n - lo) // 2
            if spf[idx] == 0:
                spf[idx] = p
    return spf


def factors_from_segment(n: int, lo: int, spf: array, base_primes: list[int]) -> list[tuple[int, int]]:
    """Factor an odd n using segment SPF for first factor, then base primes.

    This reference implementation favors clarity; Numba integration comes later.
    """
    if n < lo or n > lo + 2 * (len(spf) - 1) or n % 2 == 0:
        raise ValueError('n must be an odd integer within the segment')
    first = spf[(n - lo) // 2]
    if first == 0:
        return [(n, 1)]
    remainder = n
    factors: list[tuple[int, int]] = []
    for p in base_primes:
        if p == 2:
            continue
        if p * p > remainder:
            break
        if remainder % p == 0:
            exponent = 0
            while remainder % p == 0:
                remainder //= p
                exponent += 1
            factors.append((p, exponent))
    if remainder > 1:
        factors.append((remainder, 1))
    return factors


def reference_factors(n: int) -> list[tuple[int, int]]:
    result = []
    p = 3
    while p * p <= n:
        if n % p == 0:
            e = 0
            while n % p == 0:
                n //= p
                e += 1
            result.append((p, e))
        p += 2
    if n > 1:
        result.append((n, 1))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description='v0.15.0 segmented odd-SPF correctness prototype')
    parser.add_argument('--max-odd', type=int, default=1_000_000)
    parser.add_argument('--segment-odds', type=int, default=100_000)
    parser.add_argument('--samples-per-segment', type=int, default=100)
    parser.add_argument('--exhaustive', action='store_true', help='Verify every odd n (best for <= 1M)')
    args = parser.parse_args()
    if args.max_odd < 3 or args.segment_odds < 1 or args.samples_per_segment < 0:
        parser.error('Invalid bound, segment size or sample count')
    bound = args.max_odd if args.max_odd % 2 else args.max_odd - 1
    primes = primes_upto(math.isqrt(bound))
    rng = random.Random(1500)
    checked = 0
    segments = 0
    t0 = time.perf_counter()
    for lo in range(3, bound + 1, 2 * args.segment_odds):
        hi = min(bound, lo + 2 * (args.segment_odds - 1))
        spf = odd_spf_segment(lo, hi, primes)
        size = len(spf)
        if args.exhaustive:
            indices = range(size)
        else:
            indices = sorted(set([0, size - 1, size // 2] +
                                 [rng.randrange(size) for _ in range(args.samples_per_segment)]))
        for idx in indices:
            n = lo + 2 * idx
            actual = factors_from_segment(n, lo, spf, primes)
            expected = reference_factors(n)
            if actual != expected:
                raise AssertionError(f'MISMATCH n={n} segment=[{lo},{hi}]: {actual} != {expected}')
            if math.prod(p ** e for p, e in actual) != n:
                raise AssertionError(f'PRODUCT MISMATCH n={n}')
            checked += 1
        segments += 1
    print('SEGMENTED FACTORIZATION v0.15.0')
    print(f'Max odd: {bound:,}; segment odds: {args.segment_odds:,}')
    print(f'Segments: {segments:,}; checked: {checked:,}; exhaustive: {args.exhaustive}')
    print(f'Base primes: {len(primes):,}; elapsed: {time.perf_counter()-t0:.3f}s')
    print('FACTORIZATION EXACT MATCH')


if __name__ == '__main__':
    main()
