#!/usr/bin/env python3
"""EulerBrickResearch v0.8.2: discrete ACO vs random, 30+ independent runs."""
import argparse
import csv
import random
import statistics
from math import gcd, isqrt, lcm
from pathlib import Path
from time import perf_counter

FIELDS = ['run', 'seed', 'method', 'a', 'b', 'c', 'x', 'y', 'z',
          'space_squared', 'space_floor', 'square_gap', 'normalized_gap', 'perfect']
METRICS = ['run', 'seed', 'method', 'evaluations', 'unique_candidates',
           'primitive_bricks', 'best_fitness', 'elapsed_seconds']


def triple(m, n):
    return m*m-n*n, 2*m*n


def construct(p, q, choice, max_edge):
    u, v = triple(*p)
    w, z = triple(*q)
    common1, other1 = (u, v) if choice // 2 == 0 else (v, u)
    common2, other2 = (w, z) if choice % 2 == 0 else (z, w)
    common = lcm(common1, common2)
    b = other1 * (common // common1)
    c = other2 * (common // common2)
    d = gcd(gcd(common, b), c)
    a, b, c = sorted((common // d, b // d, c // d))
    if a == b or b == c or c > max_edge:
        return None
    return a, b, c


def inspect(edges):
    a, b, c = edges
    aa, bb, cc = a*a, b*b, c*c
    face_squares = (aa+bb, aa+cc, bb+cc)
    roots = tuple(isqrt(v) for v in face_squares)
    exact = tuple(r*r == v for r, v in zip(roots, face_squares))
    if sum(exact) < 2:
        raise AssertionError('Construction did not preserve two square faces')
    face_score = sum(
        min(v-r*r, (r+1)*(r+1)-v) / (2*r+1)
        for v, r, ok in zip(face_squares, roots, exact) if not ok
    )
    space = aa+bb+cc
    floor = isqrt(space)
    near = floor if space-floor*floor <= (floor+1)*(floor+1)-space else floor+1
    gap = abs(space-near*near)
    normalized_gap = gap / (floor+near)
    score = face_score + (normalized_gap if all(exact) else 0.0)
    row = (a, b, c, *roots, space, floor, gap,
           f'{normalized_gap:.12f}', int(floor*floor == space and all(exact)))
    return row, all(exact), score


def legalize(coords, max_m):
    m1 = max(2, min(max_m, round(coords[0])))
    n1 = max(1, min(m1-1, round(coords[1])))
    m2 = max(2, min(max_m, round(coords[2])))
    n2 = max(1, min(m2-1, round(coords[3])))
    return (m1, n1), (m2, n2)


class Tracker:
    def __init__(self, method, max_edge):
        self.method = method
        self.max_edge = max_edge
        self.evaluations = 0
        self.unique = set()
        self.bricks = {}
        self.best = None
        self.best_score = float('inf')

    def evaluate(self, coords, max_m):
        p, q = legalize(coords, max_m)
        local_score = float('inf')
        for choice in range(4):
            self.evaluations += 1
            edges = construct(p, q, choice, self.max_edge)
            if edges is None:
                continue
            self.unique.add(edges)
            row, brick, score = inspect(edges)
            if brick:
                self.bricks[edges] = row
            if score < local_score:
                local_score = score
            if score < self.best_score:
                self.best_score = score
                self.best = row
        return local_score


def random_coords(rng, max_m):
    m1 = rng.randint(2, max_m)
    m2 = rng.randint(2, max_m)
    return [float(m1), float(rng.randint(1, m1-1)),
            float(m2), float(rng.randint(1, m2-1))]


def weighted_choice(rng, weights):
    total = sum(weights)
    target = rng.random() * total
    for index, weight in enumerate(weights):
        target -= weight
        if target < 0:
            return index
    return len(weights) - 1


def aco(seed, ants, iterations, max_m, max_edge,
        evaporation=0.20, elite_fraction=0.20, exploration=0.15):
    """Discrete ACO on Euclid parameter choices; four evaluations per ant.

    Pheromone is maintained independently for m1,n1,m2,n2, and the
    admissible n range is conditional on the sampled m. This is a
    factorized construction model, not a proof of completeness.
    """
    rng = random.Random(seed)
    tracker = Tracker('ACO', max_edge)
    pheromone = [[1.0] * (max_m + 1) for _ in range(4)]
    elite_count = max(1, round(ants * elite_fraction))
    for generation in range(iterations + 1):
        batch = []
        for _ in range(ants):
            coords = []
            for m_index, n_index in ((0, 1), (2, 3)):
                if rng.random() < exploration:
                    m = rng.randint(2, max_m)
                    n = rng.randint(1, m - 1)
                else:
                    m = 2 + weighted_choice(rng, pheromone[m_index][2:max_m + 1])
                    n = 1 + weighted_choice(rng, pheromone[n_index][1:m])
                coords.extend((float(m), float(n)))
            score = tracker.evaluate(coords, max_m)
            batch.append((score, coords))
        if generation == iterations:
            break
        # Rank-based pheromone reinforcement; scores may be infinite
        # for inadmissible constructions, so avoid inverse-score weights.
        for trail in pheromone:
            for i in range(1, len(trail)):
                trail[i] = max(0.05, trail[i] * (1.0 - evaporation))
        for rank, (score, coords) in enumerate(sorted(batch, key=lambda x: x[0])[:elite_count]):
            if score == float('inf'):
                continue
            deposit = (elite_count - rank) / elite_count
            for dimension, value in enumerate(coords):
                pheromone[dimension][int(value)] += deposit
    return tracker


def baseline(seed, iterations, particles, max_m, max_edge):
    rng = random.Random(seed)
    tracker = Tracker('RANDOM', max_edge)
    for _ in range(particles*(iterations+1)):
        tracker.evaluate(random_coords(rng, max_m), max_m)
    return tracker


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(fields)
        writer.writerows(rows)


def report(metrics, runs):
    print('\nSUMMARY (30+ independent runs; lower best_fitness is better)')
    for method in ('ACO', 'RANDOM'):
        rows = [r for r in metrics if r['method'] == method]
        for key in ('primitive_bricks', 'unique_candidates', 'best_fitness'):
            vals = [r[key] for r in rows]
            print(f'{method} {key}: mean={statistics.mean(vals):.9g}, '
                  f'median={statistics.median(vals):.9g}, '
                  f'std={statistics.stdev(vals):.9g}')
    for key, lower_better in (('primitive_bricks', False),
                              ('unique_candidates', False),
                              ('best_fitness', True)):
        wins = losses = ties = 0
        differences = []
        for i in range(runs):
            a, b = metrics[2*i][key], metrics[2*i+1][key]
            differences.append(a-b)
            if a == b:
                ties += 1
            elif (a < b) == lower_better:
                wins += 1
            else:
                losses += 1
        print(f'Paired {key}: ACO wins={wins}, RANDOM wins={losses}, '
              f'ties={ties}, mean(ACO-RANDOM)={statistics.mean(differences):.9g}')
    print('Descriptive statistics only; no significance claim.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-edge', type=int, default=10_000_000)
    parser.add_argument('--max-m', type=int, default=120)
    parser.add_argument('--ants', type=int, default=80)
    parser.add_argument('--iterations', type=int, default=200)
    parser.add_argument('--runs', type=int, default=30)
    parser.add_argument('--evaporation', type=float, default=0.20)
    parser.add_argument('--elite-fraction', type=float, default=0.20)
    parser.add_argument('--exploration', type=float, default=0.15)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output', default='bricks_aco_082.csv')
    parser.add_argument('--summary-output', default='aco_082_runs.csv')
    args = parser.parse_args()
    if args.max_edge < 2 or args.max_m < 2 or args.ants < 2 or args.iterations < 0:
        parser.error('Invalid search parameters')
    if args.runs < 30:
        parser.error('--runs must be at least 30')
    if not (0 < args.evaporation < 1 and 0 < args.elite_fraction <= 1
            and 0 <= args.exploration <= 1):
        parser.error('Invalid ACO parameters')
    if Path(args.output).resolve() == Path(args.summary_output).resolve():
        parser.error('Output and summary-output must be different files')
    start = perf_counter()
    metrics = []
    brick_rows = []
    for run in range(1, args.runs + 1):
        seed_aco = args.seed + (run - 1) * 2
        seed_random = seed_aco + 1
        for method, seed, runner in (
            ('ACO', seed_aco, lambda: aco(seed_aco, args.ants, args.iterations,
                args.max_m, args.max_edge, args.evaporation,
                args.elite_fraction, args.exploration)),
            ('RANDOM', seed_random, lambda: baseline(seed_random,
                args.iterations, args.ants, args.max_m, args.max_edge)),
        ):
            t0 = perf_counter()
            tracker = runner()
            expected = 4 * args.ants * (args.iterations + 1)
            assert tracker.evaluations == expected
            metrics.append(dict(run=run, seed=seed, method=method,
                evaluations=tracker.evaluations,
                unique_candidates=len(tracker.unique),
                primitive_bricks=len(tracker.bricks),
                best_fitness=tracker.best_score,
                elapsed_seconds=perf_counter() - t0))
            for edges in sorted(tracker.bricks):
                brick_rows.append([run, seed, method, *tracker.bricks[edges]])
        a, b = metrics[-2:]
        print(f'Run {run:02d}/{args.runs}: '
              f'ACO bricks={a["primitive_bricks"]}, fitness={a["best_fitness"]:.9g}; '
              f'RANDOM bricks={b["primitive_bricks"]}, fitness={b["best_fitness"]:.9g}',
              flush=True)
        write_csv(Path(args.summary_output), METRICS,
                  [[r[k] for k in METRICS] for r in metrics])
        write_csv(Path(args.output), FIELDS, brick_rows)
    report(metrics, args.runs)
    print(f'Total time: {perf_counter()-start:.3f}s')
    print(f'Run metrics: {args.summary_output}')
    print(f'Bricks: {args.output}')


if __name__ == '__main__':
    main()
