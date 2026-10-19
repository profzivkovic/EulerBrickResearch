#!/usr/bin/env python3
"""Experimental EulerBrickResearch v0.10.0: Numba pair-check kernel.

Requires numpy and numba. Imports v0.9.9 for SPF and compatible-leg generation.
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

MAX_SAFE_BOUND = 1_000_000_000  # conservative: 3*B**2 fits signed int64


@njit(cache=True)
def integer_sqrt64(n):
    """Exact floor sqrt for 0 <= n <= 3e18, using float estimate + correction."""
    r = int(math.sqrt(n))
    while (r + 1) * (r + 1) <= n:
        r += 1
    while r * r > n:
        r -= 1
    return r


@njit(cache=True)
def check_pairs(odd, divisible, nondivisible):
    """Return matching (e1,e2) pairs and (tested, rejected) counts."""
    matches = []
    tested = 0
    rejected = 0
    if odd % 3 == 0:
        for i in range(len(divisible)):
            e1 = divisible[i]
            g1 = math.gcd(odd, e1)
            sq1 = e1 * e1
            for j in range(len(nondivisible)):
                e2 = nondivisible[j]
                if math.gcd(g1, e2) != 1:
                    rejected += 1
                    continue
                tested += 1
                n = sq1 + e2 * e2
                r = integer_sqrt64(n)
                if r * r == n:
                    matches.append((e1, e2))
    else:
        for i in range(len(divisible)):
            e1 = divisible[i]
            g1 = math.gcd(odd, e1)
            sq1 = e1 * e1
            for j in range(i + 1, len(divisible)):
                e2 = divisible[j]
                if math.gcd(g1, e2) != 1:
                    rejected += 1
                    continue
                tested += 1
                n = sq1 + e2 * e2
                r = integer_sqrt64(n)
                if r * r == n:
                    matches.append((e1, e2))
    return matches, tested, rejected


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
    args = parser.parse_args()
    if not 1 <= args.max_edge <= MAX_SAFE_BOUND:
        parser.error(f'--max-edge must be in 1..{MAX_SAFE_BOUND} for int64 safety')
    if args.progress_every < 0:
        parser.error('--progress-every must be nonnegative')

    stable = load_stable(args.source)
    print('ODD-LEG experimental v0.10.0 / Numba pair kernel', flush=True)
    print(f'Bound={args.max_edge:,}; stable source={args.source}', flush=True)
    t0 = time.perf_counter()
    # Compile before benchmarking; compilation time is reported separately.
    tc = time.perf_counter()
    check_pairs(3, np.empty(0, dtype=np.int64), np.empty(0, dtype=np.int64))
    print(f'Numba compilation: {time.perf_counter()-tc:.3f}s', flush=True)
    ts = time.perf_counter()
    spf = stable.build_spf(args.max_edge)
    print(f'SPF sieve: {time.perf_counter()-ts:.3f}s', flush=True)

    bricks = set()
    tested_total = rejected_total = 0
    tsearch = time.perf_counter()
    for odd in range(1, args.max_edge + 1, 2):
        legs = stable.compatible_even_legs(odd, args.max_edge, spf)
        if len(legs) < 2:
            continue
        div = np.asarray([e for e in legs if e % 3 == 0], dtype=np.int64)
        nondiv = np.asarray([e for e in legs if e % 3 != 0], dtype=np.int64)
        pairs, tested, rejected = check_pairs(odd, div, nondiv)
        tested_total += tested
        rejected_total += rejected
        for e1, e2 in pairs:
            triple = tuple(sorted((int(odd), int(e1), int(e2))))
            if not stable.verify_brick(triple, args.max_edge):
                raise AssertionError(f'Invalid Numba candidate: {triple}')
            bricks.add(triple)
        if args.progress_every and odd % args.progress_every == 1:
            print(f'odd={odd:,}; bricks={len(bricks)}', flush=True)

    print(f'Search time: {time.perf_counter()-tsearch:.3f}s', flush=True)
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
