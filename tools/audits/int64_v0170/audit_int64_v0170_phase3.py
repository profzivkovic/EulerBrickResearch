#!/usr/bin/env python3
"""EulerBrickResearch v0.17.0 / phase 3: divisor uniqueness and counter audit.

Read-only. No full search, no changes to stable sources or bound.
Run from repo root:
    python tools/audit_int64_v0170_phase3.py --max-edge 2000000000 --samples 256
"""
from __future__ import annotations

import argparse
import importlib.util
import math
import random
import sys
from pathlib import Path

import numpy as np

INT64_MAX = (1 << 63) - 1
LIMIT = 2_000_000_000


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Cannot load {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reference_legs(odd: int, bound: int) -> list[int]:
    """Independent big-int reference: factor odd by trial division, enumerate odd**2 divisors."""
    n = odd
    factors = []
    p = 3
    while p * p <= n:
        if n % p == 0:
            k = 0
            while n % p == 0:
                n //= p
                k += 1
            factors.append((p, k))
        p += 2
    if n > 1:
        factors.append((n, 1))
    divisors = [1]
    for p, k in factors:
        divisors = [d * p**j for d in divisors for j in range(2 * k + 1)]
        assert len(divisors) == len(set(divisors)), 'duplicate divisors in reference'
    square = odd * odd
    legs = [(square // d - d) // 2 for d in divisors if d < odd]
    legs = [e for e in legs if 0 < e <= bound]
    assert len(legs) == len(set(legs)), 'duplicate legs in reference'
    return sorted(legs)


def reference_counts(odd: int, legs: list[int]) -> tuple[int, int, list[tuple[int, int]]]:
    div = [e for e in legs if e % 3 == 0]
    nondiv = [e for e in legs if e % 3 != 0] if odd % 3 == 0 else []
    candidates = ((a, b) for a in div for b in nondiv) if odd % 3 == 0 else (
        (div[i], div[j]) for i in range(len(div)) for j in range(i + 1, len(div))
    )
    tested = rejected = 0
    matches = []
    for a, b in candidates:
        if math.gcd(math.gcd(odd, a), b) != 1:
            rejected += 1
            continue
        tested += 1
        s = a * a + b * b
        if math.isqrt(s) ** 2 == s:
            matches.append((a, b))
    return tested, rejected, matches


def sample_odds(bound: int, count: int, seed: int) -> list[int]:
    rng = random.Random(seed)
    anchors = [3, 5, 7, 9, 15, 45, 105, 315, 945, 10395,
               3**17, 5**13, 7**11, 999999937, 1000000001,
               1999999999, 1999999997, 1999999995, 1999999993]
    selected = {x for x in anchors if 3 <= x <= bound and x % 2}
    selected.add(bound if bound % 2 else bound - 1)
    while len(selected) < min(count, (bound - 1) // 2):
        selected.add(2 * rng.randrange(1, (bound - 1) // 2 + 1) + 1)
    return sorted(selected)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument('--max-edge', type=int, default=LIMIT)
    ap.add_argument('--samples', type=int, default=256)
    ap.add_argument('--seed', type=int, default=1703)
    args = ap.parse_args()
    if not 3 <= args.max_edge <= LIMIT or args.samples < 1:
        ap.error('max-edge must be 3..2B and samples must be positive')
    src = args.repo_root.resolve() / 'src'
    sys.path.insert(0, str(src))
    kernel = load(src / 'odd_leg_numba_segmented.py', 'audit_phase3_kernel')
    helper = load(src / 'segmented_factorization.py', 'audit_phase3_helper')
    assert kernel.MAX_SAFE_BOUND == 1_000_000_000, 'Stable bound changed!'
    bound = args.max_edge
    print('NUMERICAL AUDIT v0.17.0 / PHASE 3 (read-only)')
    print(f'Bound={bound:,}; stable MAX_SAFE_BOUND={kernel.MAX_SAFE_BOUND:,}')

    # A leg e corresponds to exactly one divisor d because e=(odd**2/d-d)/2
    # strictly decreases with positive d. Unique prime factorization generates
    # every divisor exactly once; the test below checks the implementation.
    max_legs = bound // 2
    max_pairs = max_legs * (max_legs - 1) // 2
    assert max_pairs <= INT64_MAX
    assert 2 * bound * bound <= INT64_MAX
    print(f'Counter bound C(floor(B/2),2)={max_pairs:,} < int64 max: PASS')
    print('Each pair belongs to exactly one of tested/rejected; sum <= pair bound.')
    print('Proof condition: unique legs, distinct pair iteration, 0 < even leg <= B.')

    primes = np.asarray(helper.primes_upto(math.isqrt(bound)), dtype=np.int64)
    odds = sample_odds(bound, args.samples, args.seed)
    total_legs = total_tested = total_rejected = total_matches = 0
    for index, odd in enumerate(odds, 1):
        # A single-entry segment isolates the odd being tested and exercises
        # the same SPF/Numba entry points as the segmented search.
        spf = np.asarray(helper.odd_spf_segment(odd, odd, primes), dtype=np.uint32)
        actual = list(map(int, kernel.compatible_even_legs_jit(
            np.int64(odd), np.int64(bound), spf, np.int64(odd), primes)))
        expected = reference_legs(odd, bound)
        assert len(actual) == len(set(actual)), f'odd={odd}: duplicate Numba legs'
        assert sorted(actual) == expected, f'odd={odd}: leg mismatch'
        matches, tested, rejected = kernel.fused_odd_kernel(
            np.int64(odd), np.int64(bound), spf, np.int64(odd), primes)
        ref_tested, ref_rejected, ref_matches = reference_counts(odd, expected)
        assert (int(tested), int(rejected)) == (ref_tested, ref_rejected), (
            f'odd={odd}: counter mismatch')
        assert sorted(map(tuple, matches)) == sorted(ref_matches), f'odd={odd}: match mismatch'
        assert 0 <= int(tested) + int(rejected) <= max_pairs
        total_legs += len(actual)
        total_tested += int(tested)
        total_rejected += int(rejected)
        total_matches += len(matches)
        if index % 50 == 0 or index == len(odds):
            print(f'Checked {index}/{len(odds)} odds: PASS')
    print(f'PASS: {len(odds)} odds, {total_legs} unique legs, '
          f'{total_tested} tested, {total_rejected} rejected, {total_matches} matches')
    print('LIMITATIONS: sampled implementation checks, not exhaustive search;')
    print('mathematical uniqueness relies on correct distinct prime factorization.')
    print('Do NOT modify stable MAX_SAFE_BOUND or promote a prototype yet.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
