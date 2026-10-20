#!/usr/bin/env python3
"""v0.13.0: exact-integer space-diagonal gap analysis of Euler bricks.

Read-only with respect to the source catalog. No claim of completeness or
statistical independence is made.
"""
import argparse
import csv
import math
from collections import Counter
from pathlib import Path
from statistics import median


def load_bricks(path):
    with open(path, newline='', encoding='utf-8-sig') as handle:
        reader = csv.reader(handle)
        first = next(reader, None)
        if first is None:
            raise ValueError('Empty CSV')
        names = [x.strip().lower() for x in first]
        if {'a', 'b', 'c'} <= set(names):
            indices = [names.index(x) for x in ('a', 'b', 'c')]
            lines = enumerate(reader, 2)
        else:
            indices = [0, 1, 2]
            lines = enumerate([first, *reader], 1)
        seen = set()
        for line_no, row in lines:
            if not row or all(not cell.strip() for cell in row):
                continue
            try:
                a, b, c = (int(row[i].strip()) for i in indices)
            except (IndexError, ValueError) as exc:
                raise ValueError(f'Invalid edges on CSV line {line_no}: {row!r}') from exc
            if not (0 < a < b < c):
                raise ValueError(f'Edges must satisfy 0 < a < b < c on line {line_no}')
            if (a, b, c) in seen:
                raise ValueError(f'Duplicate triple on line {line_no}: {(a, b, c)}')
            seen.add((a, b, c))
            yield a, b, c


def exact_face_check(a, b, c):
    if math.gcd(math.gcd(a, b), c) != 1:
        return False
    for q in (a*a + b*b, a*a + c*c, b*b + c*c):
        r = math.isqrt(q)
        if r*r != q:
            return False
    return True


def analyze(input_path, output_path, max_edge):
    rows = []
    for a, b, c in load_bricks(input_path):
        if max_edge is not None and c > max_edge:
            raise ValueError(f'Edge {c} exceeds --max-edge {max_edge}')
        if not exact_face_check(a, b, c):
            raise ValueError(f'Not a primitive Euler brick: {(a, b, c)}')
        s = a*a + b*b + c*c
        k = math.isqrt(s)
        lower = s - k*k
        upper = (k+1)*(k+1) - s
        delta = min(lower, upper)
        nearest = k if lower <= upper else k+1
        # The adjacent-square spacing 2*k+1 is exact; ratio is in [0, 1/2].
        norm = delta / (2*k + 1)
        rows.append((a, b, c, s, k, nearest, delta, norm))
    if not rows:
        raise ValueError('No rows found')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(('a','b','c','space_diagonal_squared','floor_diagonal',
                         'nearest_integer_diagonal','nearest_square_gap',
                         'gap_over_adjacent_square_spacing'))
        for a,b,c,s,k,nearest,delta,norm in rows:
            writer.writerow((a,b,c,s,k,nearest,delta,f'{norm:.12g}'))

    gaps = [r[6] for r in rows]
    norms = [r[7] for r in rows]
    print(f'INPUT: {input_path}; rows={len(rows):,}; max_observed_edge={max(r[2] for r in rows):,}')
    print(f'OUTPUT: {output_path}; rows={len(rows):,}')
    print(f'PERFECT CUBOIDS: {sum(g == 0 for g in gaps)}')
    print(f'NEAREST-SQUARE GAP: min={min(gaps):,}; median={median(gaps):,.1f}; max={max(gaps):,}')
    print(f'NORMALIZED GAP: min={min(norms):.8f}; median={median(norms):.8f}; max={max(norms):.8f}')
    print('NORMALIZED GAP BINS (gap / (2*floor(sqrt(S))+1)):')
    for i in range(10):
        lo, hi = i/20, (i+1)/20
        count = sum((lo <= x < hi) if i < 9 else (lo <= x <= hi) for x in norms)
        print(f'  [{lo:.2f}, {hi:.2f}{")" if i < 9 else "]"}: {count:,}')
    print('TEN SMALLEST NORMALIZED GAPS:')
    for a,b,c,s,k,nearest,delta,norm in sorted(rows, key=lambda r: (r[7],r[6],r[2]))[:10]:
        print(f'  ({a}, {b}, {c}) delta={delta:,} normalized={norm:.10f} nearest_d={nearest:,}')
    print('LIMITATIONS: Finite catalog; no inference of a perfect cuboid or asymptotic distribution.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, default=Path('data/verified_euler_bricks.csv'))
    p.add_argument('--output', type=Path, default=Path('space_diagonal_analysis_0130.csv'))
    p.add_argument('--max-edge', type=int, default=1_000_000_000)
    args = p.parse_args()
    try:
        analyze(args.input, args.output, args.max_edge)
    except (OSError, ValueError) as exc:
        p.exit(1, f'ERROR: {exc}\n')


if __name__ == '__main__':
    main()
