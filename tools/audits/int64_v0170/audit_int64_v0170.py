#!/usr/bin/env python3
"""EulerBrickResearch v0.17.0: bounded int64 audit for segmented v0.16.0.

Read-only test tool: does not change src/, the verified catalog, or MAX_SAFE_BOUND.
This is a targeted numerical regression audit, NOT a proof of safety for all
inputs and NOT a full Euler-brick search to the requested bound.

Run from repository root:
    python tools/audit_int64_v0170.py
    python tools/audit_int64_v0170.py --max-edge 2000000000 --random-samples 64
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
DEFAULT_BOUND = 2_000_000_000


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def factor_odd_python(n: int, base_primes: list[int]) -> list[tuple[int, int]]:
    result = []
    remainder = n
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
            result.append((p, exponent))
    if remainder > 1:
        result.append((remainder, 1))
    return result


def reference_legs(odd: int, bound: int, base_primes: list[int]) -> list[int]:
    """Independent Python big-int implementation, no NumPy/Numba arithmetic."""
    if odd <= 1:
        return []
    divisors = [1]
    for p, exponent in factor_odd_python(odd, base_primes):
        divisors = [d * p**k for d in divisors for k in range(2 * exponent + 1)
                    if d * p**k < odd]
    odd_sq = odd * odd
    return sorted((odd_sq // d - d) // 2 for d in divisors
                  if 0 < (odd_sq // d - d) // 2 <= bound)


def check_sqrt(kernel, bound: int) -> int:
    values = {0, 1, 2, 3, 4, 8, 9, 15, 16, 17, INT64_MAX,
              min(INT64_MAX, 2 * bound * bound), bound * bound}
    for root in [1, 2, 3, 46340, 2**26, 2**31 - 1, 2**31, math.isqrt(INT64_MAX)]:
        square = root * root
        for delta in (-2, -1, 0, 1, 2):
            candidate = square + delta
            if 0 <= candidate <= INT64_MAX:
                values.add(candidate)
    for n in sorted(values):
        actual = int(kernel.integer_sqrt64(np.int64(n)))
        expected = math.isqrt(n)
        if actual != expected:
            raise AssertionError(f"integer_sqrt64({n}): {actual} != {expected}")
    return len(values)


def sample_odds(bound: int, random_samples: int, seed: int) -> list[int]:
    rng = random.Random(seed)
    candidates = {3, 5, 7, 9, 15, 27, 81, 315, 65535, 999999937,
                  999999999, 1000000001, 1073741823, 1073741825,
                  1999999991, 1999999993, 1999999997, 1999999999}
    for offset in range(1, 100, 2):
        candidates.add(bound - offset if (bound - offset) % 2 else bound - offset - 1)
    for _ in range(random_samples):
        candidates.add(rng.randrange(3, bound + 1, 2))
    return sorted(n for n in candidates if 3 <= n <= bound and n % 2 == 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-edge', type=int, default=DEFAULT_BOUND)
    parser.add_argument('--random-samples', type=int, default=24)
    parser.add_argument('--seed', type=int, default=1700)
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    if not 3 <= args.max_edge <= DEFAULT_BOUND:
        parser.error('This audit is scoped to max-edge in 3..2,000,000,000')
    if args.random_samples < 0:
        parser.error('--random-samples must be nonnegative')

    root = args.repo_root.resolve()
    src = root / 'src'
    sys.path.insert(0, str(src))
    kernel = load_module(src / 'odd_leg_numba_segmented.py', 'segmented_v0160_audit')
    helper = load_module(src / 'segmented_factorization.py', 'spf_helper_audit')
    if kernel.MAX_SAFE_BOUND != 1_000_000_000:
        print(f"WARNING: active MAX_SAFE_BOUND is {kernel.MAX_SAFE_BOUND:,}, expected 1B")

    bound = args.max_edge
    print('NUMERICAL AUDIT v0.17.0 (read-only, targeted)', flush=True)
    print(f'Bound={bound:,}; Python reference uses arbitrary-precision integers', flush=True)
    assert 2 * bound * bound <= INT64_MAX, 'Pairwise squared sum exceeds int64'
    assert bound * bound <= INT64_MAX, 'Odd square exceeds int64'
    print(f'Max pairwise sum: {2 * bound * bound:,} / int64 max {INT64_MAX:,}')
    print('Note: three-square sum is checked only in Python big-int verifier.')

    sqrt_count = check_sqrt(kernel, bound)
    print(f'integer_sqrt64: {sqrt_count} boundary cases PASS', flush=True)
    primes = helper.primes_upto(math.isqrt(bound))
    primes_np = np.asarray(primes, dtype=np.int64)
    odds = sample_odds(bound, args.random_samples, args.seed)
    checked_legs = 0
    for i, odd in enumerate(odds, 1):
        spf = np.asarray(helper.odd_spf_segment(odd, odd, primes), dtype=np.uint32)
        first = int(spf[0])
        factors = factor_odd_python(odd, primes)
        expected_first = factors[0][0] if factors[0][0] != odd else 0
        if first != expected_first:
            raise AssertionError(f'SPF mismatch odd={odd}: {first} != {expected_first}')
        actual = sorted(int(x) for x in kernel.compatible_even_legs_jit(
            np.int64(odd), np.int64(bound), spf, np.int64(odd), primes_np))
        expected = reference_legs(odd, bound, primes)
        if actual != expected:
            raise AssertionError(f'Leg mismatch odd={odd}: {actual[:10]} != {expected[:10]}')
        checked_legs += len(actual)
        if i % 25 == 0 or i == len(odds):
            print(f'Factorization/legs: {i}/{len(odds)} odd samples PASS', flush=True)

    # Probe fused kernel on a small odd value but with the 2B bound, so the
    # arithmetic path uses the intended high-bound argument type.
    spf3 = np.asarray(helper.odd_spf_segment(3, 3, primes), dtype=np.uint32)
    pairs, tested, rejected = kernel.fused_odd_kernel(
        np.int64(3), np.int64(bound), spf3, np.int64(3), primes_np)
    assert int(tested) >= 0 and int(rejected) >= 0
    print(f'Fused kernel smoke test: pairs={len(pairs)}, tested={tested}, rejected={rejected} PASS')
    print('Compiled Numba signatures:')
    for name in ('integer_sqrt64', 'compatible_even_legs_jit', 'fused_odd_kernel'):
        obj = getattr(kernel, name)
        print(f'  {name}: {obj.signatures}')
    print(f'PASS: {len(odds)} sampled odds, {checked_legs} compatible legs; no full search')
    print('LIMITATIONS: sample-based only; no exhaustive proof, counter-overflow proof,')
    print('or verification of every Numba intermediate type. Do not raise MAX_SAFE_BOUND yet.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
