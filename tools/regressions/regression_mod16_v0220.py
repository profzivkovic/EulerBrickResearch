"""Exact segment-by-segment v0.21 vs v0.22 comparison, with timing.

Run from repository root: python tools/regressions/regression_mod16_v0220.py
Does not write catalogs, checkpoints, or change the production runner.
"""
import argparse
import importlib.util
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Cannot load {path}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(engine, segments, bound, primes):
    matches = set()
    tested = rejected = 0
    start = time.perf_counter()
    for lo, hi, spf in segments:
        triples, t, r = engine.fused_segment_kernel(lo, hi, bound, spf, primes)
        tested += int(t)
        rejected += int(r)
        for odd, e1, e2 in triples:
            matches.add(tuple(sorted((int(odd), int(e1), int(e2)))))
    return matches, tested, rejected, time.perf_counter() - start


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--max-edge', type=int, default=100_000)
    ap.add_argument('--segment-odds', type=int, default=10_000)
    args = ap.parse_args()
    if not 3 <= args.max_edge <= 1_000_000 or args.segment_odds < 1:
        ap.error('Allowed regression bound: 3..1,000,000; segment-odds >= 1')
    baseline = load('baseline_v0210', SRC / 'odd_leg_numba_1000b_experimental.py')
    candidate = load('candidate_v0220', SRC / 'odd_leg_numba_50b_experimental_v0220.py')
    factor = load('factor_v0220', SRC / 'segmented_factorization.py')
    primes = np.asarray(factor.primes_upto(math.isqrt(args.max_edge)), dtype=np.int64)
    segments = []
    for lo in range(3, args.max_edge + 1, 2 * args.segment_odds):
        hi = min(args.max_edge, lo + 2 * (args.segment_odds - 1))
        spf = np.asarray(factor.odd_spf_segment(lo, hi, primes), dtype=np.uint32)
        segments.append((lo, hi, spf))
    # JIT warm-up excluded from timing.
    for engine in (baseline, candidate):
        engine.fused_segment_kernel(3, 101, 100, np.asarray(factor.odd_spf_segment(3, 101, primes), dtype=np.uint32), primes)
    old = run(baseline, segments, args.max_edge, primes)
    new = run(candidate, segments, args.max_edge, primes)
    print(f'Bound={args.max_edge:,}; segments={len(segments)}')
    print(f'Baseline: bricks={len(old[0])}, tested={old[1]}, rejected={old[2]}, kernel={old[3]:.6f}s')
    print(f'Candidate: bricks={len(new[0])}, tested={new[1]}, rejected={new[2]}, kernel={new[3]:.6f}s')
    if old[:3] != new[:3]:
        print('Missing:', sorted(old[0] - new[0])[:10]); print('Extra:', sorted(new[0] - old[0])[:10])
        raise SystemExit('FAIL: set or counters differ')
    print(f'PASS: exact set and counters; kernel speedup={old[3]/new[3]:.3f}x')
    print('NOTE: small-bound regression only; not 50B arithmetic or runner approval')


if __name__ == '__main__':
    main()

