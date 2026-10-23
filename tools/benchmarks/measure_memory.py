#!/usr/bin/env python3
"""v0.15.3: measure memory of the actual search subprocess and its descendants.

Usage: python tools/measure_memory_0153.py -- python -u src/odd_leg_numba_segmented.py ...
"""
import argparse
import subprocess
import sys
import time

try:
    import psutil
except ImportError:
    raise SystemExit('Install psutil: python -m pip install psutil')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interval', type=float, default=0.05, help='sampling interval in seconds')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command and command[0] == '--':
        command = command[1:]
    if not command:
        parser.error('Supply command after --')
    if args.interval <= 0:
        parser.error('--interval must be positive')

    started = time.perf_counter()
    proc = subprocess.Popen(command)
    root = psutil.Process(proc.pid)
    sampled_peak = 0
    os_peak = 0
    first_rss = None
    samples = 0
    seen = {proc.pid}
    try:
        while True:
            try:
                children = root.children(recursive=True)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                children = []
            processes = [root, *children]
            total_rss = 0
            total_os_peak = 0
            active = 0
            for p in processes:
                try:
                    with p.oneshot():
                        mem = p.memory_info()
                    total_rss += mem.rss
                    total_os_peak += getattr(mem, 'peak_wset', mem.rss)
                    seen.add(p.pid)
                    active += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            if active:
                if first_rss is None:
                    first_rss = total_rss
                sampled_peak = max(sampled_peak, total_rss)
                os_peak = max(os_peak, total_os_peak)
                samples += 1
            if proc.poll() is not None:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        raise SystemExit(130)
    returncode = proc.wait()
    mib = 1024 * 1024
    print('\nMEMORY BENCHMARK v0.15.3', flush=True)
    print(f'Search PID: {proc.pid}; observed PIDs: {sorted(seen)}')
    print(f'Initial sampled RSS: {(first_rss or 0)/mib:.2f} MiB')
    print(f'Peak sampled RSS (process tree): {sampled_peak/mib:.2f} MiB')
    print(f'Peak OS working set (observed process tree): {os_peak/mib:.2f} MiB')
    print(f'Samples: {samples}; interval: {args.interval:.3f}s')
    print(f'Wall time: {time.perf_counter()-started:.3f}s')
    print(f'Exit code: {returncode}')
    if sys.platform == 'win32':
        print('OS peak uses Windows peak_wset; process-tree sum of peaks is not necessarily simultaneous.')
    else:
        print('OS peak is an RSS fallback on this platform.')
    return returncode


if __name__ == '__main__':
    sys.exit(main())
