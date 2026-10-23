#!/usr/bin/env python3
"""Resumable process-parallel v0.18.0 search; no canonical files modified.

Example (repository root):
 python tools/runners/checkpoint_parallel_v0180.py --max-edge 100000000 --workers 4 --checkpoint-dir checkpoints/test_100m --reference data/verified_euler_bricks.csv
Resume by running the identical command again. --stop-after-chunks 3 simulates interruption.
"""
import argparse
import hashlib
import json
import multiprocessing as mp
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import sys
import time

import sys
from pathlib import Path

BENCHMARKS_DIR = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCHMARKS_DIR))

# Reuse exactly the existing benchmark's worker implementation.
import benchmark_parallel_v0180 as engine

FORMAT = 1

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
    triples, tested, rejected, segments = engine.process_chunk(task)
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
    args = p.parse_args()
    if not 3 <= args.max_edge <= 2_000_000_000 or (args.max_edge > 1_000_000_000 and not args.confirm_2b):
        p.error('v0.18.0 supports <=2B; --confirm-2b required above 1B')
    if min(args.workers, args.segment_odds, args.chunk_segments) < 1 or args.stop_after_chunks < 0:
        p.error('Invalid workers/segment/chunk/stop setting')
    src = args.src_dir.resolve()
    required = ['odd_leg_search.py', 'odd_leg_numba_segmented.py', 'segmented_factorization.py']
    if any(not (src / f).is_file() for f in required):
        p.error('Missing src files; use --src-dir')
    if not args.reference.is_file():
        p.error('Reference CSV missing')
    stable = engine.load_file('checkpoint_stable_reference', src / 'odd_leg_search.py')
    if stable.VERSION != '0.9.9':
        p.error('Unexpected stable engine version')
    reference = stable.load_reference(args.reference, args.max_edge)
    stride = 2 * args.segment_odds * args.chunk_segments
    tasks = [(lo, min(args.max_edge + 1, lo + stride), args.max_edge, args.segment_odds)
             for lo in range(3, args.max_edge + 1, stride)]
    config = {'format': FORMAT, 'max_edge': args.max_edge, 'segment_odds': args.segment_odds,
              'chunk_segments': args.chunk_segments, 'tasks': len(tasks),
              'sources': {f: sha256(src / f) for f in required}}
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
    print(f'Bound={args.max_edge:,} workers={args.workers} chunks={len(tasks)} resumed={len(completed)} pending={len(pending)} reference={len(reference)}', flush=True)
    start = time.perf_counter()
    saved = 0
    if pending:
        ctx = mp.get_context('spawn')
        with ProcessPoolExecutor(max_workers=args.workers, mp_context=ctx,
                                 initializer=engine.init_worker, initargs=(str(src), args.max_edge)) as pool:
            # Bounded submission keeps memory use modest and stop-after meaningful.
            iterator = iter(pending)
            active = {}
            for _ in range(min(args.workers, len(pending))):
                i, task = next(iterator)
                active[pool.submit(task_result, i, task)] = i
            while active:
                future = next(as_completed(active))
                i = active.pop(future)
                index, payload = future.result()
                if index != i:
                    raise AssertionError('Wrong chunk returned')
                atomic_json(chunks / f'{i:08d}.json', sealed(payload))
                completed[i] = payload
                saved += 1
                if saved % 10 == 0 or saved == 1:
                    print(f'checkpoint saved={saved} total={len(completed)}/{len(tasks)} elapsed={time.perf_counter()-start:.1f}s', flush=True)
                if args.stop_after_chunks and saved >= args.stop_after_chunks:
                    for f in active:
                        f.cancel()
                    print(f'INTENTIONAL STOP: saved {saved} new chunks; rerun same command without --stop-after-chunks', flush=True)
                    return 0
                next_task = next(iterator, None)
                if next_task is not None:
                    j, task = next_task
                    active[pool.submit(task_result, j, task)] = j
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
    missing, extra = reference - triples, triples - reference
    if missing or extra:
        print(f'FAIL missing={len(missing)} extra={len(extra)}', flush=True)
        print(f'missing examples: {sorted(missing)[:5]} extra examples: {sorted(extra)[:5]}', flush=True)
        return 1
    summary = {'config_sha256': hashlib.sha256(canonical(config)).hexdigest(),
               'bricks': len(triples), 'tested': tested, 'rejected': rejected,
               'segments': segments, 'chunks': len(tasks), 'exact_set_match': True}
    atomic_json(folder / 'result.json', sealed(summary))
    print(f'PASS EXACT SET MATCH bricks={len(triples)} tested={tested} rejected={rejected} segments={segments} '
          f'chunks={len(tasks)} wall_this_run={time.perf_counter()-start:.3f}s', flush=True)
    return 0

if __name__ == '__main__':
    mp.freeze_support()
    sys.exit(main())
