#!/usr/bin/env python3
"""EulerBrickResearch v0.8.1: diversity-preserving PSO vs random, 30+ runs."""
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


def pso(seed, particles, iterations, max_m, max_edge,
        stagnation=12, restart_fraction=0.30, neighborhoods=5):
    """Ring-neighborhood PSO with personal-stagnation restarts.

    Neighborhoods and restarts preserve exploration; exact candidate
    validation remains in Tracker. Every restart consumes one evaluation,
    so the evaluation budget matches the random baseline exactly.
    """
    rng = random.Random(seed)
    tracker = Tracker('PSO', max_edge)
    positions = [random_coords(rng, max_m) for _ in range(particles)]
    velocities = [[0.0] * 4 for _ in range(particles)]
    personal = [pos[:] for pos in positions]
    personal_score = [tracker.evaluate(pos, max_m) for pos in positions]
    stagnant = [0] * particles
    restart_count = max(1, round(particles * restart_fraction))
    for iteration in range(iterations):
        # Select neighborhoods using only the previous iteration's scores.
        guides = []
        for i in range(particles):
            group = i * neighborhoods // particles
            members = range(group * particles // neighborhoods,
                            (group + 1) * particles // neighborhoods)
            winner = min(members, key=lambda j: personal_score[j])
            guides.append(personal[winner][:])
        # Restart a fraction of the most stagnant particles at fixed intervals.
        # Restarting changes their positions but never increases the budget.
        selected = set()
        if stagnation > 0 and (iteration + 1) % stagnation == 0:
            selected = set(sorted(range(particles),
                                  key=lambda i: (-stagnant[i], i))[:restart_count])
        for i in range(particles):
            if i in selected:
                positions[i] = random_coords(rng, max_m)
                velocities[i] = [0.0] * 4
                personal[i] = positions[i][:]
                score = tracker.evaluate(positions[i], max_m)
                personal_score[i] = score
                stagnant[i] = 0
                continue
            for k in range(4):
                velocities[i][k] = max(-max_m / 3, min(max_m / 3,
                    0.65 * velocities[i][k]
                    + 1.4 * rng.random() * (personal[i][k] - positions[i][k])
                    + 1.4 * rng.random() * (guides[i][k] - positions[i][k])))
                positions[i][k] = max(1.0, min(float(max_m),
                                                positions[i][k] + velocities[i][k]))
            score = tracker.evaluate(positions[i], max_m)
            if score < personal_score[i]:
                personal_score[i] = score
                personal[i] = positions[i][:]
                stagnant[i] = 0
            else:
                stagnant[i] += 1
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
    print('\nSUMMARY (independent runs; lower best_fitness is better)')
    for method in ('PSO', 'RANDOM'):
        rows = [r for r in metrics if r['method'] == method]
        for key in ('primitive_bricks', 'unique_candidates', 'best_fitness'):
            vals = [r[key] for r in rows]
            print(f'{method} {key}: mean={statistics.mean(vals):.9g}, '
                  f'median={statistics.median(vals):.9g}, '
                  f'std={statistics.stdev(vals):.9g}, '
                  f'min={min(vals):.9g}, max={max(vals):.9g}')
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
        print(f'Paired {key}: PSO wins={wins}, RANDOM wins={losses}, '
              f'ties={ties}, mean(PSO-RANDOM)={statistics.mean(differences):.9g}')
    print('Descriptive statistics only; no significance claim.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-edge', type=int, default=10_000_000)
    parser.add_argument('--max-m', type=int, default=120)
    parser.add_argument('--particles', type=int, default=80)
    parser.add_argument('--iterations', type=int, default=200)
    parser.add_argument('--runs', type=int, default=30)
    parser.add_argument('--stagnation', type=int, default=12)
    parser.add_argument('--restart-fraction', type=float, default=0.30)
    parser.add_argument('--neighborhoods', type=int, default=5)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output', default='bricks_pso_081.csv')
    parser.add_argument('--summary-output', default='pso_081_runs.csv')
    args = parser.parse_args()
    if min(args.max_edge, args.max_m, args.particles) < 2 or args.iterations < 0:
        parser.error('Invalid search parameters')
    if not (1 <= args.neighborhoods <= args.particles):
        parser.error('--neighborhoods must be between 1 and particles')
    if args.stagnation < 1 or not (0 < args.restart_fraction <= 1):
        parser.error('Invalid stagnation/restart-fraction')
    if args.runs < 30:
        parser.error('--runs must be at least 30')
    if Path(args.output).resolve() == Path(args.summary_output).resolve():
        parser.error('Output and summary-output must be different files')

    start = perf_counter()
    metrics = []
    brick_rows = []
    for run in range(1, args.runs+1):
        # Independent RNG streams, reproducible across executions.
        seed_pso = args.seed + (run-1)*2
        seed_random = seed_pso + 1
        for method, seed, runner in (
            ('PSO', seed_pso, lambda: pso(seed_pso, args.particles,
                args.iterations, args.max_m, args.max_edge,
                args.stagnation, args.restart_fraction, args.neighborhoods)),
            ('RANDOM', seed_random, lambda: baseline(seed_random,
                args.iterations, args.particles, args.max_m, args.max_edge)),
        ):
            t0 = perf_counter()
            tracker = runner()
            expected = 4*args.particles*(args.iterations+1)
            assert tracker.evaluations == expected
            metrics.append(dict(run=run, seed=seed, method=method,
                evaluations=tracker.evaluations,
                unique_candidates=len(tracker.unique),
                primitive_bricks=len(tracker.bricks),
                best_fitness=tracker.best_score,
                elapsed_seconds=perf_counter()-t0))
            for edges in sorted(tracker.bricks):
                brick_rows.append([run, seed, method, *tracker.bricks[edges]])
        a, b = metrics[-2:]
        print(f'Run {run:02d}/{args.runs}: '
              f'PSO bricks={a["primitive_bricks"]}, fitness={a["best_fitness"]:.9g}; '
              f'RANDOM bricks={b["primitive_bricks"]}, fitness={b["best_fitness"]:.9g}',
              flush=True)
        # Save checkpoints after each complete paired run.
        write_csv(Path(args.summary_output), METRICS,
                  [[r[k] for k in METRICS] for r in metrics])
        write_csv(Path(args.output), FIELDS, brick_rows)
    report(metrics, args.runs)
    print(f'Total time: {perf_counter()-start:.3f}s')
    print(f'Run metrics: {args.summary_output}')
    print(f'Bricks: {args.output}')


if __name__ == '__main__':
    main()
