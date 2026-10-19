#!/usr/bin/env python3
"""Independent bounded audit of EulerBrickResearch odd-leg v0.9.9.

Standard library only. Does not modify source, reference data, or output CSVs.
"""
import argparse
import importlib.util
import math
import random
from collections import defaultdict
from pathlib import Path


def load_engine(path):
    spec = importlib.util.spec_from_file_location('audited_odd_leg', path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Cannot import {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def independent_legs(odd, bound):
    """Direct integer-square testing; independent of factorization and SPF."""
    out = set()
    for e in range(2, bound + 1, 2):
        s = odd * odd + e * e
        r = math.isqrt(s)
        if r * r == s:
            out.add(e)
    return out


def graph_bricks(bound):
    """Independent Pythagorean-pair graph enumerator, no odd-leg divisors."""
    neighbors = defaultdict(set)
    for a in range(1, bound + 1):
        for b in range(a + 1, bound + 1):
            s = a*a + b*b
            r = math.isqrt(s)
            if r*r == s:
                neighbors[a].add(b)
                neighbors[b].add(a)
    result = set()
    for a in range(1, bound + 1):
        larger = sorted(b for b in neighbors[a] if b > a)
        for i, b in enumerate(larger):
            for c in larger[i+1:]:
                if c in neighbors[b] and math.gcd(math.gcd(a,b),c) == 1:
                    result.add((a,b,c))
    return result


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('src/odd_leg_search.py'))
    parser.add_argument('--max-edge', type=int, default=1000)
    parser.add_argument('--samples', type=int, default=150)
    args = parser.parse_args()
    if args.max_edge < 2 or args.samples < 0:
        parser.error('--max-edge must be >=2 and --samples must be >=0')
    engine = load_engine(args.source)
    B = args.max_edge
    print(f'AUDIT source={args.source}; version={engine.VERSION}; bound={B}', flush=True)
    spf = engine.build_spf(B)
    checked = 0
    # Full coverage of odd legs at the selected small bound.
    for odd in range(1, B+1, 2):
        got_list = engine.compatible_even_legs(odd, B, spf)
        got = set(got_list)
        expected = independent_legs(odd, B)
        check(len(got_list) == len(got), f'Duplicate legs for odd={odd}')
        check(got == expected, f'Leg mismatch odd={odd}: missing={sorted(expected-got)} extra={sorted(got-expected)}')
        checked += 1
    print(f'PASS compatible legs: {checked} odd values (independent square tests)', flush=True)

    # Extra factorization/divisor checks with independent trial division on sampled odds.
    rng = random.Random(20261019)
    sample_odds = [rng.randrange(1, B+1) | 1 for _ in range(args.samples)]
    sample_odds = [o if o <= B else o-2 for o in sample_odds]
    check(engine.divisors_below_root(1, []) == [1],
          'Unexpected odd=1 helper convention')
    check(engine.compatible_even_legs(1, B, spf) == [],
          'odd=1 must have no compatible even legs')
    for odd in sample_odds:
        if odd == 1:
            continue  # The helper's [1] seed is not a divisor strictly below 1.
        factors = engine.factorize(odd, spf)
        reconstructed = math.prod(p**k for p,k in factors)
        check(reconstructed == odd, f'Factorization mismatch odd={odd}')
        divisors = engine.divisors_below_root(odd, factors)
        brute = {u for u in range(1, odd) if odd*odd % u == 0}
        check(set(divisors) == brute and len(divisors) == len(brute), f'Divisor mismatch odd={odd}')
    print(f'PASS bounded divisors: {sum(o > 1 for o in sample_odds)} reproducible samples; odd=1 separately checked', flush=True)

    expected = graph_bricks(B)
    actual, stats = engine.search(B, 0)
    missing, extra = expected - actual, actual - expected
    check(not missing and not extra, f'Brick mismatch: missing={sorted(missing)[:10]}, extra={sorted(extra)[:10]}')
    check(stats['primitive_pairs'] == stats['isqrt_calls'], 'Primitive pair / isqrt count mismatch')
    check(stats['partition_pairs'] == stats['primitive_pairs'] + stats['rejected_nonprimitive'], 'Pair accounting mismatch')
    check(stats['all_possible_pairs'] >= stats['partition_pairs'], 'Partition accounting mismatch')
    for a,b,c in actual:
        odd = next(x for x in (a,b,c) if x % 2)
        evens = [x for x in (a,b,c) if x % 2 == 0]
        check(len(evens) == 2, f'Parity mismatch {(a,b,c)}')
        check(sum(x % 3 == 0 for x in (a,b,c)) == 2, f'Mod3 mismatch {(a,b,c)}')
        check(engine.verify_brick((a,b,c), B), f'Verification mismatch {(a,b,c)}')
    print(f'PASS independent graph enumeration: {len(actual)} primitive bricks, exact set match', flush=True)
    print('PASS pair accounting, parity, modulo-3 and row verification', flush=True)
    print('NUMERIC: Python int and math.isqrt are arbitrary-precision; SPF array(I) is for indices/factors only.')
    print('LIMITATION: This audit tests finite small bounds; it is not a formal proof of all implementation paths.')
    print('AUDIT PASSED')


if __name__ == '__main__':
    main()
