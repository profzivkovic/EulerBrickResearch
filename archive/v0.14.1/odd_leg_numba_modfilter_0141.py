#!/usr/bin/env python3
"""EulerBrickResearch v0.14.1: benchmark exact quadratic-residue prefilters against v0.10.4.

Requires numpy and numba. Imports v0.9.9 for SPF, independent verification and reference handling.
Does not modify the stable implementation or verified catalog.
"""
import argparse
import csv
import importlib.util
import math
import time
from pathlib import Path

import numpy as np
from numba import njit

# mode: 0 baseline, 1 mod64, 2 mod256, 3 mod5, 4 mod256+5
Q64 = np.zeros(64, dtype=np.uint8)
Q256 = np.zeros(256, dtype=np.uint8)
Q5 = np.zeros(5, dtype=np.uint8)
for _i in range(256):
    Q64[(_i * _i) & 63] = 1
    Q256[(_i * _i) & 255] = 1
    Q5[(_i * _i) % 5] = 1

MAX_SAFE_BOUND = 1_000_000_000  # 3*B**2 <= 3e18 < 2**63-1


@njit(cache=True)
def compatible_even_legs_jit(odd, bound, spf):
    """Generate every e<=bound from divisors d<odd of odd**2 (Numba int64)."""
    if odd <= 1:
        return np.empty(0, dtype=np.int64)
    n = odd
    primes = []
    exponents = []
    while n > 1:
        prime = int(spf[n])
        exponent = 0
        while n % prime == 0:
            n //= prime
            exponent += 1
        primes.append(prime)
        exponents.append(exponent)
    divisors = [1]
    odd_squared = odd * odd
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
                    e = (odd_squared // value - value) // 2
                    if 0 < e <= bound:
                        legs.append(e)
                    value *= prime
            return np.asarray(legs, dtype=np.int64)
        next_divisors = []
        for d in divisors:
            value = d
            for _ in range(2 * exponent + 1):
                if value >= odd:
                    break
                next_divisors.append(value)
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
def fused_odd_kernel(odd, bound, spf, mode, q64, q256, q5):
    """Generate legs, partition, and check all admissible primitive pairs in JIT."""
    legs = compatible_even_legs_jit(odd, bound, spf)
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
    skipped = 0
    if odd % 3 == 0:
        for e1 in div:
            g1 = math.gcd(odd, e1)
            sq1 = e1 * e1
            for e2 in nondiv:
                if math.gcd(g1, e2) != 1:
                    rejected += 1
                    continue
                tested += 1
                n = sq1 + e2 * e2
                if mode == 1 and q64[n & 63] == 0:
                    skipped += 1
                    continue
                if (mode == 2 or mode == 4) and q256[n & 255] == 0:
                    skipped += 1
                    continue
                if (mode == 3 or mode == 4) and q5[n % 5] == 0:
                    skipped += 1
                    continue
                r = integer_sqrt64(n)
                if r * r == n:
                    matches.append((e1, e2))
    else:
        for i in range(len(div)):
            e1 = div[i]
            g1 = math.gcd(odd, e1)
            sq1 = e1 * e1
            for j in range(i + 1, len(div)):
                e2 = div[j]
                if math.gcd(g1, e2) != 1:
                    rejected += 1
                    continue
                tested += 1
                n = sq1 + e2 * e2
                if mode == 1 and q64[n & 63] == 0:
                    skipped += 1
                    continue
                if (mode == 2 or mode == 4) and q256[n & 255] == 0:
                    skipped += 1
                    continue
                if (mode == 3 or mode == 4) and q5[n % 5] == 0:
                    skipped += 1
                    continue
                r = integer_sqrt64(n)
                if r * r == n:
                    matches.append((e1, e2))
    return matches, tested, rejected, skipped


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
    parser.add_argument('--filter', choices=('baseline','mod64','mod256','mod5','mod256+5'), default='baseline')
    parser.add_argument('--source', type=Path, default=Path('src/odd_leg_search.py'))
    parser.add_argument('--max-edge', type=int, required=True)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--catalog', type=Path, help='Canonical 1B CSV; automatically filter c <= max-edge')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--progress-every', type=int, default=0)
    args = parser.parse_args()
    if not 1 <= args.max_edge <= MAX_SAFE_BOUND:
        parser.error(f'--max-edge must be in 1..{MAX_SAFE_BOUND} for int64 safety')
    if args.progress_every < 0:
        parser.error('--progress-every must be nonnegative')

    stable = load_stable(args.source)
    print(f'ODD-LEG modular benchmark v0.14.1; filter={args.filter}', flush=True)
    print(f'Bound={args.max_edge:,}; stable source={args.source}', flush=True)
    t0 = time.perf_counter()
    ts = time.perf_counter()
    spf = stable.build_spf(args.max_edge)
    print(f'SPF sieve: {time.perf_counter()-ts:.3f}s', flush=True)
    spf_view = np.frombuffer(spf, dtype=np.uint32)
    tc = time.perf_counter()
    mode = {'baseline':0,'mod64':1,'mod256':2,'mod5':3,'mod256+5':4}[args.filter]
    fused_odd_kernel(3, 100, spf_view, mode, Q64, Q256, Q5)
    print(f'Numba compilation: {time.perf_counter()-tc:.3f}s', flush=True)

    bricks = set()
    tested_total = rejected_total = skipped_total = 0
    kernel_seconds = verification_seconds = 0.0
    kernel_calls = 0
    tsearch = time.perf_counter()
    for odd in range(1, args.max_edge + 1, 2):
        t = time.perf_counter()
        pairs, tested, rejected, skipped = fused_odd_kernel(odd, args.max_edge, spf_view, mode, Q64, Q256, Q5)
        skipped_total += skipped
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
        if args.progress_every and odd % args.progress_every == 1:
            print(f'odd={odd:,}; bricks={len(bricks)}', flush=True)

    search_seconds = time.perf_counter() - tsearch
    print(f'Search time: {search_seconds:.3f}s', flush=True)
    print(f'Fused Numba kernel: {kernel_seconds:.3f}s; calls={kernel_calls:,}')
    print(f'Candidate verification: {verification_seconds:.3f}s')
    print('Timing categories exclude Python loop/accounting overhead.')
    print(f'Primitive Euler bricks: {len(bricks)}')
    print(f'Primitive candidate pairs: {tested_total:,}')
    print(f'Rejected nonprimitive: {rejected_total:,}')
    print(f'Modular rejects before isqrt: {skipped_total:,}')
    print(f'Integer-sqrt calls: {tested_total - skipped_total:,}')
    print(f'Modular rejection rate: {100*skipped_total/tested_total if tested_total else 0:.4f}%')
    perfect = sum(stable.is_square(a*a+b*b+c*c) for a,b,c in bricks)
    print(f'Perfect cuboids: {perfect}')

    if args.catalog:
        with args.catalog.open(newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            expected = {tuple(int(row[k]) for k in ('a','b','c')) for row in reader if int(row['c']) <= args.max_edge}
        missing, extra = expected - bricks, bricks - expected
        print(f'CATALOG expected={len(expected)} missing={len(missing)} extra={len(extra)}')
        if missing or extra:
            print(f'Missing examples: {sorted(missing)[:5]}')
            print(f'Extra examples: {sorted(extra)[:5]}')
            print('CATALOG MISMATCH - output not written')
            return 1
        print('EXACT SET MATCH')

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
