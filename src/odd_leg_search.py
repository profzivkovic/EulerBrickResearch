
#!/usr/bin/env python3
"""
EulerBrickResearch
Odd-Leg Search v0.9.5 - Modulo-3 Pair Partition

Experimental complete search for primitive Euler bricks.

Key optimization:
    Partition compatible even legs by divisibility by 3,
    and generate only pair combinations compatible with
    the proven modulo-3 structure of primitive Euler bricks.

The stable v0.9.0 implementation remains untouched.

Standard library only.
"""

import argparse
import csv
import math
import time
from array import array
from pathlib import Path


VERSION = "0.9.5"


def is_square(n: int) -> bool:
    root = math.isqrt(n)
    return root * root == n


def build_spf(limit: int) -> array:
    """Smallest-prime-factor sieve."""
    spf = array("I", range(limit + 1))

    for p in range(2, math.isqrt(limit) + 1):
        if spf[p] != p:
            continue

        for multiple in range(p * p, limit + 1, p):
            if spf[multiple] == multiple:
                spf[multiple] = p

    return spf


def factorize(
    n: int,
    spf: array,
) -> list[tuple[int, int]]:
    factors = []

    while n > 1:
        p = spf[n]
        exponent = 0

        while n % p == 0:
            n //= p
            exponent += 1

        factors.append((p, exponent))

    return factors


def divisors_below_root(
    root: int,
    factors: list[tuple[int, int]],
) -> list[int]:
    """
    Generate all divisors u of root**2 satisfying u < root.
    """
    divisors = [1]

    for prime, exponent in factors:
        powers = [1]
        power = 1

        for _ in range(2 * exponent):
            power *= prime
            powers.append(power)

        divisors = [
            d * p
            for d in divisors
            for p in powers
        ]

    return [d for d in divisors if d < root]


def compatible_even_legs(
    odd: int,
    bound: int,
    spf: array,
) -> list[int]:
    """
    Enumerate all positive even legs e <= bound
    for which odd**2 + e**2 is a perfect square.

    For odd odd:
        u*v = odd**2, u < odd < v
        e = (v-u)//2
    """
    factors = factorize(odd, spf)
    odd_squared = odd * odd

    legs = []

    for u in divisors_below_root(odd, factors):
        v = odd_squared // u
        e = (v - u) // 2

        if 0 < e <= bound:
            legs.append(e)

    return legs


def verify_brick(
    triple: tuple[int, int, int],
    bound: int,
) -> bool:
    a, b, c = triple

    return (
        0 < a < b < c <= bound
        and math.gcd(math.gcd(a, b), c) == 1
        and is_square(a*a + b*b)
        and is_square(a*a + c*c)
        and is_square(b*b + c*c)
    )


def search(
    bound: int,
    progress_every: int,
) -> tuple[set[tuple[int, int, int]], dict]:
    print(
        f"Building SPF sieve up to {bound:,}...",
        flush=True,
    )

    sieve_start = time.perf_counter()
    spf = build_spf(bound)
    sieve_seconds = time.perf_counter() - sieve_start

    bricks = set()

    stats = {
        "all_possible_pairs": 0,
        "partition_pairs": 0,
        "primitive_pairs": 0,
        "rejected_nonprimitive": 0,
        "isqrt_calls": 0,
        "sieve_seconds": sieve_seconds,
    }

    start = time.perf_counter()

    gcd = math.gcd
    isqrt = math.isqrt

    for odd in range(1, bound + 1, 2):
        legs = compatible_even_legs(odd, bound, spf)
        n = len(legs)

        if n < 2:
            continue

        stats["all_possible_pairs"] += n * (n - 1) // 2

        divisible = []
        nondivisible = []

        for e in legs:
            if e % 3 == 0:
                divisible.append(e)
            else:
                nondivisible.append(e)

        if odd % 3 == 0:
            # Exactly one even edge divisible by 3.
            #
            # Iterate the Cartesian product of the two groups.
            # No pair ordering is required: every pair occurs once.
            stats["partition_pairs"] += (
                len(divisible) * len(nondivisible)
            )

            for e1 in divisible:
                e1_squared = e1 * e1

                for e2 in nondivisible:
                    if gcd(gcd(odd, e1), e2) != 1:
                        stats["rejected_nonprimitive"] += 1
                        continue

                    stats["primitive_pairs"] += 1
                    stats["isqrt_calls"] += 1

                    n2 = e1_squared + e2 * e2
                    root = isqrt(n2)

                    if root * root != n2:
                        continue

                    triple = tuple(sorted((odd, e1, e2)))

                    if verify_brick(triple, bound):
                        bricks.add(triple)

        else:
            # Both even edges must be divisible by 3.
            m = len(divisible)
            stats["partition_pairs"] += m * (m - 1) // 2

            for i, e1 in enumerate(divisible):
                e1_squared = e1 * e1
                g1 = gcd(odd, e1)

                for e2 in divisible[i + 1:]:
                    if gcd(g1, e2) != 1:
                        stats["rejected_nonprimitive"] += 1
                        continue

                    stats["primitive_pairs"] += 1
                    stats["isqrt_calls"] += 1

                    n2 = e1_squared + e2 * e2
                    root = isqrt(n2)

                    if root * root != n2:
                        continue

                    triple = tuple(sorted((odd, e1, e2)))

                    if verify_brick(triple, bound):
                        bricks.add(triple)

        if (
            progress_every
            and (odd - 1) % progress_every == 0
        ):
            elapsed = time.perf_counter() - start

            print(
                f"Progress: odd={odd:,}/{bound:,}; "
                f"bricks={len(bricks)}; "
                f"partition_pairs="
                f"{stats['partition_pairs']:,}; "
                f"elapsed={elapsed:.2f}s",
                flush=True,
            )

    stats["search_seconds"] = (
        time.perf_counter() - start
    )

    return bricks, stats


def load_reference(
    path: Path,
    bound: int,
) -> set[tuple[int, int, int]]:
    reference = set()

    with path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        reader = csv.DictReader(f)

        if not {"a", "b", "c"}.issubset(
            reader.fieldnames or []
        ):
            raise ValueError(
                "Reference CSV must contain a,b,c columns"
            )

        for row in reader:
            triple = tuple(
                sorted(
                    int(row[k])
                    for k in ("a", "b", "c")
                )
            )

            if triple[2] <= bound:
                reference.add(triple)

    return reference


def write_output(
    path: Path,
    bricks: set[tuple[int, int, int]],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.writer(f)
        writer.writerow(("a", "b", "c"))

        for triple in sorted(
            bricks,
            key=lambda t: (t[2], t[0], t[1]),
        ):
            writer.writerow(triple)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        "--max-edge",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--reference",
        type=Path,
    )

    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--progress-every",
        type=int,
        default=100000,
    )

    args = parser.parse_args()

    if args.max_edge < 1:
        parser.error(
            "--max-edge must be positive"
        )

    if args.progress_every < 0:
        parser.error(
            "--progress-every must be nonnegative"
        )

    print(
        f"EULER BRICK RESEARCH - ODD-LEG v{VERSION}",
        flush=True,
    )
    print(f"Maximum edge: {args.max_edge:,}")
    print("Mode: modulo-3 pair partition")

    total_start = time.perf_counter()

    bricks, stats = search(
        args.max_edge,
        args.progress_every,
    )

    perfect = sum(
        is_square(a*a + b*b + c*c)
        for a, b, c in bricks
    )

    print()
    print(f"Primitive Euler bricks: {len(bricks)}")
    print(f"Perfect cuboids: {perfect}")

    print(
        f"All possible pairs: "
        f"{stats['all_possible_pairs']:,}"
    )
    print(
        f"Pairs after modulo-3 partition: "
        f"{stats['partition_pairs']:,}"
    )
    print(
        f"Primitive candidate pairs: "
        f"{stats['primitive_pairs']:,}"
    )
    print(
        f"Rejected nonprimitive: "
        f"{stats['rejected_nonprimitive']:,}"
    )
    print(
        f"isqrt calls: "
        f"{stats['isqrt_calls']:,}"
    )

    all_pairs = stats["all_possible_pairs"]
    partition_pairs = stats["partition_pairs"]

    reduction = (
        100.0 * (all_pairs - partition_pairs) / all_pairs
        if all_pairs
        else 0.0
    )

    print(
        f"Pair reduction: {reduction:.2f}%"
    )
    print(
        f"Sieve time: "
        f"{stats['sieve_seconds']:.3f}s"
    )
    print(
        f"Search time: "
        f"{stats['search_seconds']:.3f}s"
    )
    print(
        f"Elapsed: "
        f"{time.perf_counter() - total_start:.3f}s"
    )

    if args.reference:
        reference = load_reference(
            args.reference,
            args.max_edge,
        )

        missing = reference - bricks
        extra = bricks - reference

        print(
            f"REFERENCE: expected={len(reference)}; "
            f"missing={len(missing)}; "
            f"extra={len(extra)}"
        )

        if missing or extra:
            print(
                f"Missing examples: "
                f"{sorted(missing)[:10]}"
            )
            print(
                f"Extra examples: "
                f"{sorted(extra)[:10]}"
            )
            print("REFERENCE MISMATCH")
            return 1

        print("EXACT SET MATCH")

    write_output(args.output, bricks)
    print(f"Output: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
