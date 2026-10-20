#!/usr/bin/env python3
"""EulerBrickResearch v0.17.0 phase 2: Numba type and counter audit.

Read-only; no full search, no edits to src/, no bound change.
Run from repository root:
    python tools/audit_int64_v0170_phase2.py
    python tools/audit_int64_v0170_phase2.py --report tools/audit_int64_v0170_types.txt
The optional report contains verbose Numba typed IR for manual review.
"""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import math
import sys
from pathlib import Path

import numpy as np
from numba import types

INT64_MAX = (1 << 63) - 1
BOUND_LIMIT = 2_000_000_000


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Cannot import {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument('--max-edge', type=int, default=BOUND_LIMIT)
    ap.add_argument('--report', type=Path, help='Optional path for complete Numba typed IR')
    args = ap.parse_args()
    if not 3 <= args.max_edge <= BOUND_LIMIT:
        ap.error('max-edge must be between 3 and 2,000,000,000')
    root = args.repo_root.resolve()
    src = root / 'src'
    sys.path.insert(0, str(src))
    kernel = load_module(src / 'odd_leg_numba_segmented.py', 'segmented_phase2')
    helper = load_module(src / 'segmented_factorization.py', 'helper_phase2')
    bound = args.max_edge

    print('NUMERICAL AUDIT v0.17.0 / PHASE 2 (read-only)')
    print(f'Bound={bound:,}; active MAX_SAFE_BOUND={kernel.MAX_SAFE_BOUND:,}')
    if kernel.MAX_SAFE_BOUND != 1_000_000_000:
        raise AssertionError('Expected unchanged stable bound of 1B')

    # Mathematical bounds. All generated even legs satisfy 0 < e <= bound.
    odd_sq = bound * bound
    pair_sq = 2 * bound * bound
    triple_sq = 3 * bound * bound
    print(f'odd**2 <= {odd_sq:,}: {"PASS" if odd_sq <= INT64_MAX else "FAIL"}')
    print(f'e1**2 + e2**2 <= {pair_sq:,}: {"PASS" if pair_sq <= INT64_MAX else "FAIL"}')
    assert pair_sq <= INT64_MAX
    print(f'a**2+b**2+c**2 <= {triple_sq:,}: Python big-int ONLY')
    if triple_sq > INT64_MAX:
        print('WARNING: three-square sum exceeds signed int64; keep it outside Numba int64')

    # Per-call counters: at most floor(B/2) distinct positive even legs.
    # Each unordered pair is visited at most once in the current partition loops.
    max_legs = bound // 2
    max_pairs = max_legs * (max_legs - 1) // 2
    print(f'Conservative max even legs per odd: {max_legs:,}')
    print(f'Conservative max pairs per fused call: {max_pairs:,}')
    assert max_pairs <= INT64_MAX
    print('Per-call tested/rejected counters: mathematical int64 bound PASS')
    print('Totals are accumulated as Python integers in main(); no int64 bound needed there.')
    print('Assumption: leg generator emits no duplicates; verify this separately if modified.')

    # Divisor expansion: value < odd before multiplication and prime <= odd.
    # Therefore value*prime < odd**2 <= bound**2, including the last loop update.
    print(f'Divisor update value*prime < odd**2 <= {odd_sq:,}: mathematical bound PASS')
    print(f'Base-prime square <= bound ({math.isqrt(bound):,}**2 <= bound): PASS')

    primes = np.asarray(helper.primes_upto(math.isqrt(bound)), dtype=np.int64)
    spf = np.asarray(helper.odd_spf_segment(9, 9, primes), dtype=np.uint32)
    b = np.int64(bound)
    kernel.integer_sqrt64(np.int64(pair_sq))
    legs = kernel.compatible_even_legs_jit(np.int64(9), b, spf, np.int64(9), primes)
    pairs, tested, rejected = kernel.fused_odd_kernel(np.int64(9), b, spf, np.int64(9), primes)
    assert len(legs) == len(set(map(int, legs)))
    assert 0 <= int(tested) <= max_pairs and 0 <= int(rejected) <= max_pairs
    print(f'Numba smoke: odd=9, legs={len(legs)}, tested={tested}, rejected={rejected} PASS')

    # inspect_types reports Numba typed intermediate IR; the signatures alone
    # do not prove that every arithmetic expression is int64.
    ir_parts = []
    for name in ('integer_sqrt64', 'compatible_even_legs_jit', 'fused_odd_kernel'):
        obj = getattr(kernel, name)
        if not obj.nopython_signatures:
            raise AssertionError(f'{name} did not compile in nopython mode')
        for signature in obj.nopython_signatures:
            if signature.return_type is None:
                raise AssertionError(f'{name}: missing return type')
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            obj.inspect_types(file=stream)
        typed_ir = stream.getvalue()
        if not typed_ir.strip():
            raise AssertionError(f'No typed IR available for {name}')
        ir_parts.append(f'===== {name} =====\n{typed_ir}')
        print(f'{name}: nopython PASS; {len(typed_ir):,} chars of typed IR captured')
        for sig in obj.nopython_signatures:
            print(f'  {sig}')

    if args.report:
        destination = args.report
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text('\n\n'.join(ir_parts), encoding='utf-8')
        print(f'Typed IR report: {destination}')

    print('PASS: analytical pair bounds, nopython compilation, typed IR captured')
    print('OPEN: manually review typed IR for each arithmetic intermediate;')
    print('      verify distinct-leg invariant and any future changes to loop structure.')
    print('Do NOT increase MAX_SAFE_BOUND based on this test alone.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
