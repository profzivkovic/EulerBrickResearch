"""Exact, Numba-compatible arithmetic for nonnegative edges <= 10**12.

128-bit unsigned values are represented by (high uint64, low uint64).
No floating-point value determines the final square-test result.
"""
import math
import numpy as np
from numba import njit

MAX_EDGE = 1_000_000_000_000
FAST_EDGE = 2_147_483_647  # 2*x*x <= int64 max for x <= this value
MASK32 = np.uint64(0xFFFFFFFF)


@njit(cache=True)
def square_u128(x):
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
def is_square_sum(a, b):
    """Exact for 0 <= a,b <= 10**12; uses fast int64 when safe."""
    if a <= FAST_EDGE and b <= FAST_EDGE:
        n = a*a + b*b
        r = np.int64(math.sqrt(n))
        while (r + 1) <= n // (r + 1):
            r += 1
        while r > 0 and r > n // r:
            r -= 1
        return r*r == n

    ah, al = square_u128(a)
    bh, bl = square_u128(b)
    low = al + bl
    carry = np.uint64(1) if low < al else np.uint64(0)
    high = ah + bh + carry
    # sqrt(float) is only a starting approximation, corrected by exact comparisons.
    r = np.int64(math.sqrt(float(a)*float(a) + float(b)*float(b)))
    while True:
        rh, rl = square_u128(r)
        if rh < high or (rh == high and rl <= low):
            break
        r -= 1
    while True:
        sh, sl = square_u128(r + 1)
        if sh > high or (sh == high and sl > low):
            break
        r += 1
    rh, rl = square_u128(r)
    return rh == high and rl == low


def checked_square_sum(a, b):
    if not (isinstance(a, int) and isinstance(b, int) and 0 <= a <= MAX_EDGE and 0 <= b <= MAX_EDGE):
        raise ValueError('Both edges must be Python integers in 0..1_000_000_000_000')
    return bool(is_square_sum(np.int64(a), np.int64(b)))
