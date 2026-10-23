"""Experimental exact 10B pair-square arithmetic; not a complete search kernel.

All inputs must be nonnegative and <= 10_000_000_000.
A two-word unsigned representation avoids int64 overflow.
"""
import math
import numpy as np
from numba import njit

LIMIT = 10_000_000_000
MASK32 = np.uint64(0xFFFFFFFF)


@njit(cache=True)
def square_u128(x):
    """Return (high64, low64) of x*x, with x <= 10B."""
    a = np.uint64(x)
    lo = a & MASK32
    hi = a >> np.uint64(32)
    p0 = lo * lo
    p1 = lo * hi
    p2 = hi * hi
    middle = (p0 >> np.uint64(32)) + (p1 & MASK32) * np.uint64(2)
    low = (p0 & MASK32) | ((middle & MASK32) << np.uint64(32))
    high = p2 + (p1 >> np.uint64(32)) * np.uint64(2) + (middle >> np.uint64(32))
    return high, low


@njit(cache=True)
def sum_two_squares_u128(a, b):
    ah, al = square_u128(a)
    bh, bl = square_u128(b)
    low = al + bl
    carry = np.uint64(1) if low < al else np.uint64(0)
    return ah + bh + carry, low


@njit(cache=True)
def is_square_sum_10b(a, b):
    """Exact test for a*a + b*b being a square, without overflowing int64."""
    high, low = sum_two_squares_u128(a, b)
    # Float is used only as a seed; all decisions use exact 128-bit words.
    estimate = int(math.sqrt(float(a) * float(a) + float(b) * float(b)))
    for candidate in (estimate - 1, estimate, estimate + 1):
        if candidate < 0:
            continue
        ch, cl = square_u128(candidate)
        if ch == high and cl == low:
            return True
    return False


def checked_square_sum(a, b):
    if not (isinstance(a, int) and isinstance(b, int) and 0 <= a <= LIMIT and 0 <= b <= LIMIT):
        raise ValueError('a and b must be integers in 0..10B')
    return bool(is_square_sum_10b(np.uint64(a), np.uint64(b)))
