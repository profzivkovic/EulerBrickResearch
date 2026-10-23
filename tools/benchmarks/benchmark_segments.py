#!/usr/bin/env python3
"""v0.15.2: benchmark unchanged v0.15.1 with different segment sizes.

Requires: pip install psutil
Run from EulerBrickResearch repository root.
"""
import argparse
import csv
import re
import subprocess
import sys
import time
from pathlib import Path

try:
    import psutil
except ImportError:
    raise SystemExit('Missing psutil: python -m pip install psutil')


def extract(pattern, text, label):
    m = re.search(pattern, text)
    if not m:
        raise ValueError(f'Missing {label} in search output')
    return m.group(1)


def run_once(args, segment_odds, repeat):
    out = args.output_dir / f'segmented_0152_{args.max_edge}_s{segment_odds}_r{repeat}.csv'
    cmd = [sys.executable, '-u', str(args.script), '--source', str(args.source),
           '--max-edge', str(args.max_edge), '--segment-odds', str(segment_odds),
           '--reference', str(args.reference), '--output', str(out)]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True)
    child = psutil.Process(proc.pid)
    peak_rss = 0
    peak_os = 0
    start = time.perf_counter()
    while proc.poll() is None:
        try:
            mem = child.memory_info()
            peak_rss = max(peak_rss, mem.rss)
            peak_os = max(peak_os, getattr(mem, 'peak_wset', 0))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        time.sleep(0.025)
    output = proc.communicate()[0]
    elapsed = time.perf_counter() - start
    print(output, end='' if output.endswith('\n') else '\n', flush=True)
    if proc.returncode:
        raise RuntimeError(f'Search failed (exit {proc.returncode}), segment={segment_odds}, repeat={repeat}')
    if 'EXACT SET MATCH' not in output:
        raise RuntimeError(f'No exact-set confirmation, segment={segment_odds}, repeat={repeat}')
    return dict(bound=args.max_edge, segment_odds=segment_odds, repeat=repeat,
                bricks=int(extract(r'Primitive Euler bricks:\s*([\d,]+)', output, 'bricks').replace(',', '')),
                search_seconds=float(extract(r'Search time:\s*([\d.]+)s', output, 'search time')),
                construction_seconds=float(extract(r'Segment construction:\s*([\d.]+)s', output, 'construction time')),
                kernel_seconds=float(extract(r'Fused Numba kernel:\s*([\d.]+)s', output, 'kernel time')),
                wall_seconds=round(elapsed, 3),
                peak_rss_mib=round(peak_rss / 1048576, 2),
                peak_os_working_set_mib=round(peak_os / 1048576, 2) if peak_os else '',
                exact_set_match=True, output_csv=str(out))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--max-edge', type=int, default=10_000_000)
    p.add_argument('--sizes', type=int, nargs='+', default=[25_000, 100_000, 400_000])
    p.add_argument('--repeats', type=int, default=2)
    p.add_argument('--script', type=Path, default=Path('src/odd_leg_numba_segmented.py'))
    p.add_argument('--source', type=Path, default=Path('src/odd_leg_search.py'))
    p.add_argument('--reference', type=Path, default=Path('data/verified_euler_bricks.csv'))
    p.add_argument('--output-dir', type=Path, default=Path('benchmark_0152_outputs'))
    p.add_argument('--summary', type=Path, default=Path('benchmark_segments_0152.csv'))
    args = p.parse_args()
    if args.repeats < 1 or not args.sizes or any(x < 1 for x in args.sizes):
        p.error('repeats and segment sizes must be positive')
    for f in (args.script, args.source, args.reference):
        if not f.is_file():
            p.error(f'File not found: {f}')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    fields = ['bound', 'segment_odds', 'repeat', 'bricks', 'search_seconds',
              'construction_seconds', 'kernel_seconds', 'wall_seconds',
              'peak_rss_mib', 'peak_os_working_set_mib', 'exact_set_match', 'output_csv']
    # Rotate order to reduce the impact of fixed ordering.
    with args.summary.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for repeat in range(1, args.repeats + 1):
            shift = (repeat - 1) % len(args.sizes)
            order = args.sizes[shift:] + args.sizes[:shift]
            for size in order:
                print(f'\n=== repeat={repeat}/{args.repeats} segment_odds={size:,} ===', flush=True)
                result = run_once(args, size, repeat)
                writer.writerow(result)
                f.flush()
                print(f"RESULT search={result['search_seconds']:.3f}s "
                      f"rss_sampled_peak={result['peak_rss_mib']:.2f} MiB "
                      f"os_peak={result['peak_os_working_set_mib']} MiB", flush=True)
    print(f'\nALL RUNS EXACT SET MATCH; summary={args.summary}')
    print('Memory: sampled RSS is an estimate; OS peak working set is Windows-specific.')


if __name__ == '__main__':
    main()
