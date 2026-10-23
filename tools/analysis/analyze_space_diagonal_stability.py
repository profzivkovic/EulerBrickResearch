#!/usr/bin/env python3
"""v0.13.1: finite-range stability of Euler-brick space-diagonal gaps.

Reads v0.13.0 output CSV (with a,b,c) or the canonical brick catalog.
No changes are made to inputs. Uses integer arithmetic for square gaps.
"""
import argparse
import csv
import math
from pathlib import Path

BINS = [0, 10_000_000, 50_000_000, 100_000_000, 200_000_000, 500_000_000, 1_000_000_000]


def load(path, max_edge):
    rows = []
    seen = set()
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not {'a', 'b', 'c'}.issubset(reader.fieldnames):
            raise ValueError('CSV must contain a,b,c columns')
        for lineno, r in enumerate(reader, 2):
            try:
                a, b, c = (int(r[k]) for k in ('a', 'b', 'c'))
            except (ValueError, KeyError, TypeError) as e:
                raise ValueError(f'Invalid edges on line {lineno}: {e}') from e
            if not (0 < a < b < c <= max_edge):
                raise ValueError(f'Invalid order or bound on line {lineno}')
            if (a,b,c) in seen:
                raise ValueError(f'Duplicate triple on line {lineno}')
            seen.add((a,b,c))
            s = a*a + b*b + c*c
            k = math.isqrt(s)
            delta = min(s-k*k, (k+1)*(k+1)-s)
            if delta == 0:
                raise ValueError(f'Perfect cuboid encountered on line {lineno}; review separately')
            rows.append((c, delta/(2*k+1)))
    return rows


def median(v):
    v = sorted(v)
    n = len(v)
    return (v[(n-1)//2]+v[n//2])/2 if n else float('nan')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True, type=Path)
    p.add_argument('--max-edge', type=int, default=1_000_000_000)
    p.add_argument('--output', type=Path, default=Path('space_diagonal_stability_0131.csv'))
    args = p.parse_args()
    if args.max_edge != BINS[-1]:
        p.error('This version uses fixed intervals through 1B; --max-edge must be 1000000000')
    rows = load(args.input, args.max_edge)
    results = []
    print(f'INPUT: {args.input}; rows={len(rows):,}')
    print('INTERVALS: lower < c <= upper (first interval includes all c > 0)')
    print('Expected uniform fraction for normalized gap < 0.05: 10% (descriptive benchmark)')
    for lo, hi in zip(BINS, BINS[1:]):
        vals = [g for c,g in rows if lo < c <= hi]
        n = len(vals)
        if not n:
            print(f'({lo:,}, {hi:,}]: n=0')
            continue
        small = sum(g < .05 for g in vals)
        counts = [sum((j*.05 <= g < (j+1)*.05) if j < 9 else (.45 <= g <= .5) for g in vals) for j in range(10)]
        # Pearson statistic is descriptive only; samples need not be independent.
        chi2 = sum((x-n/10)**2/(n/10) for x in counts)
        rec = dict(lower_exclusive=lo, upper_inclusive=hi, count=n,
                   median_gap=f'{median(vals):.10f}', mean_gap=f'{sum(vals)/n:.10f}',
                   count_gap_lt_005=small, fraction_gap_lt_005=f'{small/n:.8f}',
                   descriptive_chi_square=f'{chi2:.5f}',
                   **{f'bin_{j}':x for j,x in enumerate(counts)})
        results.append(rec)
        print(f'({lo:>11,}, {hi:>13,}]: n={n:4d} median={median(vals):.8f} '
              f'mean={sum(vals)/n:.8f} gap<0.05={small:4d} ({100*small/n:5.2f}%) '
              f'chi2_descriptive={chi2:.3f}')
        print('  bins:', ', '.join(map(str, counts)))
    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]) if results else ['lower_exclusive','upper_inclusive','count'])
        writer.writeheader()
        writer.writerows(results)
    print(f'OUTPUT: {args.output}; intervals={len(results)}')
    print('LIMITATIONS: Descriptive finite-catalog comparison; no independent sampling or significance claim.')
    print('LIMITATIONS: Gap is the v0.13.0 nearest-square gap divided by 2*floor(sqrt(S))+1.')

if __name__ == '__main__':
    main()
