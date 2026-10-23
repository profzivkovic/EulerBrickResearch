#!/usr/bin/env python3
"""Compare a local primitive Euler-brick catalog with Giovanni Resta's OEIS table.

Read-only. Fetches OEIS over HTTPS unless --resta-file is provided.
Does not modify the canonical catalog or manifest.
"""
import argparse
import csv
import hashlib
import math
from pathlib import Path
from urllib.request import Request, urlopen

URL = 'https://oeis.org/A031173/a031173.txt'


def local_catalog(path):
    result = set()
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not {'a', 'b', 'c'}.issubset(reader.fieldnames):
            raise ValueError('Local CSV must have columns a,b,c')
        for line, row in enumerate(reader, 2):
            triple = tuple(int(row[k]) for k in ('a', 'b', 'c'))
            if not (0 < triple[0] < triple[1] < triple[2]):
                raise ValueError(f'Invalid edge ordering on CSV line {line}')
            if triple in result:
                raise ValueError(f'Duplicate local triple on CSV line {line}')
            result.add(triple)
    return result


def resta_catalog(text):
    result = set()
    indices = []
    for line, raw in enumerate(text.splitlines(), 1):
        raw = raw.strip()
        if not raw or raw.startswith('#'):
            continue
        parts = raw.split()
        if len(parts) != 4:
            raise ValueError(f'Unexpected OEIS row on line {line}: {raw!r}')
        index, c, b, a = map(int, parts)
        if not (0 < a < b < c):
            raise ValueError(f'Invalid OEIS edge ordering on line {line}')
        triple = (a, b, c)
        if triple in result:
            raise ValueError(f'Duplicate OEIS triple on line {line}')
        result.add(triple)
        indices.append(index)
    if indices != list(range(1, len(indices) + 1)):
        raise ValueError('OEIS row indices are not sequential from 1')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, default=Path('data/verified_euler_bricks.csv'))
    p.add_argument('--resta-file', type=Path, help='Optional previously downloaded OEIS text file')
    p.add_argument('--max-edge', type=int, default=500_000_000)
    args = p.parse_args()
    if args.max_edge <= 0:
        p.error('--max-edge must be positive')
    local = local_catalog(args.input)
    if args.resta_file:
        data = args.resta_file.read_bytes()
        origin = str(args.resta_file)
    else:
        req = Request(URL, headers={'User-Agent': 'EulerBrickResearch/0.11 (research comparison)'})
        with urlopen(req, timeout=30) as response:
            data = response.read()
        origin = URL
    external = resta_catalog(data.decode('utf-8-sig'))
    # OEIS table uses strict c < 500M; compare only the common strict bound.
    # At any other requested bound, the same strict comparison is applied.
    local_bounded = {t for t in local if t[2] < args.max_edge}
    external_bounded = {t for t in external if t[2] < args.max_edge}
    missing = external_bounded - local_bounded
    extra = local_bounded - external_bounded
    print(f'LOCAL: {args.input}; total={len(local)}; below_bound={len(local_bounded)}')
    print(f'OEIS: {origin}; total={len(external)}; below_bound={len(external_bounded)}')
    print(f'OEIS_SHA256: {hashlib.sha256(data).hexdigest()}')
    print(f'BOUND: largest edge < {args.max_edge:,} (strict)')
    print(f'MISSING_FROM_LOCAL: {len(missing)}')
    print(f'EXTRA_IN_LOCAL: {len(extra)}')
    for title, triples in [('MISSING', missing), ('EXTRA', extra)]:
        for triple in sorted(triples, key=lambda t: (t[2], t[0], t[1]))[:10]:
            print(f'{title}: {triple}')
    if missing or extra:
        print('SET MISMATCH')
        raise SystemExit(1)
    if not local_bounded or not external_bounded:
        print('EMPTY COMPARISON - NOT ACCEPTED')
        raise SystemExit(1)
    print('EXACT SET MATCH')
    if args.max_edge == 500_000_000 and len(external) != 3556:
        print('WARNING: OEIS table row count differs from the expected historical 3556')
        raise SystemExit(1)


if __name__ == '__main__':
    main()
