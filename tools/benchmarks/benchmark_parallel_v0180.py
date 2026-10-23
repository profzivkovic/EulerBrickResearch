#!/usr/bin/env python3
"""Experimental process-parallel benchmark of unchanged v0.18.0 Numba kernels.
Run from repository root: python tools/benchmarks/benchmark_parallel_v0180.py --max-edge 10000000 --workers 1 2 4
No canonical files are modified. Uses Windows-safe spawn multiprocessing.
"""
import argparse
import importlib.util
import math
import multiprocessing as mp
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ENGINE = None
FACTOR = None
PRIMES = None

def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

def init_worker(src_dir, bound):
    global ENGINE, FACTOR, PRIMES
    import numpy as np
    src_dir = Path(src_dir)
    sys.path.insert(0, str(src_dir))
    FACTOR = load_file('parallel_segmented_factorization', src_dir / 'segmented_factorization.py')
    ENGINE = load_file('parallel_odd_leg_numba_segmented', src_dir / 'odd_leg_numba_segmented.py')
    PRIMES = np.asarray(FACTOR.primes_upto(math.isqrt(bound)), dtype=np.int64)
    # Explicit warmup in each worker, including cached Numba compilation.
    spf = np.asarray(FACTOR.odd_spf_segment(3, 101, PRIMES), dtype=np.uint32)
    ENGINE.fused_segment_kernel(3, 101, 100, spf, PRIMES)

def process_chunk(task):
    import numpy as np
    first_lo, last_lo, bound, segment_odds = task
    result = set()
    tested_total = rejected_total = 0
    segments = 0
    for lo in range(first_lo, last_lo, 2 * segment_odds):
        hi = min(bound, lo + 2 * (segment_odds - 1))
        spf = np.asarray(FACTOR.odd_spf_segment(lo, hi, PRIMES), dtype=np.uint32)
        matches, tested, rejected = ENGINE.fused_segment_kernel(lo, hi, bound, spf, PRIMES)
        tested_total += int(tested)
        rejected_total += int(rejected)
        segments += 1
        for odd, e1, e2 in matches:
            result.add(tuple(sorted((int(odd), int(e1), int(e2)))))
    return result, tested_total, rejected_total, segments

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-edge', type=int, default=10_000_000)
    parser.add_argument('--workers', nargs='+', type=int, default=[1, 2, 4])
    parser.add_argument('--segment-odds', type=int, default=100_000)
    parser.add_argument('--chunk-segments', type=int, default=10)
    parser.add_argument('--src-dir', type=Path, default=Path('src'))
    parser.add_argument('--reference', type=Path, default=Path('data/verified_euler_bricks.csv'))
    parser.add_argument('--confirm-2b', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.max_edge <= 2_000_000_000:
        parser.error('v0.18.0 is safe only up to 2B')
    if args.max_edge > 1_000_000_000 and not args.confirm_2b:
        parser.error('Use --confirm-2b for bounds above 1B')
    if any(w < 1 for w in args.workers) or args.segment_odds < 1 or args.chunk_segments < 1:
        parser.error('Workers, segment size, and chunk size must be positive')
    src = args.src_dir.resolve()
    if not (src / 'odd_leg_numba_segmented.py').is_file() or not (src / 'segmented_factorization.py').is_file():
        parser.error('Cannot find source files; specify --src-dir')
    stable = load_file('parallel_stable_reference', src / 'odd_leg_search.py')
    if stable.VERSION != '0.9.9':
        parser.error('Expected stable odd-leg v0.9.9')
    if not args.reference.is_file():
        parser.error('Reference CSV is required for exact-set verification')
    reference = stable.load_reference(args.reference, args.max_edge)
    stride = 2 * args.segment_odds
    chunk_stride = stride * args.chunk_segments
    tasks = [(lo, min(args.max_edge + 1, lo + chunk_stride), args.max_edge, args.segment_odds)
             for lo in range(3, args.max_edge + 1, chunk_stride)]
    print(f'Bound={args.max_edge:,}; reference={len(reference)}; tasks={len(tasks)}; CPUs={os.cpu_count()}', flush=True)
    baseline = None
    for workers in args.workers:
        t0 = time.perf_counter()
        results = set()
        tested = rejected = segments = 0
        ctx = mp.get_context('spawn')
        with ProcessPoolExecutor(max_workers=workers, mp_context=ctx,
                                 initializer=init_worker, initargs=(str(src), args.max_edge)) as pool:
            for triples, ntested, nrejected, nsegments in pool.map(process_chunk, tasks):
                results.update(triples)
                tested += ntested
                rejected += nrejected
                segments += nsegments
        elapsed = time.perf_counter() - t0
        for triple in results:
            if not stable.verify_brick(triple, args.max_edge):
                raise AssertionError(f'Invalid triple: {triple}')
        missing, extra = reference - results, results - reference
        if missing or extra:
            print(f'FAIL workers={workers} missing={len(missing)} extra={len(extra)}', flush=True)
            raise SystemExit(1)
        stats = (len(results), tested, rejected, segments)
        if baseline is None:
            baseline = (elapsed, stats)
        elif stats != baseline[1]:
            raise AssertionError(f'Counter mismatch: {stats} vs {baseline[1]}')
        print(f'workers={workers} wall={elapsed:.3f}s speedup={baseline[0]/elapsed:.2f}x '
              f'bricks={len(results)} tested={tested} rejected={rejected} segments={segments} EXACT SET MATCH', flush=True)
    print('PASS: all configurations agree with the verified catalog', flush=True)

if __name__ == '__main__':
    mp.freeze_support()
    main()
