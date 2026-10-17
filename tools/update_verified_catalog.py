#!/usr/bin/env python3
"""Maintain a versioned catalog of arithmetically verified primitive Euler bricks."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from datetime import datetime, timezone

FIELDS = ('a', 'b', 'c')


def square(n):
    r = math.isqrt(n)
    return r * r == n


def read_bricks(path, bound):
    bricks = set()
    count = 0
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not set(FIELDS).issubset(reader.fieldnames):
            raise ValueError(f'{path}: CSV must contain columns a,b,c')
        for line, row in enumerate(reader, 2):
            try:
                a, b, c = (int(row[k]) for k in FIELDS)
            except (ValueError, TypeError, KeyError) as exc:
                raise ValueError(f'{path}:{line}: invalid integer edge') from exc
            t = (a, b, c)
            if not (0 < a < b < c <= bound):
                raise ValueError(f'{path}:{line}: invalid edge order or bound: {t}')
            if math.gcd(math.gcd(a, b), c) != 1:
                raise ValueError(f'{path}:{line}: nonprimitive brick: {t}')
            if not all(square(x*x+y*y) for x,y in ((a,b),(a,c),(b,c))):
                raise ValueError(f'{path}:{line}: invalid face diagonal: {t}')
            if t in bricks:
                raise ValueError(f'{path}:{line}: duplicate brick: {t}')
            bricks.add(t)
            count += 1
    return bricks


def canonical_bytes(bricks):
    rows = ['a,b,c\n']
    rows.extend(f'{a},{b},{c}\n' for a,b,c in sorted(bricks, key=lambda t: (t[2],t[0],t[1])))
    return ''.join(rows).encode('utf-8')


def stage_bytes(target, content):
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f'.{target.name}.', suffix='.tmp', dir=target.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise
    return Path(name)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True, type=Path)
    p.add_argument('--max-edge', required=True, type=int)
    p.add_argument('--catalog', type=Path, default=Path('data/verified_euler_bricks.csv'))
    p.add_argument('--manifest', type=Path, default=Path('data/verified_manifest.json'))
    args = p.parse_args()
    if args.max_edge < 1:
        p.error('--max-edge must be positive')
    if args.catalog.resolve() == args.input.resolve():
        p.error('--input and --catalog must differ')
    if args.manifest.resolve() in (args.input.resolve(), args.catalog.resolve()):
        p.error('--manifest must differ from input and catalog')
    incoming = read_bricks(args.input, args.max_edge)
    if args.catalog.exists() != args.manifest.exists():
        raise ValueError('Catalog and manifest must both exist or both be absent')
    old = set()
    old_bound = 0
    if args.catalog.exists():
        meta = json.loads(args.manifest.read_text(encoding='utf-8'))
        old_bound = int(meta['searched_max_edge'])
        if args.max_edge < old_bound:
            raise ValueError(f'New bound {args.max_edge} is smaller than catalog bound {old_bound}')
        old = read_bricks(args.catalog, old_bound)
        if len(old) != int(meta['brick_count']):
            raise ValueError('Catalog count does not match manifest')
        if hashlib.sha256(canonical_bytes(old)).hexdigest() != meta['sha256']:
            raise ValueError('Catalog checksum does not match manifest')
        missing = old - incoming
        if missing:
            raise ValueError(f'New search misses {len(missing)} catalog bricks; example: {min(missing)}')
    # A complete bounded search should include every previous brick, so the
    # incoming set must be a superset; do not silently hide omissions via union.
    combined = incoming | old
    data = canonical_bytes(combined)
    digest = hashlib.sha256(data).hexdigest()
    perfect = sum(square(a*a+b*b+c*c) for a,b,c in combined)
    meta = {
        'schema_version': 1,
        'searched_max_edge': args.max_edge,
        'brick_count': len(combined),
        'perfect_cuboid_count': perfect,
        'sha256': digest,
        'updated_utc': datetime.now(timezone.utc).isoformat(),
        'source_file': args.input.name,
        'verification': 'Exact arithmetic for every stored row; completeness of generator not independently proved',
    }
    catalog_temp = stage_bytes(args.catalog, data)
    manifest_temp = None
    try:
        manifest_temp = stage_bytes(args.manifest, (json.dumps(meta, indent=2, ensure_ascii=False)+'\n').encode('utf-8'))
        # Two-file replacement is not a single atomic transaction. On interruption,
        # a checksum mismatch is detected on the next invocation.
        os.replace(catalog_temp, args.catalog)
        os.replace(manifest_temp, args.manifest)
    finally:
        catalog_temp.unlink(missing_ok=True)
        if manifest_temp is not None:
            manifest_temp.unlink(missing_ok=True)
    print(f'CATALOG UPDATED: previous={len(old)}, added={len(combined)-len(old)}, total={len(combined)}')
    print(f'BOUND: {args.max_edge}; PERFECT CUBOIDS: {perfect}')
    print(f'SHA256: {digest}')
    print(f'CATALOG: {args.catalog}')
    print(f'MANIFEST: {args.manifest}')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit(f'ERROR: {exc}')
