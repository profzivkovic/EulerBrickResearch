
from collections import defaultdict
from math import gcd, isqrt
from time import perf_counter
import argparse
import csv


# =========================================================
# PYTHAGOREAN GRAPH
# =========================================================

def pythagorean_graph(max_edge):
    """
    Build a graph where a--b exists exactly when
    a^2 + b^2 is a perfect square.

    All endpoints are positive integers <= max_edge.
    """
    neighbors = defaultdict(set)
    primitive_count = 0

    m = 2

    while m*m - 1 <= max_edge:
        for n in range(1, m):

            if gcd(m, n) != 1:
                continue

            if (m - n) % 2 == 0:
                continue

            u = m*m - n*n
            v = 2*m*n

            lo, hi = sorted((u, v))

            if hi > max_edge:
                continue

            primitive_count += 1

            # Include every multiple of this primitive
            # Pythagorean pair within the edge bound.
            for k in range(1, max_edge // hi + 1):
                a = k * lo
                b = k * hi

                neighbors[a].add(b)
                neighbors[b].add(a)

        m += 1

    return neighbors, primitive_count


# =========================================================
# TRIANGLE SEARCH
# =========================================================

def primitive_bricks(neighbors):
    """
    Find graph triangles a < b < c.

    Keep only primitive Euler bricks:
    gcd(a, b, c) = 1.
    """
    for a in sorted(neighbors):

        larger_neighbors = sorted(
            b for b in neighbors[a] if b > a
        )

        for b in larger_neighbors:

            common = neighbors[a].intersection(
                neighbors[b]
            )

            for c in sorted(v for v in common if v > b):

                if gcd(gcd(a, b), c) == 1:
                    yield a, b, c


def square_gap(n):
    """Distance to the nearest perfect square."""
    r = isqrt(n)

    return min(
        n - r*r,
        (r+1)*(r+1) - n
    )


# =========================================================
# EXPERIMENT
# =========================================================

def run(max_edge, top, output):

    start = perf_counter()

    graph, primitive_count = pythagorean_graph(max_edge)

    graph_ready = perf_counter()

    total_bricks = 0
    perfect_count = 0
    best = []

    with open(
        output,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "a", "b", "c",
            "x", "y", "z",
            "space_squared",
            "nearest_space_integer",
            "square_gap",
            "perfect"
        ])

        for a, b, c in primitive_bricks(graph):

            total_bricks += 1

            # All three face diagonals are exact integers.
            x = isqrt(a*a + b*b)
            y = isqrt(a*a + c*c)
            z = isqrt(b*b + c*c)

            assert x*x == a*a + b*b
            assert y*y == a*a + c*c
            assert z*z == b*b + c*c

            space_squared = a*a + b*b + c*c

            d = isqrt(space_squared)

            perfect = (
                d*d == space_squared
            )

            gap = square_gap(space_squared)

            if perfect:
                perfect_count += 1

                print("\n*** PERFECT CUBOID FOUND ***")
                print(f"Edges: ({a}, {b}, {c})")
                print(f"Face diagonals: ({x}, {y}, {z})")
                print(f"Space diagonal: {d}")

            nearest = d

            if (
                (d+1)*(d+1) - space_squared
                < space_squared - d*d
            ):
                nearest = d+1

            writer.writerow([
                a, b, c,
                x, y, z,
                space_squared,
                nearest,
                gap,
                int(perfect)
            ])

            best.append(
                (gap, a, b, c)
            )

    best.sort()

    elapsed = perf_counter() - start

    print("=" * 60)
    print("EULER BRICK RESEARCH - GRAPH GENERATOR v0.4")
    print("=" * 60)

    print(f"Max edge: {max_edge}")
    print(f"Primitive Pythagorean triples: {primitive_count}")
    print(f"Graph vertices: {len(graph)}")
    print(
        "Graph edges:",
        sum(len(v) for v in graph.values()) // 2
    )

    print(f"Primitive Euler bricks: {total_bricks}")
    print(f"Perfect cuboids: {perfect_count}")

    print("\nPERFORMANCE")
    print(
        f"Graph construction: "
        f"{graph_ready-start:.3f} seconds"
    )
    print(f"Total time: {elapsed:.3f} seconds")

    print("\nTOP CANDIDATES (absolute square gap)")

    for gap, a, b, c in best[:top]:
        print(
            f"({a}, {b}, {c}) gap={gap}"
        )

    print(f"\nSaved to: {output}")

    if perfect_count == 0:
        print("No perfect cuboid found in this search.")


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--max-edge",
        type=int,
        default=1000
    )

    parser.add_argument(
        "--top",
        type=int,
        default=10
    )

    parser.add_argument(
        "--output",
        default="graph_bricks.csv"
    )

    args = parser.parse_args()

    if args.max_edge < 1 or args.top < 1:
        parser.error(
            "max-edge and top must be positive"
        )

    run(
        args.max_edge,
        args.top,
        args.output
    )
