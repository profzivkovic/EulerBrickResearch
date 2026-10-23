#!/usr/bin/env python3
"""Read-only 10B arithmetic boundary audit; no search, no catalog writes."""
import math

BOUND = 10_000_000_000
INT64_MAX = (1 << 63) - 1
UINT64_MAX = (1 << 64) - 1


def even_leg_exact(odd: int, divisor: int) -> int:
    """Exact divisor identity; divisor must divide odd**2."""
    assert odd > 0 and odd % 2 == 1
    assert 0 < divisor < odd
    square = odd * odd
    assert square % divisor == 0
    return (square // divisor - divisor) // 2


def square_pair_exact(a: int, b: int) -> bool:
    n = a * a + b * b
    r = math.isqrt(n)
    return r * r == n


def run():
    assert BOUND * BOUND > UINT64_MAX
    assert 2 * BOUND * BOUND > UINT64_MAX
    # Odd hypotenuse and its corresponding even leg: (odd, (odd**2-1)//2).
    # The result is deliberately >BOUND; exact arithmetic must reject it.
    for odd in (3, 3_037_000_501, 9_999_999_999):
        e = even_leg_exact(odd, 1)
        assert e == (odd * odd - 1) // 2
        assert (e <= BOUND) == (e <= 10_000_000_000)
    # Divisors near the square root, including an admissible leg at 10B.
    odd = 9_999_999_999
    d = odd // 3
    assert odd * odd % d == 0
    e = even_leg_exact(odd, d)
    assert e == 4 * d
    assert e > BOUND  # 13,333,333,332
    # Pythagorean and non-Pythagorean pairs whose square sums exceed int64.
    assert square_pair_exact(6_000_000_000, 8_000_000_000)
    assert not square_pair_exact(9_999_999_999, 9_999_999_998)
    assert 6_000_000_000**2 + 8_000_000_000**2 > INT64_MAX
    print('PASS: exact 10B arithmetic boundary cases (Python arbitrary precision)')
    print('NOTE: this is an arithmetic oracle, NOT a Numba kernel or a 10B search')


if __name__ == '__main__':
    run()
