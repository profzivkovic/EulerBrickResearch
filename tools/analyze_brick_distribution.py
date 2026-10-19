#!/usr/bin/env python3
"""v0.11.0: read-only descriptive distribution analysis of primitive Euler bricks.

Uses catalog triples, not an independent arithmetic or completeness validator.
Standard library only. No changes to canonical catalog or manifest.
"""
import argparse
import csv
import math
from bisect import bisect_right
from pathlib import Path

DEFAULT_BOUNDS = (10_000_000, 20_000_000, 50_000_000,
                  100_000_000, 200_000_000, 500_000_000)


def parse_bounds(raw):
    bounds = [int(x.strip()) for x in raw.split(',')]
    if not bounds or any(x <= 0 for x in bounds) or bounds != sorted(set(bounds)):
        raise ValueError('Bounds must be strictly increasing positive integers')
    return bounds


def read_largest_edges(path):
    largest = []
    seen = set()
    with path.open('r', encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {'a', 'b', 'c'} <= set(reader.fieldnames):
            raise ValueError('CSV must contain a,b,c columns')
        for line, row in enumerate(reader, start=2):
            try:
                triple = tuple(int(row[k]) for k in ('a', 'b', 'c'))
            except (TypeError, ValueError) as exc:
                raise ValueError(f'Invalid edge at line {line}') from exc
            a, b, c = triple
            if not 0 < a < b < c or triple in seen:
                raise ValueError(f'Invalid or duplicate triple at line {line}: {triple}')
            seen.add(triple)
            largest.append(c)
    return sorted(largest)


def make_rows(largest, bounds):
    result = []
    lo = previous = 0
    for hi in bounds:
        total = bisect_right(largest, hi)
        new = total - previous
        density = 1_000_000 * new / (hi - lo)
        alpha = (math.log(total / previous) / math.log(hi / lo)
                 if lo > 0 and previous > 0 and total > 0 else None)
        result.append((lo, hi, new, total, density, alpha))
        lo, previous = hi, total
    return result


def log_bounds(start, stop, steps):
    """Generate approximately log-uniform integer boundaries, inclusive of endpoints."""
    if not 0 < start < stop or steps < 2:
        raise ValueError('Log bins require 0 < start < final bound and steps >= 2')
    result = [start]
    for i in range(1, steps):
        edge = round(math.exp(math.log(start) + i * math.log(stop / start) / steps))
        if edge <= result[-1]:
            raise ValueError('Log-bin boundaries are not distinct; reduce bin count')
        result.append(edge)
    result.append(stop)
    return result


def fit_power_law(points):
    """OLS on log cumulative counts: log N = intercept + alpha log B."""
    if len(points) < 2:
        raise ValueError('At least two positive cumulative observations are needed')
    xs = [math.log(b) for b, _ in points]
    ys = [math.log(n) for _, n in points]
    xm = sum(xs) / len(xs)
    ym = sum(ys) / len(ys)
    denom = sum((x - xm)**2 for x in xs)
    if denom == 0:
        raise ValueError('Distinct fitting bounds required')
    alpha = sum((x - xm)*(y - ym) for x, y in zip(xs, ys)) / denom
    intercept = ym - alpha * xm
    return intercept, alpha


def print_table(rows):
    print('Interval                     New      Total    New / 1M   Local alpha')
    for lo, hi, new, total, density, alpha in rows:
        a = f'{alpha:.4f}' if alpha is not None else 'n/a'
        print(f'{lo:>11,}–{hi:<11,} {new:>7,} {total:>10,} {density:>11.3f} {a:>13}')


def write_rows(path, rows):
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(('lower_exclusive', 'upper_inclusive', 'new_bricks',
                         'cumulative_bricks', 'new_per_million', 'local_alpha'))
        for lo, hi, new, total, density, alpha in rows:
            writer.writerow((lo, hi, new, total, f'{density:.6f}',
                             '' if alpha is None else f'{alpha:.8f}'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('data/verified_euler_bricks.csv'))
    parser.add_argument('--bounds', default=','.join(map(str, DEFAULT_BOUNDS)))
    parser.add_argument('--output', type=Path, help='Optional CSV for fixed-bound table')
    parser.add_argument('--log-start', type=int, default=1_000_000,
                        help='First log-bin boundary (default 1M)')
    parser.add_argument('--log-bins', type=int, default=12,
                        help='Number of logarithmically spaced intervals')
    parser.add_argument('--log-output', type=Path, help='Optional CSV for log-bin table')
    parser.add_argument('--train-max', type=int, default=200_000_000,
                        help='Maximum fitting bound (default 200M)')
    parser.add_argument('--predict-at', type=int, default=500_000_000,
                        help='Held-out comparison bound (default 500M)')
    args = parser.parse_args()

    bounds = parse_bounds(args.bounds)
    largest = read_largest_edges(args.input)
    if largest and largest[-1] > bounds[-1]:
        parser.error('Catalog contains edges above the last --bounds value')
    if not 0 < args.train_max < args.predict_at <= bounds[-1]:
        parser.error('Require 0 < --train-max < --predict-at <= last --bounds')

    print(f'INPUT: {args.input}; rows={len(largest)}; unique={len(largest)}')
    print('\nFIXED BOUNDS')
    fixed = make_rows(largest, bounds)
    print_table(fixed)
    if args.output:
        write_rows(args.output, fixed)
        print(f'FIXED CSV: {args.output}')

    print('\nLOGARITHMIC INTERVALS')
    edges = log_bounds(args.log_start, bounds[-1], args.log_bins)
    log_rows = make_rows(largest, edges)[1:]  # exclude (0, log_start]
    print(f'Initial (0, {args.log_start:,}]: {bisect_right(largest, args.log_start)} bricks')
    print_table(log_rows)
    if args.log_output:
        write_rows(args.log_output, log_rows)
        print(f'LOG CSV: {args.log_output}')

    print('\nOUT-OF-SAMPLE POWER-LAW CHECK')
    train = [(b, bisect_right(largest, b)) for b in bounds
             if b <= args.train_max and bisect_right(largest, b) > 0]
    if len(train) < 2:
        parser.error('Need at least two positive fixed-bound counts <= --train-max')
    intercept, alpha = fit_power_law(train)
    prediction = math.exp(intercept + alpha * math.log(args.predict_at))
    actual = bisect_right(largest, args.predict_at)
    error_pct = 100 * (prediction - actual) / actual if actual else None
    print(f'Training bounds: {[b for b, _ in train]}')
    print(f'Fit: N(B) = C * B^alpha; alpha={alpha:.6f}; C={math.exp(intercept):.8g}')
    print(f'Prediction at B={args.predict_at:,}: {prediction:.1f}')
    print(f'Observed at B={args.predict_at:,}: {actual}')
    print(f'Prediction error (predicted - observed)/observed: {error_pct:+.2f}%'
          if error_pct is not None else 'Prediction error: n/a')
    print('NOTE: Fits are descriptive; cumulative counts are dependent observations.')
    print('NOTE: Held-out check is one historical extrapolation, not a proof or uncertainty interval.')
    print('NOTE: This tool does not independently verify Euler conditions or completeness.')


if __name__ == '__main__':
    main()
