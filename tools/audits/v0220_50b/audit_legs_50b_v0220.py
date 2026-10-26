"""Independent exact-integer audit of high-bound even-leg generation. Read-only."""
import argparse
import math
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
import segmented_factorization as factor
import odd_leg_numba_1000b_experimental as engine

BOUND = 50_000_000_000

def exact_legs(odd, bound, primes):
    n = odd
    fs = []
    for p in primes:
        if p * p > n:
            break
        if n % p == 0:
            e = 0
            while n % p == 0:
                n //= p
                e += 1
            fs.append((p, e))
    if n > 1:
        fs.append((n, 1))
    divisors = [1]
    for p, e in fs:
        powers = [p**k for k in range(2*e+1)]
        divisors = [d*power for d in divisors for power in powers if d*power < odd]
    legs = []
    for d in divisors:
        quotient, remainder = divmod(odd*odd, d)
        assert remainder == 0
        if quotient > d and (quotient-d) % 2 == 0:
            leg = (quotient-d)//2
            if 0 < leg <= bound:
                legs.append(leg)
    return sorted(legs)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--odds-per-region', type=int, default=20)
    args = ap.parse_args()
    if not 1 <= args.odds_per_region <= 200:
        ap.error('odds-per-region must be 1..200')
    primes = factor.primes_upto(math.isqrt(BOUND))
    prime_np = np.asarray(primes, dtype=np.int64)
    regions = [20_000_000_001, 45_000_000_001, 49_992_040_901,
               BOUND - (2*args.odds_per_region-1)]
    total = nonempty = 0
    for lo in regions:
        if lo % 2 == 0:
            lo += 1
        hi = lo + 2*(args.odds_per_region-1)
        assert 3 <= lo <= hi < BOUND
        spf = np.asarray(factor.odd_spf_segment(lo, hi, primes), dtype=np.uint32)
        for odd in range(lo, hi+1, 2):
            got = sorted(int(x) for x in engine.compatible_even_legs_jit(
                np.int64(odd), np.int64(BOUND), spf, np.int64(lo), prime_np))
            expected = exact_legs(odd, BOUND, primes)
            if got != expected:
                raise AssertionError(f'MISMATCH odd={odd} expected={expected[:12]} got={got[:12]} '
                                     f'lengths={len(expected)}/{len(got)}')
            total += 1
            nonempty += bool(got)
        print(f'PASS [{lo:,}..{hi:,}] odds={args.odds_per_region}', flush=True)
    print(f'PASS independent Python-bigint leg comparison: odds={total}, nonempty={nonempty}')
    print('NOT full 50B overflow/completeness or checkpoint approval.')

if __name__ == '__main__':
    main()
