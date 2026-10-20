#!/usr/bin/env python3
"""v0.12.1: sensitivity and interval-increment checks for Euler-brick growth fits.

Descriptive finite-range tests only; reads but never modifies the verified catalog.
Requires NumPy and the v0.12.0 compare_growth_models.py in the same directory.
"""
import argparse
import csv
import math
from bisect import bisect_right
from pathlib import Path

import numpy as np
from compare_growth_models import ANCHORS, load_edges

MODELS = ('power', 'power_log_beta1', 'power_log_free')
CUTOFFS = (1_000_000, 2_000_000, 5_000_000, 10_000_000)
TESTS = ((50_000_000, 100_000_000), (100_000_000, 200_000_000),
         (200_000_000, 500_000_000), (200_000_000, 1_000_000_000),
         (500_000_000, 1_000_000_000))


def fit_model(bounds, counts, model):
    """OLS of log N, with centered/scaled predictors; fixed beta=1 when requested."""
    x = np.log(np.asarray(bounds, dtype=float))
    y = np.log(np.asarray(counts, dtype=float))
    fixed_beta = 1.0 if model == 'power_log_beta1' else 0.0
    if model == 'power_log_beta1':
        y = y - np.log(x)
    predictors = [x]
    if model == 'power_log_free':
        predictors.append(np.log(x))
    z = np.column_stack(predictors)
    means, scales = z.mean(axis=0), z.std(axis=0)
    if np.any(scales <= 0):
        raise ValueError('Degenerate predictors')
    design = np.column_stack((np.ones(len(x)), (z-means)/scales))
    coefficients, _, rank, singular = np.linalg.lstsq(design, y, rcond=None)
    if rank != design.shape[1]:
        raise ValueError('Rank deficient fit')
    slopes = coefficients[1:] / scales
    log_c = float(coefficients[0] - np.dot(slopes, means))
    alpha = float(slopes[0])
    beta = float(slopes[1]) if model == 'power_log_free' else fixed_beta
    return log_c, alpha, beta, float(singular[0]/singular[-1])


def predict(params, bound):
    log_c, alpha, beta, _ = params
    return math.exp(log_c + alpha*math.log(bound) + beta*math.log(math.log(bound)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('data/verified_euler_bricks.csv'))
    parser.add_argument('--catalog-bound', type=int, default=1_000_000_000)
    parser.add_argument('--output', type=Path, default=Path('growth_robustness_0121.csv'))
    args = parser.parse_args()
    edges = load_edges(args.input)
    if not edges or edges[-1] > args.catalog_bound:
        parser.error('Empty catalog or observed edge exceeds --catalog-bound')
    counts = {b: bisect_right(edges, b) for b in ANCHORS if b <= args.catalog_bound}
    print(f'INPUT: {args.input}; rows={len(edges)}; catalog_bound={args.catalog_bound:,}')
    print('All predictions are historical holdouts; no catalog data are changed.')
    rows = []
    for cutoff in CUTOFFS:
        for train_max, target in TESTS:
            if target not in counts:
                continue
            training = [(b, n) for b, n in counts.items() if cutoff <= b <= train_max and n > 0]
            if len(training) < 4:  # avoid a near-interpolating 3-parameter fit
                continue
            bounds, observations = zip(*training)
            actual = counts[target]
            base = counts[train_max]
            observed_increment = actual-base
            for model in MODELS:
                params = fit_model(bounds, observations, model)
                predicted = predict(params, target)
                predicted_base = predict(params, train_max)
                predicted_increment = predicted-predicted_base
                count_error = 100*(predicted-actual)/actual
                increment_error = 100*(predicted_increment-observed_increment)/observed_increment
                rows.append(dict(cutoff=cutoff, train_max=train_max, target=target,
                                 model=model, train_points=len(training), observed=actual,
                                 predicted=f'{predicted:.6f}', count_error_pct=f'{count_error:+.6f}',
                                 observed_increment=observed_increment,
                                 predicted_increment=f'{predicted_increment:.6f}',
                                 increment_error_pct=f'{increment_error:+.6f}',
                                 alpha=f'{params[1]:.8f}', beta=f'{params[2]:.8f}',
                                 condition=f'{params[3]:.5g}'))
                print(f'min={cutoff//1_000_000:>2}M train={train_max//1_000_000:>3}M '
                      f'target={target//1_000_000:>4}M {model:15} '
                      f'Nerr={count_error:+7.2f}% dNerr={increment_error:+8.2f}% '
                      f'alpha={params[1]:+.4f} beta={params[2]:+.4f}')
    if not rows:
        parser.error('No usable rolling-origin fits')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print('\nSUMMARY: mean absolute error, separately for each cutoff (tests overlap)')
    for cutoff in CUTOFFS:
        for model in MODELS:
            subset = [r for r in rows if r['cutoff'] == cutoff and r['model'] == model]
            if subset:
                mae_n = sum(abs(float(r['count_error_pct'])) for r in subset)/len(subset)
                mae_dn = sum(abs(float(r['increment_error_pct'])) for r in subset)/len(subset)
                print(f'min={cutoff//1_000_000:>2}M {model:15} '
                      f'tests={len(subset)} MAE_N={mae_n:.2f}% MAE_dN={mae_dn:.2f}%')
    print(f'OUTPUT: {args.output}; rows={len(rows)}')
    print('LIMITATIONS: Cumulative counts and rolling tests overlap; intervals are not independent replicates.')
    print('LIMITATIONS: Increment forecasts are differences of fitted cumulative curves, not separately fitted interval models.')
    print('LIMITATIONS: No claim of asymptotic law, statistical significance, or completeness.')


if __name__ == '__main__':
    main()
