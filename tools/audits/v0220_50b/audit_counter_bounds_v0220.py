"""Mathematical upper bound for v0.22.0 per-segment Numba counters, up to 50B.
Does not run a search or modify repository files.
"""
from __future__ import annotations
import argparse

PRIMES = (3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47)
I64_MAX = 2**63 - 1

def max_odd_square_divisors(bound):
    # For an odd n <= bound, the maximum tau(n^2) occurs among
    # exponent vectors e1 >= e2 >= ... >= 1 on consecutive odd primes.
    best = (1, 1, ())
    def visit(index, previous_exponent, value, count, exponents):
        nonlocal best
        if count > best[0]:
            best = (count, value, exponents)
        if index == len(PRIMES):
            return
        next_value = value
        for exponent in range(1, previous_exponent + 1):
            next_value *= PRIMES[index]
            if next_value > bound:
                break
            visit(index + 1, exponent, next_value,
                  count * (2 * exponent + 1), exponents + (exponent,))
    visit(0, bound.bit_length(), 1, 1, ())
    return best

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-edge", type=int, default=50_000_000_000)
    parser.add_argument("--segment-odds", type=int, default=100_000)
    parser.add_argument("--chunk-segments", type=int, default=10)
    a = parser.parse_args()
    if not (3 <= a.max_edge <= 50_000_000_000):
        parser.error("This proof is restricted to 3..50B")
    if not (1 <= a.segment_odds <= 100_000) or a.chunk_segments < 1:
        parser.error("segment-odds must be 1..100000 and chunk-segments positive")
    tau, witness, exponents = max_odd_square_divisors(a.max_edge)
    # For odd n, divisors of n^2 pair as d < n and d > n, plus d=n.
    # Each d<n yields at most one compatible even leg, so legs <= (tau-1)/2.
    max_legs = (tau - 1) // 2
    # The kernel checks at most all unordered pairs of these legs.
    pairs_per_odd = max_legs * (max_legs - 1) // 2
    per_segment = a.segment_odds * pairs_per_odd
    per_chunk = a.chunk_segments * per_segment
    print(f"max_edge={a.max_edge:,} segment_odds={a.segment_odds:,} chunk_segments={a.chunk_segments:,}")
    print(f"max tau(odd^2)={tau:,}; witness={witness:,}; exponents={exponents}")
    print(f"max legs/odd={max_legs:,}; max pairs/odd={pairs_per_odd:,}")
    print(f"upper bound tested+rejected per segment={per_segment:,}")
    print(f"upper bound tested+rejected per chunk={per_chunk:,}")
    assert per_segment <= I64_MAX, "FAIL: segment counter may overflow signed int64"
    assert per_chunk <= I64_MAX, "FAIL: chunk counter may overflow signed int64"
    assert 3*a.max_edge <= I64_MAX, "FAIL: divisor quotient cap may overflow signed int64"
    assert 2*a.max_edge*a.max_edge < 2**128, "FAIL: pair-square sum exceeds unsigned 128 bits"
    print("PASS conservative int64 counter bounds for this segment/chunk configuration")
    print("NOT full kernel arithmetic proof, completeness proof, or 50B runner approval")

if __name__ == "__main__":
    main()
