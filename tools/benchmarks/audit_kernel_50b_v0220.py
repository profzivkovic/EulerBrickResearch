"""Read-only targeted 50B arithmetic and kernel audit (NOT full-search approval)."""
from __future__ import annotations
import argparse
import math
import random
import sys
from pathlib import Path
import numpy as np
from numba import njit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import segmented_factorization as factor
import odd_leg_numba_1000b_experimental as engine
import safe_arithmetic_1000b as arith

BOUND = 50_000_000_000
@njit(cache=False)
def spf_numba_core(lo, hi, primes):
    count = (hi - lo) // 2 + 1
    spf = np.zeros(count, dtype=np.uint32)
    for j in range(primes.size):
        p = np.int64(primes[j])
        if p == 2:
            continue
        if p * p > hi:
            break
        start = ((lo + p - 1) // p) * p
        if start < p * p:
            start = p * p
        if start % 2 == 0:
            start += p
        for n in range(start, hi + 1, 2 * p):
            idx = (n - lo) // 2
            if spf[idx] == 0:
                spf[idx] = np.uint32(p)
    return spf

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample-odds", type=int, default=100)
    ap.add_argument("--random-pairs", type=int, default=3000)
    args = ap.parse_args()
    if not 1 <= args.sample_odds <= 1000 or not 1 <= args.random_pairs <= 100000:
        ap.error("sample-odds in 1..1000; random-pairs in 1..100000")

    # Audit only the pair-square primitive with independent arbitrary-precision Python.
    rng = random.Random(22050)
    edges = [0, 1, 2, 3, 2_147_483_647, 2_147_483_648,
             20_000_000_000, 45_000_000_000, BOUND-1, BOUND]
    pairs = [(a, b) for a in edges for b in edges]
    pairs += [(3*k, 4*k) for k in [1, 10, 1_000, 100_000, 1_000_000_000, 10_000_000_000]]
    pairs += [(rng.randrange(BOUND + 1), rng.randrange(BOUND + 1))
              for _ in range(args.random_pairs)]
    for a, b in pairs:
        n = a*a + b*b
        expected = math.isqrt(n)**2 == n
        got = bool(arith.is_square_sum(np.int64(a), np.int64(b)))
        if expected != got:
            raise AssertionError(f"Square mismatch: {a}, {b}; expected={expected}, got={got}")
    print(f"PASS square-sum vs Python big integers: {len(pairs):,} cases")

    # Algebraic bounds; this is NOT a full code-path overflow proof.
    max_pair_sum = 2*BOUND*BOUND
    max_space_sum = 3*BOUND*BOUND
    assert max_pair_sum > (1 << 63)-1
    assert max_space_sum > (1 << 63)-1
    assert BOUND < (1 << 63)-1
    assert 3*BOUND < (1 << 63)-1
    assert math.isqrt(BOUND) < (1 << 32)
    print("PASS arithmetic bounds: int64 edge/cap and uint32 SPF fit; pair/space sums require wide integers")

    primes_list = factor.primes_upto(math.isqrt(BOUND))
    primes_np = np.asarray(primes_list, dtype=np.int64)
    spf_numba_core(np.int64(3), np.int64(101), primes_np)
    warm = np.asarray(factor.odd_spf_segment(3, 101, primes_list), dtype=np.uint32)
    engine.fused_segment_kernel(3, 101, 100, warm, primes_np)
    cases = [
        ("20B+1", 20_000_000_001),
        ("45B+1", 45_000_000_001),
        ("prime-square", 49_992_040_921 - 99),
        ("50B-tail", BOUND - (2*args.sample_odds - 1)),
    ]
    for label, lo in cases:
        if lo % 2 == 0:
            lo += 1
        hi = lo + 2*(args.sample_odds-1)
        if hi >= BOUND:
            raise AssertionError(f"Invalid interval {label}")
        old = np.asarray(factor.odd_spf_segment(lo, hi, primes_list), dtype=np.uint32)
        new = spf_numba_core(np.int64(lo), np.int64(hi), primes_np)
        if not np.array_equal(old, new):
            raise AssertionError(f"SPF mismatch {label}")
        a = engine.fused_segment_kernel(lo, hi, BOUND, old, primes_np)
        b = engine.fused_segment_kernel(lo, hi, BOUND, new, primes_np)
        # Compare exact triples and counters.
        if sorted(tuple(map(int, t)) for t in a[0]) != sorted(tuple(map(int, t)) for t in b[0]) or tuple(map(int,a[1:])) != tuple(map(int,b[1:])):
            raise AssertionError(f"Kernel mismatch {label}")
        for odd, e1, e2 in a[0]:
            sides = [int(odd), int(e1), int(e2)]
            assert max(sides) <= BOUND
            assert math.gcd(math.gcd(*sides[:2]), sides[2]) == 1
            for i, j in ((0,1),(0,2),(1,2)):
                n = sides[i]**2+sides[j]**2
                assert math.isqrt(n)**2 == n
        print(f"PASS {label}: [{lo:,}..{hi:,}] odds={args.sample_odds} "
              f"bricks={len(a[0])} tested={int(a[1])} rejected={int(a[2])}")
    print("PASS targeted arithmetic and sampled kernel checks.")
    print("NOT a proof of full 50B overflow safety, completeness, or checkpoint/resume integrity.")

if __name__ == "__main__":
    main()
