#!/usr/bin/env python3
"""Run unchanged v0.18.0 checkpoint search on fast local storage, mirror to Drive.

Run from the repository root. The durable directory should be a mounted Google
Drive directory. Re-run the same command after Colab reconnects to resume.

This is a companion to tools/checkpoint_parallel_v0180.py, not a new kernel.
No 10B support: the underlying v0.18.0 runner is limited to 2B.
"""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
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
    # Reuse exactly the checkpoint file validator, including its payload seal.
    from checkpoint_parallel_v0180 import read_sealed
    return read_sealed(path)


def transfer(src, dst):
    """Copy, flush, verify, publish, and verify again (no overwrite on conflict)."""
    checked(src)
    src_hash = digest(src)
    if dst.exists():
        checked(dst)
        if digest(dst) != src_hash:
            raise RuntimeError(f'Checkpoint conflict (refusing overwrite): {dst}')
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + f'.{os.getpid()}.partial')
    try:
        with src.open('rb') as inp, tmp.open('wb') as out:
            shutil.copyfileobj(inp, out, length=1024 * 1024)
            out.flush()
            os.fsync(out.fileno())
        if digest(tmp) != src_hash:
            raise RuntimeError(f'Copy SHA-256 mismatch: {tmp}')
        checked(tmp)
        # On a mounted Drive, rename visibility/durability is subject to FUSE
        # semantics; on restart we always re-read and validate the full file.
        os.replace(tmp, dst)
        if digest(dst) != src_hash:
            raise RuntimeError(f'Published SHA-256 mismatch: {dst}')
        checked(dst)
        return True
    finally:
        if tmp.exists():
            tmp.unlink()


def sync_files(source, destination, known=None):
    """Mirror only complete, validated checkpoint files; never mirror .tmp."""
    count = 0
    def send(src, dst):
        nonlocal count
        key = str(dst)
        if known is not None and key in known:
            return
        count += transfer(src, dst)
        if known is not None:
            known.add(key)
    for relative in ('config.json',):
        f = source / relative
        if f.is_file():
            send(f, destination / relative)
    folder = source / 'chunks'
    if folder.exists():
        for f in sorted(folder.glob('*.json')):
            send(f, destination / 'chunks' / f.name)
    f = source / 'result.json'
    if f.is_file():
        send(f, destination / 'result.json')
    return count


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--max-edge', required=True, type=int)
    p.add_argument('--workers', type=int, default=2)
    p.add_argument('--local-dir', type=Path, required=True,
                   help='Fast ephemeral Colab VM directory, e.g. /content/euler_work/500m')
    p.add_argument('--drive-dir', type=Path, required=True,
                   help='Persistent mounted Google Drive directory')
    p.add_argument('--reference', type=Path, default=Path('data/verified_euler_bricks.csv'))
    p.add_argument('--src-dir', type=Path, default=Path('src'))
    p.add_argument('--runner', type=Path, default=Path('tools/checkpoint_parallel_v0180.py'))
    p.add_argument('--segment-odds', type=int, default=100000)
    p.add_argument('--chunk-segments', type=int, default=10)
    p.add_argument('--sync-seconds', type=float, default=1.0)
    p.add_argument('--stop-after-chunks', type=int, default=0)
    p.add_argument('--confirm-2b', action='store_true')
    a = p.parse_args()
    if not 3 <= a.max_edge <= 2_000_000_000:
        p.error('v0.18.0 is limited to 2B; 10B is NOT supported')
    if a.sync_seconds <= 0 or a.workers < 1:
        p.error('Invalid sync interval or worker count')
    local, drive = a.local_dir.resolve(), a.drive_dir.resolve()
    if local == drive or local in drive.parents or drive in local.parents:
        p.error('Local and Drive checkpoint directories must be separate')
    if not a.runner.is_file() or not a.reference.is_file():
        p.error('Runner or reference file missing (run from repository root)')
    # This import is only for the existing sealed checkpoint format validator.
    sys.path.insert(0, str(a.runner.resolve().parent))
    local.mkdir(parents=True, exist_ok=True)
    if not drive.is_dir():
        p.error('Drive directory does not exist: mount Google Drive and create it first')
    if not os.path.ismount('/content/drive') and str(drive).startswith('/content/drive/'):
        p.error('Google Drive is not mounted at /content/drive')
    print('RESTORE: checking durable Drive checkpoints', flush=True)
    restored = sync_files(drive, local)
    print(f'RESTORE: {restored} file(s) copied to VM', flush=True)
    known = set()
    mirrored = sync_files(local, drive, known)
    print(f'MIRROR: {mirrored} local-only file(s) copied to Drive', flush=True)
    cmd = [sys.executable, '-u', str(a.runner.resolve()),
           '--max-edge', str(a.max_edge), '--workers', str(a.workers),
           '--checkpoint-dir', str(local), '--reference', str(a.reference.resolve()),
           '--src-dir', str(a.src_dir.resolve()),
           '--segment-odds', str(a.segment_odds), '--chunk-segments', str(a.chunk_segments)]
    if a.confirm_2b:
        cmd.append('--confirm-2b')
    if a.stop_after_chunks:
        cmd += ['--stop-after-chunks', str(a.stop_after_chunks)]
    print('RUN:', ' '.join(cmd), flush=True)
    proc = subprocess.Popen(cmd)
    total = 0
    try:
        while proc.poll() is None:
            total += sync_files(local, drive, known)
            time.sleep(a.sync_seconds)
    except (KeyboardInterrupt, Exception):
        # Stop new work; the last fully published Drive checkpoints remain valid.
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        total += sync_files(local, drive, known)
        raise
    total += sync_files(local, drive, known)
    print(f'MIRROR: published {total} new durable file(s)', flush=True)
    if proc.returncode:
        print(f'FAIL: search exit code {proc.returncode}', flush=True)
        return proc.returncode
    if a.stop_after_chunks:
        print('INTENTIONAL STOP: rerun without --stop-after-chunks', flush=True)
        return 0
    result = local / 'result.json'
    if not result.is_file():
        raise RuntimeError('Search returned success without final result.json')
    summary = checked(result)
    if not summary.get('exact_set_match'):
        raise RuntimeError('Final result is not EXACT SET MATCH')
    if digest(result) != digest(drive / 'result.json'):
        raise RuntimeError('Final result not durably mirrored')
    print(f'PASS DURABLE MIRROR bricks={summary["bricks"]} chunks={summary["chunks"]}', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
