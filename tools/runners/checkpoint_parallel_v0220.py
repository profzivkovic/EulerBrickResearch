#!/usr/bin/env python3
"""Resumable process-parallel v0.22.0 experimental Numba-SPF search; no canonical files modified.

Example (repository root):
 python tools/runners/checkpoint_parallel_v0220.py --max-edge 100000000 --workers 4 --checkpoint-dir checkpoints/test_100m --reference data/verified_euler_bricks.csv
Resume by running the identical command again. --stop-after-chunks 3 simulates interruption.
"""
import argparse
import importlib.util
import math
import numpy as np
import hashlib
import json
import multiprocessing as mp
import os
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from pathlib import Path
import sys
import time

# Independent v0.20 worker: never import or mutate the v0.18 benchmark.
ENGINE = FACTOR = PRIMES = None
FORMAT = 4
INT64_MAX = (1 << 63) - 1

def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

from numba import njit

@njit(cache=False)
def spf_numba_core(lo, hi, primes):
    count = (hi - lo) // 2 + 1
    spf = np.zeros(count, dtype=np.uint32)
    for j in range(primes.size):
        p = np.int64(primes[j])
        if p == 2:
            continue
        if p * p > hi:
            break
        start = ((lo + p - 1) // p) * p
        if start < p * p:
            start = p * p
        if start % 2 == 0:
            start += p
        for n in range(start, hi + 1, 2 * p):
            idx = (n - lo) // 2
            if spf[idx] == 0:
                spf[idx] = np.uint32(p)
    return spf

def init_worker(src_dir, bound):
    global ENGINE, FACTOR, PRIMES
    src_dir = Path(src_dir)
    sys.path.insert(0, str(src_dir))
    FACTOR = load_file('v020_factor', src_dir / 'segmented_factorization.py')
    ENGINE = load_file('v020_kernel', src_dir / 'odd_leg_numba_1000b_experimental.py')
    PRIMES = np.asarray(FACTOR.primes_upto(math.isqrt(bound)), dtype=np.int64)
    spf = spf_numba_core(np.int64(3), np.int64(101), PRIMES)
    ENGINE.fused_segment_kernel(3, 101, 100, spf, PRIMES)

def process_chunk(task):
    first_lo, last_lo, bound, segment_odds = task
    triples = set()
    tested_total = rejected_total = 0
    segments = 0
    for lo in range(first_lo, last_lo, 2 * segment_odds):
        hi = min(bound, lo + 2 * (segment_odds - 1))
        spf = spf_numba_core(np.int64(lo), np.int64(hi), PRIMES)
        matches, tested, rejected = ENGINE.fused_segment_kernel(lo, hi, bound, spf, PRIMES)
        if tested < 0 or rejected < 0:
            raise OverflowError('Numba segment counter overflow detected')
        tested_total += int(tested)
        rejected_total += int(rejected)
        segments += 1
        for odd, e1, e2 in matches:
            triples.add(tuple(sorted((int(odd), int(e1), int(e2)))))
    return triples, tested_total, rejected_total, segments


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def atomic_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    with tmp.open('wb') as f:
        f.write(canonical(obj) + b'\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def sealed(payload):
    return {'payload': payload, 'sha256': hashlib.sha256(canonical(payload)).hexdigest()}

def read_sealed(path):
    item = json.loads(path.read_text(encoding='ascii'))
    if set(item) != {'payload', 'sha256'} or item['sha256'] != hashlib.sha256(canonical(item['payload'])).hexdigest():
        raise ValueError(f'Corrupt checkpoint: {path}')
    return item['payload']

def task_result(index, task):
    triples, tested, rejected, segments = process_chunk(task)
    return index, {'index': index, 'first_lo': task[0], 'last_lo': task[1],
                   'triples': [list(t) for t in sorted(triples)],
                   'tested': tested, 'rejected': rejected, 'segments': segments}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--max-edge', type=int, required=True)
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--segment-odds', type=int, default=100000)
    p.add_argument('--chunk-segments', type=int, default=10)
    p.add_argument('--checkpoint-dir', type=Path, required=True)
    p.add_argument('--src-dir', type=Path, default=Path('src'))
    p.add_argument('--reference', type=Path, default=Path('data/verified_euler_bricks.csv'))
    p.add_argument('--stop-after-chunks', type=int, default=0, help='Stop after this many newly saved chunks (test only)')
    p.add_argument('--confirm-2b', action='store_true')
    p.add_argument('--confirm-10b', action='store_true')
    p.add_argument('--confirm-20b', action='store_true')
    p.add_argument('--progress-seconds', type=float, default=30.0)
    p.add_argument('--experimental-no-reference', action='store_true', help='Allow catalog-free validation; validate previous-catalog subset separately')
    args = p.parse_args()
    if not 3 <= args.max_edge <= 20_000_000_000:
        p.error('v0.22.0 checkpoint candidate is intentionally capped at 20B pending full 50B approval')
    if args.max_edge > 10_000_000_000 and not (args.confirm_20b and args.experimental_no_reference):
        p.error('Above 10B requires --confirm-20b --experimental-no-reference')
    if 1_000_000_000 < args.max_edge <= 2_000_000_000 and not args.confirm_2b:
        p.error('--confirm-2b required above 1B')
    if 2_000_000_000 < args.max_edge <= 10_000_000_000 and not (args.confirm_10b and args.experimental_no_reference):
        p.error('Above 2B requires --confirm-10b --experimental-no-reference')
    if args.segment_odds > 100_000 or args.progress_seconds <= 0:
        p.error('Segment limit 100000; progress interval must be positive')
    if min(args.workers, args.segment_odds, args.chunk_segments) < 1 or args.stop_after_chunks < 0:
        p.error('Invalid workers/segment/chunk/stop setting')
    src = args.src_dir.resolve()
    required = ['odd_leg_search.py', 'odd_leg_numba_1000b_experimental.py', 'safe_arithmetic_1000b.py', 'segmented_factorization.py']
    if any(not (src / f).is_file() for f in required):
        p.error('Missing src files; use --src-dir')
    if not args.experimental_no_reference and not args.reference.is_file():
        p.error('Reference CSV missing')
    sys.path.insert(0, str(src))
    stable = load_file('checkpoint_stable_reference_v020', src / 'odd_leg_search.py')
    if stable.VERSION != '0.9.9':
        p.error('Unexpected stable engine version')
    reference = None if args.experimental_no_reference else stable.load_reference(args.reference, args.max_edge)
    stride = 2 * args.segment_odds * args.chunk_segments
    tasks = [(lo, min(args.max_edge + 1, lo + stride), args.max_edge, args.segment_odds)
             for lo in range(3, args.max_edge + 1, stride)]
    config = {'format': FORMAT, 'max_edge': args.max_edge, 'segment_odds': args.segment_odds,
              'chunk_segments': args.chunk_segments, 'tasks': len(tasks), 'reference_mode': 'none' if reference is None else 'exact',
              'reference_sha256': None if reference is None else sha256(args.reference),
              'sources': {f: sha256(src / f) for f in required},
              'spf_mode': 'numba_v0220', 'runner_sha256': sha256(Path(__file__).resolve())}
    folder = args.checkpoint_dir.resolve()
    manifest = folder / 'config.json'
    if manifest.exists():
        if read_sealed(manifest) != config:
            p.error('Checkpoint configuration or source hashes changed; use a new checkpoint directory')
    else:
        if folder.exists() and any(folder.iterdir()):
            p.error('Nonempty directory without config.json; refusing to overwrite')
        atomic_json(manifest, sealed(config))
    chunks = folder / 'chunks'
    chunks.mkdir(exist_ok=True)
    completed = {}
    for i, task in enumerate(tasks):
        path = chunks / f'{i:08d}.json'
        if not path.exists():
            continue
        try:
            payload = read_sealed(path)
            if payload['index'] != i or payload['first_lo'] != task[0] or payload['last_lo'] != task[1]:
                raise ValueError('chunk interval mismatch')
            if any(len(t) != 3 or tuple(t) != tuple(sorted(t)) for t in payload['triples']):
                raise ValueError('invalid triple representation')
            if any(not isinstance(payload[k], int) or payload[k] < 0 for k in ('tested', 'rejected', 'segments')):
                raise ValueError('invalid counters')
            expected_segments = len(range(task[0], task[1], 2 * args.segment_odds))
            if payload['segments'] != expected_segments:
                raise ValueError('segment count mismatch')
            completed[i] = payload
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
            print(f'Invalid checkpoint {path}: {e}; recalculating', flush=True)
            path.rename(path.with_suffix('.invalid'))
    pending = [(i, task) for i, task in enumerate(tasks) if i not in completed]
    print(f'Bound={args.max_edge:,} workers={args.workers} chunks={len(tasks)} resumed={len(completed)} pending={len(pending)} reference={len(reference) if reference is not None else "NONE"}', flush=True)
    start = time.perf_counter()
    saved = 0
    last_report = start
    def progress(tag):
        elapsed = time.perf_counter() - start
        done = len(completed)
        rate = saved / elapsed if elapsed > 0 else 0.0
        eta = (len(tasks) - done) / rate / 3600 if rate > 0 else None
        eta_text = f'{eta:.2f}h' if eta is not None else 'unknown'
        print(f'PROGRESS {tag}: {done:,}/{len(tasks):,} ({100*done/len(tasks):.3f}%) '
              f'new={saved:,} speed={rate:.4f} chunks/s ETA={eta_text}', flush=True)
    progress('START')
    if pending:
        ctx = mp.get_context('spawn')
        with ProcessPoolExecutor(max_workers=args.workers, mp_context=ctx,
                                 initializer=init_worker, initargs=(str(src), args.max_edge)) as pool:
            # Bounded submission keeps memory use modest and stop-after meaningful.
            iterator = iter(pending)
            active = {}
            for _ in range(min(args.workers, len(pending))):
                i, task = next(iterator)
                active[pool.submit(task_result, i, task)] = i
            while active:
                finished, _ = wait(active, timeout=args.progress_seconds, return_when=FIRST_COMPLETED)
                if not finished:
                    progress('HEARTBEAT')
                    continue
                future = next(iter(finished))
                i = active.pop(future)
                index, payload = future.result()
                if index != i:
                    raise AssertionError('Wrong chunk returned')
                for triple in payload['triples']:
                    if not stable.verify_brick(tuple(triple), args.max_edge):
                        raise AssertionError(f'Invalid brick before checkpoint: {triple}')
                atomic_json(chunks / f'{i:08d}.json', sealed(payload))
                completed[i] = payload
                saved += 1
                if saved == 1 or saved % 10 == 0 or time.perf_counter() - last_report >= args.progress_seconds:
                    progress('CHECKPOINT')
                    last_report = time.perf_counter()
                if args.stop_after_chunks and saved >= args.stop_after_chunks:
                    for f in active:
                        f.cancel()
                    print(f'INTENTIONAL STOP: saved {saved} new chunks; rerun same command without --stop-after-chunks', flush=True)
                    return 0
                next_task = next(iterator, None)
                if next_task is not None:
                    j, task = next_task
                    active[pool.submit(task_result, j, task)] = j
    progress('COMPLETE')
    if len(completed) != len(tasks):
        raise AssertionError('Missing chunks')
    triples = set()
    tested = rejected = segments = 0
    for i in range(len(tasks)):
        item = completed[i]
        triples.update(map(tuple, item['triples']))
        tested += item['tested']
        rejected += item['rejected']
        segments += item['segments']
    for t in triples:
        if not stable.verify_brick(t, args.max_edge):
            raise AssertionError(f'Invalid brick: {t}')
    missing, extra = (set(), set()) if reference is None else (reference - triples, triples - reference)
    if missing or extra:
        print(f'FAIL missing={len(missing)} extra={len(extra)}', flush=True)
        print(f'missing examples: {sorted(missing)[:5]} extra examples: {sorted(extra)[:5]}', flush=True)
        return 1
    summary = {'config_sha256': hashlib.sha256(canonical(config)).hexdigest(),
               'bricks': len(triples), 'tested': tested, 'rejected': rejected,
               'segments': segments, 'chunks': len(tasks), 'exact_set_match': reference is not None, 'all_bricks_verified': True}
    atomic_json(folder / 'result.json', sealed(summary))
    print(f'PASS {"EXACT SET MATCH" if reference is not None else "BRICKS VERIFIED (NO CATALOG)"} bricks={len(triples)} tested={tested} rejected={rejected} segments={segments} '
          f'chunks={len(tasks)} wall_this_run={time.perf_counter()-start:.3f}s', flush=True)
    return 0

if __name__ == '__main__':
    mp.freeze_support()
    sys.exit(main())
