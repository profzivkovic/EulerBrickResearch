#!/usr/bin/env python3
"""Run the unchanged v0.18.0 checkpoint search locally and mirror to Drive.

Run from repository root.  Local checkpoint files are written on the VM; every
completed, sealed checkpoint is copied to durable storage while search runs.
Restart the same command to restore and resume.  This does NOT enable 10B.
"""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def checked(path):
    from checkpoint_parallel_v0180 import read_sealed
    return read_sealed(path)


def transfer(src, dst):
    """Validate, copy via temporary file, hash-check, publish, hash-check."""
    checked(src)
    source_hash = digest(src)
    if dst.exists():
        checked(dst)
        if digest(dst) != source_hash:
            raise RuntimeError(f'Checkpoint conflict; refusing overwrite: {dst}')
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + f'.{os.getpid()}.partial')
    try:
        with src.open('rb') as inp, tmp.open('wb') as out:
            shutil.copyfileobj(inp, out, length=1024 * 1024)
            out.flush()
            os.fsync(out.fileno())
        if digest(tmp) != source_hash:
            raise RuntimeError(f'SHA-256 mismatch copying {src}')
        checked(tmp)
        os.replace(tmp, dst)
        if digest(dst) != source_hash:
            raise RuntimeError(f'SHA-256 mismatch publishing {dst}')
        checked(dst)
        return True
    finally:
        if tmp.exists():
            tmp.unlink()


def sync_files(source, destination, known=None):
    """Only complete .json checkpoints; never publish .tmp/.partial files."""
    count = 0
    paths = [source / 'config.json']
    folder = source / 'chunks'
    if folder.exists():
        paths.extend(sorted(folder.glob('*.json')))
    paths.append(source / 'result.json')
    for src in paths:
        if not src.is_file():
            continue
        rel = src.relative_to(source)
        dst = destination / rel
        key = str(dst)
        if known is not None and key in known:
            continue
        count += transfer(src, dst)
        if known is not None:
            known.add(key)
    return count


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--max-edge', required=True, type=int)
    p.add_argument('--workers', type=int, default=2)
    p.add_argument('--local-dir', type=Path, required=True)
    p.add_argument('--drive-dir', type=Path, required=True)
    p.add_argument('--reference', type=Path, default=Path('data/verified_euler_bricks.csv'))
    p.add_argument('--src-dir', type=Path, default=Path('src'))
    p.add_argument('--runner', type=Path, default=Path('tools/runners/checkpoint_parallel_v0180.py'))
    p.add_argument('--segment-odds', type=int, default=100000)
    p.add_argument('--chunk-segments', type=int, default=10)
    p.add_argument('--sync-seconds', type=float, default=2.0)
    p.add_argument('--stop-after-chunks', type=int, default=0)
    p.add_argument('--confirm-2b', action='store_true')
    a = p.parse_args()
    if not 3 <= a.max_edge <= 2_000_000_000:
        p.error('v0.18.0 supports up to 2B only; 10B is NOT supported')
    if a.workers < 1 or a.sync_seconds <= 0 or a.stop_after_chunks < 0:
        p.error('Invalid workers, sync interval or stop-after-chunks')
    local, drive = a.local_dir.resolve(), a.drive_dir.resolve()
    if local == drive or local in drive.parents or drive in local.parents:
        p.error('Local and durable checkpoint directories must be separate')
    if not a.runner.is_file() or not a.reference.is_file():
        p.error('Runner or reference missing; run from repository root')
    if str(drive).startswith('/content/drive/') and not os.path.ismount('/content/drive'):
        p.error('Google Drive is not mounted at /content/drive')
    if not drive.is_dir():
        p.error('Durable directory missing; create it after mounting Drive')
    sys.path.insert(0, str(a.runner.resolve().parent))
    local.mkdir(parents=True, exist_ok=True)

    print('RESTORE: checking durable Drive checkpoints', flush=True)
    restored = sync_files(drive, local)
    print(f'RESTORE: {restored} file(s) copied to VM', flush=True)
    known = set()
    initial = sync_files(local, drive, known)
    print(f'MIRROR: {initial} local-only file(s) copied to Drive', flush=True)

    cmd = [sys.executable, '-u', str(a.runner.resolve()),
           '--max-edge', str(a.max_edge), '--workers', str(a.workers),
           '--checkpoint-dir', str(local), '--reference', str(a.reference.resolve()),
           '--src-dir', str(a.src_dir.resolve()), '--segment-odds', str(a.segment_odds),
           '--chunk-segments', str(a.chunk_segments)]
    if a.confirm_2b:
        cmd.append('--confirm-2b')
    if a.stop_after_chunks:
        cmd.extend(['--stop-after-chunks', str(a.stop_after_chunks)])
    print('RUN:', ' '.join(cmd), flush=True)

    # The search process writes locally. The parent publishes finished chunks
    # independently of the search, including during a long-running computation.
    # Avoid stdout PIPE deadlocks: subprocess inherits stdout/stderr.
    proc = subprocess.Popen(cmd)
    mirrored = 0
    last_progress = time.monotonic()
    interrupted = False
    sync_error = None
    try:
        while proc.poll() is None:
            new = sync_files(local, drive, known)
            mirrored += new
            if new:
                print(f'MIRROR LIVE: +{new} durable file(s), total_new={mirrored}', flush=True)
                last_progress = time.monotonic()
            time.sleep(a.sync_seconds)
    except KeyboardInterrupt:
        interrupted = True
        print('INTERRUPT: stopping search and flushing completed checkpoints', flush=True)
    except Exception as exc:
        sync_error = exc
        print(f'SYNC ERROR: {exc}; stopping search', file=sys.stderr, flush=True)
    finally:
        if (interrupted or sync_error is not None) and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        # Run the final mirror even on Ctrl+C or a mid-run sync failure.
        # A failed final mirror must never be presented as successful.
        try:
            new = sync_files(local, drive, known)
            mirrored += new
            if new:
                print(f'MIRROR FINAL: +{new} durable file(s)', flush=True)
        except Exception as exc:
            sync_error = exc
            print(f'FINAL SYNC ERROR: {exc}', file=sys.stderr, flush=True)

    if sync_error is not None:
        return 2
    if interrupted:
        print(f'INTERRUPTED SAFELY: {mirrored} new durable file(s); rerun to resume', flush=True)
        return 130
    print(f'MIRROR: published {mirrored} new durable file(s)', flush=True)
    if proc.returncode:
        print(f'FAIL: search exit code {proc.returncode}', flush=True)
        return proc.returncode
    if a.stop_after_chunks:
        print('INTENTIONAL STOP: rerun without --stop-after-chunks', flush=True)
        return 0
    result = local / 'result.json'
    if not result.is_file():
        raise RuntimeError('Search succeeded without result.json')
    summary = checked(result)
    if not summary.get('exact_set_match'):
        raise RuntimeError('Final result is not EXACT SET MATCH')
    if not (drive / 'result.json').is_file() or digest(result) != digest(drive / 'result.json'):
        raise RuntimeError('Final result was not mirrored')
    print(f'PASS DURABLE MIRROR bricks={summary["bricks"]} chunks={summary["chunks"]}', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
