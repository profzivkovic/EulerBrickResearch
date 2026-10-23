#!/usr/bin/env python3
"""Independent, exact validation of Euler-brick CSV output. Python 3.11+."""
import argparse
import csv
from fractions import Fraction
from math import gcd, isqrt
from pathlib import Path
import sys

REQUIRED = {'a', 'b', 'c'}
INTEGER_METADATA = {'x', 'y', 'z', 'space_squared', 'space_floor', 'square_gap', 'perfect'}


def validate(path: Path, bound: int, max_errors: int = 12):
    bricks = set()
    problems = []
    rows = perfect = 0

    def error(line, message):
        if len(problems) < max_errors:
            problems.append(f'line {line}: {message}')

    with path.open('r', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        if not REQUIRED <= fields:
            raise ValueError(f'{path}: missing columns: {sorted(REQUIRED-fields)}')
        for line, row in enumerate(reader, start=2):
            rows += 1
            try:
                a, b, c = (int(row[k]) for k in ('a', 'b', 'c'))
                if not (0 < a < b < c <= bound):
                    raise ValueError(f'edge order/bound invalid: {(a,b,c)}')
                triple = (a, b, c)
                if triple in bricks:
                    raise ValueError(f'duplicate brick: {triple}')
                bricks.add(triple)
                if gcd(gcd(a,b),c) != 1:
                    raise ValueError(f'nonprimitive brick: {triple}')
                squares = (a*a+b*b, a*a+c*c, b*b+c*c)
                diag = tuple(isqrt(v) for v in squares)
                if any(d*d != v for d,v in zip(diag,squares)):
                    raise ValueError(f'nonintegral face diagonal: {triple}')
                s = a*a+b*b+c*c
                r = isqrt(s)
                k = r if s-r*r <= (r+1)*(r+1)-s else r+1
                gap = abs(s-k*k)
                norm = Fraction(gap, r+k)
                is_perfect = int(r*r == s)
                perfect += is_perfect
                expected = dict(zip(('x','y','z'),diag))
                expected.update(space_squared=s, space_floor=r, square_gap=gap, perfect=is_perfect)
                for field, value in expected.items():
                    if field in fields and int(row[field]) != value:
                        raise ValueError(f'{field} mismatch for {triple}: CSV={row[field]}, exact={value}')
                if 'normalized_gap' in fields:
                    observed = float(row['normalized_gap'])
                    if abs(observed - float(norm)) > 5.1e-12:
                        raise ValueError(f'normalized_gap mismatch for {triple}: CSV={observed}, expected={float(norm)}')
            except (ValueError, TypeError, OverflowError, KeyError) as exc:
                error(line, str(exc))
    return bricks, rows, perfect, problems


def main():
    p = argparse.ArgumentParser(description='Exact independent validator for Euler-brick CSV files')
    p.add_argument('--input', required=True, type=Path)
    p.add_argument('--max-edge', required=True, type=int)
    p.add_argument('--subset', type=Path, help='CSV with smaller-bound bricks, all of which must appear in --input')
    p.add_argument('--subset-max-edge', type=int, help='Required when --subset is used')
    args = p.parse_args()
    if args.max_edge < 1 or (args.subset and (args.subset_max_edge is None or args.subset_max_edge < 1)):
        p.error('bounds must be positive; --subset-max-edge is required with --subset')
    try:
        bricks, rows, perfect, errors = validate(args.input, args.max_edge)
        print(f'INPUT: {args.input}; rows={rows}; unique={len(bricks)}; perfect={perfect}')
        if args.subset:
            smaller, smaller_rows, smaller_perfect, smaller_errors = validate(args.subset, args.subset_max_edge)
            errors.extend(f'SUBSET {e}' for e in smaller_errors)
            missing = smaller-bricks
            print(f'SUBSET: {args.subset}; rows={smaller_rows}; unique={len(smaller)}; missing={len(missing)}')
            if missing:
                errors.append(f'subset missing {len(missing)} bricks; examples: {sorted(missing)[:10]}')
        if errors:
            print('VALIDATION FAILED:')
            for e in errors[:15]:
                print('  '+e)
            return 1
        print('VALIDATION PASSED')
        return 0
    except (OSError, ValueError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
