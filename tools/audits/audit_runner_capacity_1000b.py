#!/usr/bin/env python3
"""Static, arithmetic capacity audit for v0.20.0 up to 10**12.

Does not run a search, modify checkpoints, or unlock the runner's 2B cap.
Uses a complete monotone-prime-exponent enumeration to bound tau(odd**2).
"""
import argparse
import ast
from pathlib import Path

MAX_EDGE = 10**12
INT64_MAX = 2**63 - 1
ODD_PRIMES = (3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53,
              59, 61, 67, 71, 73, 79, 83, 89, 97)


def max_divisors_of_odd_square(bound):
    """Exact maximum of tau(n**2), odd 1 <= n <= bound.

    For a maximum, exponents of ascending primes are nonincreasing:
    swapping e_i < e_j (p_i < p_j) reduces n without changing tau(n**2).
    Prime support is an initial prefix of odd primes for the same reason.
    """
    best_tau, best_n, best_exponents = 1, 1, ()

    def visit(index, prev_exp, n, tau, exponents):
        nonlocal best_tau, best_n, best_exponents
        if tau > best_tau or (tau == best_tau and n < best_n):
            best_tau, best_n, best_exponents = tau, n, exponents
        if index >= len(ODD_PRIMES):
            return
        p = ODD_PRIMES[index]
        v = n
        for e in range(1, prev_exp + 1):
            if v > bound // p:
                break
            v *= p
            visit(index + 1, e, v, tau * (2 * e + 1), exponents + (e,))

    visit(0, bound.bit_length(), 1, 1, ())
    return best_tau, best_n, best_exponents


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--max-edge', type=int, default=MAX_EDGE)
    ap.add_argument('--segment-odds', type=int, default=100_000)
    ap.add_argument('--chunk-segments', type=int, default=10)
    ap.add_argument('--runner', type=Path, default=Path('tools/runners/checkpoint_parallel_v0200.py'))
    args = ap.parse_args()
    if not 3 <= args.max_edge <= MAX_EDGE:
        ap.error('max-edge must be in 3..1_000_000_000_000')
    if args.segment_odds < 1 or args.chunk_segments < 1:
        ap.error('segment-odds and chunk-segments must be positive')

    tau, witness, exponents = max_divisors_of_odd_square(args.max_edge)
    # Every compatible even leg corresponds to a distinct divisor d < odd
    # of odd**2.  Therefore leg_count <= floor(tau(odd**2)/2).
    max_legs = tau // 2
    # Regardless of modulo-3 filtering, pair candidates <= C(max_legs,2).
    pairs_per_odd = max_legs * (max_legs - 1) // 2
    max_segment_pairs = pairs_per_odd * args.segment_odds
    # Each pair is either tested or rejected, so BOTH counters <= pair bound.
    print(f'Bound={args.max_edge:,} odd witness={witness:,} exponents={exponents}')
    print(f'Max tau(odd^2)={tau:,}; max compatible legs={max_legs:,}')
    print(f'Conservative max candidate pairs per odd={pairs_per_odd:,}')
    print(f'Conservative max per-segment counter={max_segment_pairs:,}')
    print(f'int64 maximum={INT64_MAX:,}')
    if max_segment_pairs > INT64_MAX:
        raise SystemExit('FAIL: possible int64 segment-counter overflow; reduce --segment-odds')
    print('PASS: segment tested/rejected int64 counters cannot overflow under these bounds')
    print('PASS: Python chunk/global integer aggregation has no fixed-width overflow')
    print(f'Chunk size={args.chunk_segments} segments; this does not multiply Numba segment counters')

    if args.runner.is_file():
        tree = ast.parse(args.runner.read_text(encoding='utf-8'))
        code = args.runner.read_text(encoding='utf-8')
        checks = {
            'Python aggregation': 'tested_total += int(tested)' in code and 'rejected_total += int(rejected)' in code,
            'sealed checkpoints': 'def read_sealed(' in code and 'def atomic_json(' in code,
            'source hash in config': "'sources':" in code and 'sha256(src / f)' in code,
            'checkpoint resume': 'completed[i] = payload' in code,
            'reference validation': 'stable.verify_brick' in code,
            'current 2B safety cap': '2_000_000_000' in code,
        }
        for label, passed in checks.items():
            print(f'{"PASS" if passed else "FAIL"}: runner static check: {label}')
        if not all(checks.values()):
            raise SystemExit('FAIL: runner static inspection')
    else:
        print(f'NOTE: runner not found at {args.runner}; static runner inspection skipped')
    print('NOT AUDITED: checkpoint disk capacity, actual runtime, Drive sync, or search above 2B')
    print('FULL SEARCH ABOVE 2B REMAINS BLOCKED')


if __name__ == '__main__':
    main()
