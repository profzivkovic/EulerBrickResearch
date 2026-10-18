
#!/usr/bin/env python3
"""
EulerBrickResearch - Odd-Leg Factorization Search v0.9.0 (experimental)

Complete bounded enumeration of primitive Euler bricks by factoring
the square of their unique odd edge.

For odd o and an integer face diagonal h:

    h^2 = o^2 + e^2
    (h-e)(h+e) = o^2

Every positive factor pair u*v=o^2, u<v, yields:
    e = (v-u)//2
    h = (v+u)//2

The algorithm generates all eligible even legs e, checks all pairs,
and verifies every accepted brick using exact integer arithmetic.

Python 3.11+. Standard library only.
"""

import argparse
import csv
import math
import time
from array import array
from pathlib import Path


VERSION = "0.9.0"


def is_square(n: int) -> bool:
    if n < 0:
        return False
    r = math.isqrt(n)
    return r * r == n


def smallest_prime_factors(limit: int) -> array:
    """Build a smallest-prime-factor sieve for 0..limit."""
    spf = array("I", range(limit + 1))

    if limit >= 1:
        spf[1] = 1

    for p in range(2, math.isqrt(limit) + 1):
        if spf[p] != p:
            continue
        for multiple in range(p * p, limit + 1, p):
            if spf[multiple] == multiple:
                spf[multiple] = p

    return spf


def factorize(n: int, spf: array) -> list[tuple[int, int]]:
    """Return [(prime, exponent), ...] for positive n."""
    factors = []

    while n > 1:
        p = spf[n]
        exponent = 0

        while n % p == 0:
            n //= p
            exponent += 1

        factors.append((p, exponent))

    return factors


def square_divisors_below_root(
    odd: int,
    factors: list[tuple[int, int]],
) -> list[int]:
    """
    Generate all positive divisors u of odd^2 with u < odd.

    Each u gives the complementary divisor v=odd^2//u.
    """
    divisors = [1]

    for prime, exponent in factors:
        powers = [1]
        power = 1

        for _ in range(2 * exponent):
            power *= prime
            powers.append(power)

        divisors = [
            d * power
            for d in divisors
            for power in powers
        ]

    return [d for d in divisors if d < odd]


def even_legs(
    odd: int,
    bound: int,
    factors: list[tuple[int, int]],
) -> list[int]:
    """Generate all even legs e <= bound compatible with odd."""
    odd_squared = odd * odd
    legs = []

    for u in square_divisors_below_root(odd, factors):
        v = odd_squared // u
        e = (v - u) // 2

        if 0 < e <= bound:
            legs.append(e)

    return sorted(set(legs))


def verify_brick(
    edges: tuple[int, int, int],
    bound: int,
) -> bool:
    """Exact independent verification of a primitive Euler brick."""
    a, b, c = edges

    if not (0 < a < b < c <= bound):
        return False

    if math.gcd(math.gcd(a, b), c) != 1:
        return False

    return (
        is_square(a * a + b * b)
        and is_square(a * a + c * c)
        and is_square(b * b + c * c)
    )


def search(
    bound: int,
    progress_every: int,
) -> tuple[set[tuple[int, int, int]], int]:
    """Enumerate primitive Euler bricks up to maximum edge bound."""
    print(f"Building SPF sieve up to {bound:,}...", flush=True)
    spf = smallest_prime_factors(bound)

    bricks = set()
    candidates_checked = 0
    start = time.perf_counter()

    for odd in range(1, bound + 1, 2):
        factors = factorize(odd, spf)
        legs = even_legs(odd, bound, factors)

        if len(legs) >= 2:
            for i, e1 in enumerate(legs):
                for e2 in legs[i + 1:]:
                    candidates_checked += 1

                    if math.gcd(math.gcd(odd, e1), e2) != 1:
                        continue

                    if not is_square(e1 * e1 + e2 * e2):
                        continue

                    triple = tuple(sorted((odd, e1, e2)))

                    if verify_brick(triple, bound):
                        bricks.add(triple)

        if progress_every and odd % progress_every in (1, 2):
            elapsed = time.perf_counter() - start
            print(
                f"Progress: odd={odd:,}/{bound:,}; "
                f"bricks={len(bricks)}; "
                f"candidates={candidates_checked:,}; "
                f"elapsed={elapsed:.2f}s",
                flush=True,
            )

    return bricks, candidates_checked


def load_reference(
    path: Path,
    bound: int,
) -> set[tuple[int, int, int]]:
    """Read reference CSV and retain only bricks within the bound."""
    reference = set()

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        if not {"a", "b", "c"}.issubset(reader.fieldnames or []):
            raise ValueError("Reference CSV must contain a,b,c columns")

        for row in reader:
            triple = tuple(int(row[key]) for key in ("a", "b", "c"))

            if triple[2] <= bound:
                reference.add(triple)

    return reference


def write_output(
    path: Path,
    bricks: set[tuple[int, int, int]],
) -> None:
    """Write canonical, sorted Euler-brick CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(("a", "b", "c"))

        for triple in sorted(bricks, key=lambda t: (t[2], t[0], t[1])):
            writer.writerow(triple)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--max-edge",
        type=int,
        required=True,
        help="Maximum permitted edge",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output CSV path",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        help="Optional verified catalog for exact set comparison",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=100000,
        help="Report progress after approximately this many odd edges",
    )

    args = parser.parse_args()

    if args.max_edge < 1:
        parser.error("--max-edge must be positive")

    if args.progress_every < 0:
        parser.error("--progress-every must be nonnegative")

    print(
        f"EULER BRICK RESEARCH - ODD-LEG SEARCH v{VERSION}",
        flush=True,
    )
    print(f"Maximum edge: {args.max_edge:,}", flush=True)

    start = time.perf_counter()

    bricks, candidates_checked = search(
        args.max_edge,
        args.progress_every,
    )

    perfect = sum(
        is_square(a * a + b * b + c * c)
        for a, b, c in bricks
    )

    print()
    print(f"Primitive Euler bricks: {len(bricks)}")
    print(f"Perfect cuboids: {perfect}")
    print(f"Candidate pairs tested: {candidates_checked:,}")
    print(f"Elapsed: {time.perf_counter() - start:.3f}s")

    if args.reference:
        reference = load_reference(args.reference, args.max_edge)
        missing = reference - bricks
        extra = bricks - reference

        print(
            f"REFERENCE: expected={len(reference)}; "
            f"missing={len(missing)}; extra={len(extra)}"
        )

        if missing or extra:
            print(f"Missing examples: {sorted(missing)[:10]}")
            print(f"Extra examples: {sorted(extra)[:10]}")
            print("REFERENCE MISMATCH")
            return 1

        print("EXACT SET MATCH")

    write_output(args.output, bricks)
    print(f"Output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
