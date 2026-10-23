
#!/usr/bin/env python3
"""
EulerBrickResearch
Odd Edge Arithmetic Analysis v0.1

Analyze the verified catalog of primitive Euler bricks.

Read-only analysis:
- Exact validation of Euler bricks
- Prime factorization of the unique odd edge
- gcd(odd, even1), gcd(odd, even2)
- Prime factor overlap between edges
- Divisibility patterns
- Statistics relevant to future search algorithms

Python standard library only.
"""

import argparse
import csv
import math
from collections import Counter
from pathlib import Path


VERSION = "0.1"


def is_square(n):
    r = math.isqrt(n)
    return r * r == n


def factorize(n):
    """Return {prime: exponent} using exact trial division."""
    factors = {}

    while n % 2 == 0 and n > 1:
        factors[2] = factors.get(2, 0) + 1
        n //= 2

    p = 3

    while p * p <= n:
        if n % p == 0:
            exponent = 0

            while n % p == 0:
                n //= p
                exponent += 1

            factors[p] = exponent

        p += 2

    if n > 1:
        factors[n] = factors.get(n, 0) + 1

    return factors


def validate_brick(triple):
    a, b, c = triple

    if not (0 < a < b < c):
        return False

    if math.gcd(math.gcd(a, b), c) != 1:
        return False

    return (
        is_square(a*a + b*b)
        and is_square(a*a + c*c)
        and is_square(b*b + c*c)
    )


def load_catalog(path):
    bricks = []
    seen = set()

    with path.open(
        "r", newline="", encoding="utf-8-sig"
    ) as f:
        reader = csv.DictReader(f)

        if not {"a", "b", "c"}.issubset(
            reader.fieldnames or []
        ):
            raise ValueError(
                "CSV must contain columns a,b,c"
            )

        for row_number, row in enumerate(reader, start=2):
            triple = (
                int(row["a"]),
                int(row["b"]),
                int(row["c"]),
            )

            if not validate_brick(triple):
                raise ValueError(
                    f"Invalid brick at row {row_number}: "
                    f"{triple}"
                )

            if triple in seen:
                raise ValueError(
                    f"Duplicate brick at row {row_number}: "
                    f"{triple}"
                )

            seen.add(triple)
            bricks.append(triple)

    return bricks


def odd_and_even_edges(triple):
    odd = [x for x in triple if x % 2 == 1]
    even = sorted(x for x in triple if x % 2 == 0)

    if len(odd) != 1 or len(even) != 2:
        raise ValueError(
            f"Unexpected edge parity: {triple}"
        )

    return odd[0], even[0], even[1]


def percentage(count, total):
    return 100.0 * count / total if total else 0.0


def print_counter(title, counter, total, limit=20):
    print()
    print(title)
    print("-" * len(title))

    for value, count in counter.most_common(limit):
        print(
            f"{str(value):>18} : "
            f"{count:>6,} "
            f"({percentage(count, total):6.2f}%)"
        )


def analyze(bricks):
    total = len(bricks)

    odd_factor_count = Counter()
    odd_distinct_factor_count = Counter()
    odd_prime_occurrence = Counter()
    odd_prime_exponents = Counter()

    gcd_pattern = Counter()
    gcd_one_count = Counter()

    common_even_prime_occurrence = Counter()
    common_odd_even_prime_occurrence = Counter()

    even_v2_min = Counter()
    divisibility_3 = Counter()
    divisibility_5 = Counter()

    odd_equals_one = 0
    odd_coprime_to_both = 0
    odd_shares_with_both = 0

    examples_shared_both = []
    examples_odd_coprime_both = []

    for triple in bricks:
        odd, e1, e2 = odd_and_even_edges(triple)

        odd_factors = factorize(odd)
        e1_factors = factorize(e1)
        e2_factors = factorize(e2)

        odd_primes = set(odd_factors)
        e1_primes = set(e1_factors)
        e2_primes = set(e2_factors)

        g1 = math.gcd(odd, e1)
        g2 = math.gcd(odd, e2)

        if math.gcd(g1, g2) != 1:
            raise AssertionError(
                f"Primitive gcd identity failed: {triple}"
            )

        if odd == 1:
            odd_equals_one += 1

        odd_distinct_factor_count[len(odd_primes)] += 1
        odd_factor_count[
            sum(odd_factors.values())
        ] += 1

        for p, exponent in odd_factors.items():
            odd_prime_occurrence[p] += 1
            odd_prime_exponents[(p, exponent)] += 1

        gcd_pattern[(g1 == 1, g2 == 1)] += 1
        gcd_one_count[
            (g1 == 1) + (g2 == 1)
        ] += 1

        if g1 == 1 and g2 == 1:
            odd_coprime_to_both += 1

            if len(examples_odd_coprime_both) < 10:
                examples_odd_coprime_both.append(
                    (triple, odd, g1, g2)
                )

        if g1 > 1 and g2 > 1:
            odd_shares_with_both += 1

            if len(examples_shared_both) < 10:
                examples_shared_both.append(
                    (triple, odd, g1, g2)
                )

        for p in e1_primes & e2_primes:
            common_even_prime_occurrence[p] += 1

        for p in odd_primes & (e1_primes | e2_primes):
            common_odd_even_prime_occurrence[p] += 1

        def v2(n):
            exponent = 0
            while n % 2 == 0:
                n //= 2
                exponent += 1
            return exponent

        even_v2_min[min(v2(e1), v2(e2))] += 1

        divisibility_3[
            sum(x % 3 == 0 for x in triple)
        ] += 1

        divisibility_5[
            sum(x % 5 == 0 for x in triple)
        ] += 1

    print("=" * 68)
    print(
        f"EULER BRICK RESEARCH - ODD EDGE ANALYSIS v{VERSION}"
    )
    print("=" * 68)

    print(f"Validated primitive Euler bricks: {total:,}")
    print(f"Odd edge equal to 1: {odd_equals_one:,}")
    print(
        f"Odd edge coprime to both even edges: "
        f"{odd_coprime_to_both:,}"
    )
    print(
        f"Odd edge shares factors with both even edges: "
        f"{odd_shares_with_both:,}"
    )

    print_counter(
        "Number of distinct prime factors of odd edge",
        odd_distinct_factor_count,
        total,
    )

    print_counter(
        "Number of prime factors of odd edge (with multiplicity)",
        odd_factor_count,
        total,
    )

    print_counter(
        "Most frequent primes dividing odd edge",
        odd_prime_occurrence,
        total,
        limit=25,
    )

    print_counter(
        "Number of even edges coprime to odd edge",
        gcd_one_count,
        total,
    )

    print_counter(
        "GCD pattern (gcd(o,e1)==1, gcd(o,e2)==1)",
        gcd_pattern,
        total,
    )

    print_counter(
        "Primes shared by both even edges",
        common_even_prime_occurrence,
        total,
        limit=25,
    )

    print_counter(
        "Odd-edge primes also dividing an even edge",
        common_odd_even_prime_occurrence,
        total,
        limit=25,
    )

    print_counter(
        "Minimum 2-adic valuation of even edges",
        even_v2_min,
        total,
    )

    print_counter(
        "Number of edges divisible by 3",
        divisibility_3,
        total,
    )

    print_counter(
        "Number of edges divisible by 5",
        divisibility_5,
        total,
    )

    print()
    print("Examples: odd edge shares factors with both even edges")
    print("-" * 60)

    for triple, odd, g1, g2 in examples_shared_both:
        print(
            f"{triple} | odd={odd} | "
            f"gcd1={g1} | gcd2={g2}"
        )

    print()
    print("Examples: odd edge coprime to both even edges")
    print("-" * 60)

    for triple, odd, g1, g2 in examples_odd_coprime_both:
        print(
            f"{triple} | odd={odd} | "
            f"gcd1={g1} | gcd2={g2}"
        )

    print()
    print("MATHEMATICAL INTERPRETATION")
    print("-" * 60)
    print(
        "The catalog is a bounded empirical dataset."
    )
    print(
        "Observed frequencies are not universal theorems."
    )
    print(
        "For every primitive brick, "
        "gcd(gcd(o,e1),gcd(o,e2)) = 1."
    )
    print(
        "Any future pruning rule must be proved "
        "before use in a complete search."
    )


def main():
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path(
            "data/verified_euler_bricks.csv"
        ),
    )

    args = parser.parse_args()

    bricks = load_catalog(args.input)
    analyze(bricks)


if __name__ == "__main__":
    main()
