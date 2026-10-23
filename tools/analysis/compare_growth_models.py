#!/usr/bin/env python3
"""v0.12.0: rolling-origin comparison of empirical Euler-brick growth models.

Reads a validated canonical CSV (a,b,c); never modifies it.
Requires NumPy. All fits are descriptive, not completeness proofs.
"""
import argparse
import csv
import math
from bisect import bisect_right
from pathlib import Path

import numpy as np

ANCHORS = (1_000_000, 2_000_000, 5_000_000, 10_000_000,
           20_000_000, 50_000_000, 100_000_000,
           200_000_000, 500_000_000, 1_000_000_000)
TESTS = ((50_000_000, 100_000_000),
         (100_000_000, 200_000_000),
         (200_000_000, 500_000_000),
         (200_000_000, 1_000_000_000),
         (500_000_000, 1_000_000_000))


def load_edges(path):
    edges = []
    seen = set()
    with path.open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        if not {'a', 'b', 'c'} <= set(reader.fieldnames or ()):
            raise ValueError('Input CSV requires columns a,b,c')
        for line, row in enumerate(reader, 2):
            try:
                a, b, c = (int(row[k]) for k in ('a', 'b', 'c'))
            except (TypeError, ValueError) as exc:
                raise ValueError(f'Invalid integer at CSV line {line}') from exc
            if not 0 < a < b < c:
                raise ValueError(f'Edges must satisfy 0<a<b<c at line {line}')
            triple = (a, b, c)
            if triple in seen:
                raise ValueError(f'Duplicate triple at line {line}: {triple}')
            seen.add(triple)
            edges.append(c)
    edges.sort()
    return edges


def fit(bounds, counts, corrected):
    """Least squares in log-count space, with SVD and column scaling."""
    x = np.log(np.asarray(bounds, dtype=np.float64))
    y = np.log(np.asarray(counts, dtype=np.float64))
    columns = [np.ones_like(x), x]
    if corrected:
        columns.append(np.log(x))
    matrix = np.column_stack(columns)
    # Center/scale non-intercept columns to reduce severe collinearity.
    means = matrix[:, 1:].mean(axis=0)
    scales = matrix[:, 1:].std(axis=0)
    if np.any(scales <= 0):
        raise ValueError('Degenerate training bounds')
    standardized = np.column_stack([np.ones_like(x), (matrix[:, 1:] - means) / scales])
    coeff, _, rank, singular = np.linalg.lstsq(standardized, y, rcond=None)
    if rank != standardized.shape[1]:
        raise ValueError('Rank-deficient model fit')
    slopes = coeff[1:] / scales
    intercept = coeff[0] - np.dot(slopes, means)
    alpha = float(slopes[0])
    beta = float(slopes[1]) if corrected else 0.0
    return float(intercept), alpha, beta, float(singular[0] / singular[-1])


def predict(parameters, bound):
    log_c, alpha, beta, _ = parameters
    return math.exp(log_c + alpha * math.log(bound) + beta * math.log(math.log(bound)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('data/verified_euler_bricks.csv'))
    parser.add_argument('--output', type=Path, default=Path('growth_model_comparison.csv'))
    parser.add_argument('--catalog-bound', type=int, default=1_000_000_000,
                        help='Verified search bound; do not infer it from the largest observed edge')
    args = parser.parse_args()
    edges = load_edges(args.input)
    if not edges:
        parser.error('Empty catalog')
    max_edge = edges[-1]
    if max_edge > args.catalog_bound:
        parser.error('Catalog contains an edge above --catalog-bound')
    counts = {b: bisect_right(edges, b) for b in ANCHORS if b <= args.catalog_bound}
    print(f'INPUT: {args.input}; rows={len(edges)}; max_observed_edge={max_edge:,}')
    print('Counts:', ', '.join(f'{b:,}:{n:,}' for b, n in counts.items()))
    rows = []
    for train_max, target in TESTS:
        if target not in counts:
            continue
        training = [(b, n) for b, n in counts.items() if b <= train_max and n > 0]
        if len(training) < 4:
            continue
        bounds, observations = zip(*training)
        actual = counts[target]
        for model, corrected in [('power', False), ('power_log', True)]:
            params = fit(bounds, observations, corrected)
            forecast = predict(params, target)
            error = (forecast - actual) / actual * 100
            record = dict(train_max=train_max, target=target, model=model,
                          train_points=len(training), observed=actual,
                          predicted=f'{forecast:.6f}', error_pct=f'{error:+.6f}',
                          alpha=f'{params[1]:.8f}', beta=f'{params[2]:.8f}',
                          C=f'{math.exp(params[0]):.12g}',
                          scaled_design_condition=f'{params[3]:.5g}')
            rows.append(record)
            print(f'train<= {train_max:>10,} -> {target:>13,} | {model:9s} '
                  f'pred={forecast:9.1f} actual={actual:5d} '
                  f'error={error:+7.2f}% alpha={params[1]:+.4f} beta={params[2]:+.4f}')
    if not rows:
        parser.error('No available historical test points for this catalog')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f'OUTPUT: {args.output}; forecasts={len(rows)}')
    print('CAUTION: Cumulative counts are dependent; models are descriptive.')
    print('CAUTION: Log-corrected model may be unstable/extrapolate poorly; compare held-out errors.')
    print('CAUTION: This script checks CSV structure/uniqueness, not Euler arithmetic or completeness.')


if __name__ == '__main__':
    main()
