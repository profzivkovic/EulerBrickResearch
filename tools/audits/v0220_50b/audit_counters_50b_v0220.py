"""Read-only independent Python-bigint check of per-odd pair counters and matches."""
import argparse
import math
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools' / 'benchmarks'))
import segmented_factorization as factor
import odd_leg_numba_1000b_experimental as engine
from audit_legs_50b_v0220 import exact_legs

BOUND = 50_000_000_000

def reference(odd, legs):
    div = [e for e in legs if e % 3 == 0]
    nondiv = [e for e in legs if e % 3 != 0] if odd % 3 == 0 else []
    tested = rejected = 0
    matches = []
    pairs = ((a, b) for a in div for b in nondiv) if odd % 3 == 0 else (
        (div[i], div[j]) for i in range(len(div)) for j in range(i + 1, len(div)))
    for a, b in pairs:
        if math.gcd(math.gcd(odd, a), b) != 1:
            rejected += 1
        else:
            tested += 1
            if math.isqrt(a*a + b*b)**2 == a*a + b*b:
                matches.append(tuple(sorted((a, b))))
    return sorted(matches), tested, rejected

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--odds-per-region', type=int, default=20)
    args = ap.parse_args()
    if not 1 <= args.odds_per_region <= 100:
        ap.error('odds-per-region must be 1..100')
    primes = factor.primes_upto(math.isqrt(BOUND))
    primes_np = np.asarray(primes, dtype=np.int64)
    regions = [('small', 3, 150), ('20B', 20_000_000_001, args.odds_per_region),
               ('45B', 45_000_000_001, args.odds_per_region),
               ('square', 49_992_040_901, args.odds_per_region),
               ('50B-tail', BOUND - (2*args.odds_per_region-1), args.odds_per_region)]
    total = tested_total = rejected_total = matches_total = 0
    for label, lo, count in regions:
        hi = lo + 2*(count-1)
        assert lo % 2 and 3 <= lo <= hi < BOUND
        spf = np.asarray(factor.odd_spf_segment(lo, hi, primes), dtype=np.uint32)
        for odd in range(lo, hi+1, 2):
            legs = exact_legs(odd, BOUND, primes)
            expected = reference(odd, legs)
            pairs, tested, rejected = engine.fused_odd_kernel(
                np.int64(odd), np.int64(BOUND), spf, np.int64(lo), primes_np)
            actual = (sorted(tuple(sorted((int(a), int(b)))) for a, b in pairs), int(tested), int(rejected))
            if actual != expected:
                raise AssertionError(f'FAIL odd={odd}: expected={expected} actual={actual}')
            total += 1
            matches_total += len(expected[0]); tested_total += expected[1]; rejected_total += expected[2]
        print(f'PASS {label}: odds={count}', flush=True)
    assert 0 <= tested_total < 2**63 and 0 <= rejected_total < 2**63
    print(f'PASS independent counters/matches: odds={total} matches={matches_total} tested={tested_total} rejected={rejected_total}')
    print('NOT a proof of whole-run counter bounds, 50B completeness, or checkpoint safety.')

if __name__ == '__main__':
    main()
