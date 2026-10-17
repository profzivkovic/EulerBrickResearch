
from dataclasses import dataclass
from collections import Counter
from math import gcd, isqrt, lcm
from time import perf_counter
import argparse
import csv
import heapq


# =====================================================
# MATHEMATICAL UTILITIES
# =====================================================

def primitive_triples(bound):
    """Generate primitive Pythagorean triples."""
    result = []
    m = 2

    while m*m + 1 <= bound:
        for n in range(1, m):
            h = m*m + n*n

            if h > bound:
                continue

            if gcd(m, n) != 1:
                continue

            if (m-n) % 2 == 0:
                continue

            a = m*m - n*n
            b = 2*m*n

            result.append(
                (min(a, b), max(a, b), h)
            )

        m += 1

    return result


SQUARE_RESIDUES_64 = frozenset(
    (i*i) % 64 for i in range(64)
)

SQUARE_RESIDUES_63 = frozenset(
    (i*i) % 63 for i in range(63)
)


def could_be_square(n):
    """Fast modular filter for perfect squares."""
    return (
        n % 64 in SQUARE_RESIDUES_64
        and n % 63 in SQUARE_RESIDUES_63
    )


def square_info(n):
    """Exact square test and nearest-square gap."""
    r = isqrt(n)

    gap = min(
        n-r*r,
        (r+1)*(r+1)-n
    )

    return r*r == n, gap


# =====================================================
# CANDIDATE
# =====================================================

@dataclass(frozen=True)
class Candidate:
    a: int
    b: int
    c: int
    x: int
    d: int

    y_valid: bool
    z_valid: bool

    gap_y: int
    gap_z: int

    @property
    def satisfied(self):
        return (
            2
            + int(self.y_valid)
            + int(self.z_valid)
        )

    @property
    def fitness(self):
        return self.gap_y + self.gap_z

    @property
    def perfect(self):
        return self.y_valid and self.z_valid


# =====================================================
# GENERATOR
# =====================================================

def generate_candidates(bound, max_edge, stats):

    triples = primitive_triples(bound)
    seen = set()

    for a1, b1, h1 in triples:
        for u, v, h2 in triples:

            for common, other in (
                (u, v),
                (v, u)
            ):

                stats["pairs"] += 1

                x = lcm(h1, common)

                s1 = x // h1
                s2 = x // common

                raw = (
                    a1*s1,
                    b1*s1,
                    other*s2
                )

                if max(raw) > max_edge:
                    continue

                g = gcd(
                    gcd(raw[0], raw[1]),
                    raw[2]
                )

                key = tuple(
                    sorted(e//g for e in raw)
                )

                if key in seen:
                    continue

                seen.add(key)

                a = a1*s1 // g
                b = b1*s1 // g
                c = other*s2 // g

                x_reduced = x // g
                d = h2*s2 // g

                assert (
                    a*a+b*b == x_reduced*x_reduced
                )

                assert (
                    a*a+b*b+c*c == d*d
                )

                y2 = a*a+c*c
                z2 = b*b+c*c

                if not could_be_square(y2):
                    stats["modular_rejects"] += 1

                if not could_be_square(z2):
                    stats["modular_rejects"] += 1

                # Exact verification is always used.
                vy, gy = square_info(y2)
                vz, gz = square_info(z2)

                stats["candidates"] += 1

                yield Candidate(
                    a, b, c,
                    x_reduced, d,
                    vy, vz,
                    gy, gz
                )


# =====================================================
# EXPERIMENT
# =====================================================

def run_experiment(bound, max_edge, top, output):

    start = perf_counter()

    stats = Counter()
    counts = Counter()

    heap = []
    strong_count = 0

    with open(
        output,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "a", "b", "c", "x", "d",
            "satisfied",
            "gap_y", "gap_z",
            "fitness"
        ])

        for candidate in generate_candidates(
            bound, max_edge, stats
        ):

            counts[candidate.satisfied] += 1

            rank = (
                candidate.satisfied,
                -candidate.fitness
            )

            entry = (
                rank,
                stats["candidates"],
                candidate
            )

            if len(heap) < top:
                heapq.heappush(heap, entry)

            elif rank > heap[0][0]:
                heapq.heapreplace(heap, entry)

            if candidate.satisfied >= 3:
                strong_count += 1

                writer.writerow([
                    candidate.a,
                    candidate.b,
                    candidate.c,
                    candidate.x,
                    candidate.d,
                    candidate.satisfied,
                    candidate.gap_y,
                    candidate.gap_z,
                    candidate.fitness
                ])

            if candidate.perfect:
                print("\n*** PERFECT CUBOID FOUND ***")
                print(candidate)

                # Independent exact verification
                a, b, c = (
                    candidate.a,
                    candidate.b,
                    candidate.c
                )

                assert (
                    isqrt(a*a+b*b)**2 == a*a+b*b
                )
                assert (
                    isqrt(a*a+c*c)**2 == a*a+c*c
                )
                assert (
                    isqrt(b*b+c*c)**2 == b*b+c*c
                )
                assert (
                    isqrt(a*a+b*b+c*c)**2
                    == a*a+b*b+c*c
                )

    elapsed = perf_counter()-start

    print("=" * 65)
    print("EULER BRICK RESEARCH - VERSION 0.3")
    print("=" * 65)

    print(f"Max hypotenuse: {bound}")
    print(f"Max edge: {max_edge}")
    print(f"Triple pair attempts: {stats['pairs']}")
    print(f"Unique candidates: {stats['candidates']}")
    print(
        "Modular square rejections:",
        stats["modular_rejects"]
    )

    print("\nSATISFIED EQUATIONS")

    for k in (2, 3, 4):
        print(f"{k}/4: {counts[k]}")

    print("\nPERFORMANCE")
    print(f"Total time: {elapsed:.3f} seconds")

    if elapsed > 0:
        speed = stats["candidates"]/elapsed
        print(f"Candidates/second: {speed:,.0f}")

    print("\nTOP CANDIDATES")

    for _, _, c in sorted(heap, reverse=True):
        print(
            f"({c.a}, {c.b}, {c.c}) "
            f"conditions={c.satisfied}/4 "
            f"gap={c.fitness} "
            f"y={c.y_valid} "
            f"z={c.z_valid}"
        )

    print(f"\nStrong candidates: {strong_count}")
    print(f"Saved to: {output}")

    if counts[4] == 0:
        print("\nNo perfect cuboid found.")


# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--hypotenuse",
        type=int,
        default=100
    )

    parser.add_argument(
        "--max-edge",
        type=int,
        default=100000
    )

    parser.add_argument(
        "--top",
        type=int,
        default=10
    )

    parser.add_argument(
        "--output",
        default="strong_candidates.csv"
    )

    args = parser.parse_args()

    if (
        args.hypotenuse < 5
        or args.max_edge < 1
        or args.top < 1
    ):
        parser.error(
            "Invalid search parameters."
        )

    run_experiment(
        args.hypotenuse,
        args.max_edge,
        args.top,
        args.output
    )
