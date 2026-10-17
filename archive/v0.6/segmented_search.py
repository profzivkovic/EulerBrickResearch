
import argparse
import csv
import heapq
import json
import os
import struct
from collections import defaultdict, OrderedDict
from fractions import Fraction
from itertools import combinations
from math import gcd, isqrt
from pathlib import Path
from time import perf_counter


VERSION = "0.6"
PAIR = struct.Struct("<QQ")
RESULT_FIELDS = [
    "a", "b", "c", "x", "y", "z",
    "space_squared", "space_floor",
    "square_gap", "normalized_gap", "perfect"
]


def is_square(n):
    r = isqrt(n)
    return r * r == n


def square_gap(n):
    r = isqrt(n)
    return min(n - r*r, (r+1)*(r+1)-n)


def normalized_gap(n):
    r = isqrt(n)
    k = r if n-r*r <= (r+1)*(r+1)-n else r+1
    return Fraction(abs(n-k*k), r+k)


def primitive(a, b, c):
    return gcd(gcd(a, b), c) == 1


def pythagorean_pairs(bound):
    """
    Yield every Pythagorean leg pair (a,b), a<b<=bound,
    exactly once, including nonprimitive multiples.
    """
    m = 2

    # Safe bound derived from:
    # m^2-n^2 <= B and 2mn <= B.
    while 2*m*m < 3*bound:

        n_max = min(m-1, bound // (2*m))

        for n in range(1, n_max+1):

            if gcd(m, n) != 1:
                continue

            if (m-n) % 2 == 0:
                continue

            u = m*m-n*n
            v = 2*m*n

            a, b = sorted((u, v))

            if b > bound:
                continue

            for k in range(1, bound//b+1):
                yield k*a, k*b

        m += 1


class FileCache:
    """
    Keep at most 'limit' binary files open at once.
    """
    def __init__(self, limit=32):
        self.limit = limit
        self.handles = OrderedDict()

    def write(self, path, data):
        if path in self.handles:
            handle = self.handles.pop(path)
        else:
            if len(self.handles) >= self.limit:
                _, old = self.handles.popitem(last=False)
                old.close()

            handle = open(path, "ab")

        self.handles[path] = handle
        handle.write(data)

    def close(self):
        for handle in self.handles.values():
            handle.close()
        self.handles.clear()


def atomic_json(path, obj):
    temp = path.with_suffix(".tmp")
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
    os.replace(temp, path)


def prepare_workspace(bound, segment_size, workdir):
    workdir.mkdir(parents=True, exist_ok=True)

    manifest_path = workdir / "manifest.json"
    signature = {
        "version": VERSION,
        "bound": bound,
        "segment_size": segment_size
    }

    if manifest_path.exists():
        with open(manifest_path, encoding="utf-8") as f:
            old = json.load(f)

        if any(old.get(k) != v for k, v in signature.items()):
            raise RuntimeError(
                "Workspace belongs to a different experiment. "
                "Use another --workdir."
            )

        if old.get("generation_complete"):
            print("Existing pair files found. Resuming.")
            return

        raise RuntimeError(
            "Previous pair generation was interrupted. "
            "Delete this workspace and restart generation."
        )

    # Prevent accidental reuse of unrelated workspace data.
    if any(workdir.iterdir()):
        raise RuntimeError(
            "Workspace is not empty and has no manifest. "
            "Choose a new --workdir."
        )

    print("Generating Pythagorean pairs on disk...")

    start = perf_counter()
    cache = FileCache()
    pair_count = 0

    try:
        for a, b in pythagorean_pairs(bound):
            segment_id = (a-1)//segment_size
            path = workdir / f"pairs_{segment_id:06d}.bin"

            cache.write(path, PAIR.pack(a, b))
            pair_count += 1

    finally:
        cache.close()

    atomic_json(manifest_path, {
        **signature,
        "generation_complete": True,
        "pair_count": pair_count
    })

    print(f"Pythagorean graph edges: {pair_count}")
    print(f"Pair generation: {perf_counter()-start:.3f}s")


def read_segment_pairs(path):
    """
    Read only one segment into memory.
    """
    neighbors = defaultdict(list)

    if not path.exists():
        return neighbors

    with open(path, "rb") as f:
        while True:
            chunk = f.read(PAIR.size * 8192)

            if not chunk:
                break

            if len(chunk) % PAIR.size != 0:
                raise RuntimeError(f"Corrupt binary file: {path}")

            for a, b in PAIR.iter_unpack(chunk):
                neighbors[a].append(b)

    return neighbors


def examine_brick(a, b, c):
    """
    All tests are exact integer arithmetic.
    """
    x2 = a*a+b*b
    y2 = a*a+c*c
    z2 = b*b+c*c

    x = isqrt(x2)
    y = isqrt(y2)
    z = isqrt(z2)

    if not (x*x == x2 and y*y == y2 and z*z == z2):
        return None

    if not primitive(a, b, c):
        return None

    s = a*a+b*b+c*c
    d = isqrt(s)

    gap = square_gap(s)
    norm = normalized_gap(s)
    perfect = d*d == s

    return [
        a, b, c, x, y, z, s, d,
        gap, float(norm), int(perfect)
    ]


def process_segment(workdir, segment_id):
    pair_path = workdir / f"pairs_{segment_id:06d}.bin"
    result_path = workdir / f"results_{segment_id:06d}.csv"
    temp_path = workdir / f"results_{segment_id:06d}.tmp"

    if result_path.exists():
        return False, 0

    neighbors = read_segment_pairs(pair_path)
    found = 0

    with open(temp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(RESULT_FIELDS)

        for a in sorted(neighbors):
            larger_edges = sorted(set(neighbors[a]))

            for b, c in combinations(larger_edges, 2):

                # Two faces involving a are already squares.
                # Only the third face must be checked.
                if not is_square(b*b+c*c):
                    continue

                brick = examine_brick(a, b, c)

                if brick is None:
                    continue

                writer.writerow(brick)
                found += 1

    # A segment is complete only after atomic rename.
    os.replace(temp_path, result_path)

    return True, found


def independent_bricks(bound):
    """
    Independent direct pair testing for small bounds.
    Does not use Euclid's formula.
    """
    neighbors = defaultdict(set)

    for a in range(1, bound+1):
        for b in range(a+1, bound+1):
            if is_square(a*a+b*b):
                neighbors[a].add(b)
                neighbors[b].add(a)

    bricks = set()

    for a in neighbors:
        for b in neighbors[a]:
            if b <= a:
                continue

            for c in neighbors[a]:
                if c > b and c in neighbors[b]:
                    if primitive(a, b, c):
                        bricks.add((a, b, c))

    return bricks


def verify_generator(bound):
    """
    Compare the Euclid-based pair generator with
    independently checked Pythagorean pairs.
    """
    generated = set(pythagorean_pairs(bound))

    direct = set()

    for a in range(1, bound+1):
        for b in range(a+1, bound+1):
            if is_square(a*a+b*b):
                direct.add((a, b))

    if generated != direct:
        print("Missing pairs:", sorted(direct-generated)[:10])
        print("Extra pairs:", sorted(generated-direct)[:10])
        raise AssertionError("Pythagorean pair verification failed")

    # Independently reconstruct Euler bricks from generated pairs.
    neighbors = defaultdict(set)

    for a, b in generated:
        neighbors[a].add(b)
        neighbors[b].add(a)

    graph_result = set()

    for a in neighbors:
        for b in neighbors[a]:
            if b <= a:
                continue

            for c in neighbors[a]:
                if c > b and c in neighbors[b]:
                    if primitive(a, b, c):
                        graph_result.add((a, b, c))

    reference = independent_bricks(bound)

    if graph_result != reference:
        raise AssertionError("Euler brick verification failed")

    print(
        f"VERIFICATION PASSED: bound={bound}, "
        f"pairs={len(generated)}, "
        f"primitive bricks={len(reference)}"
    )


def consolidate(workdir, segment_count, output, top):
    """
    Rebuild the final CSV and ranking from completed
    segment files. Safe to repeat after a restart.
    """
    heap = []
    total = 0
    perfect_count = 0

    temp_output = output.with_name(output.name + ".tmp")

    with open(temp_output, "w", newline="", encoding="utf-8") as out:
        writer = csv.writer(out)
        writer.writerow(RESULT_FIELDS)

        for segment_id in range(segment_count):
            path = workdir / f"results_{segment_id:06d}.csv"

            if not path.exists():
                raise RuntimeError(
                    f"Missing completed segment: {segment_id}"
                )

            with open(path, newline="", encoding="utf-8") as inp:
                reader = csv.DictReader(inp)

                for row in reader:
                    writer.writerow([row[k] for k in RESULT_FIELDS])

                    a = int(row["a"])
                    b = int(row["b"])
                    c = int(row["c"])
                    s = int(row["space_squared"])

                    gap = square_gap(s)
                    norm = normalized_gap(s)

                    total += 1
                    perfect_count += int(row["perfect"])

                    key = (-norm, -gap, -a, -b, -c)
                    entry = (key, (a, b, c, gap, norm))

                    if len(heap) < top:
                        heapq.heappush(heap, entry)
                    elif key > heap[0][0]:
                        heapq.heapreplace(heap, entry)

    os.replace(temp_output, output)

    return total, perfect_count, sorted(heap, reverse=True)


def run(args):
    start = perf_counter()

    if args.verify:
        verify_generator(args.verify)

    workdir = Path(args.workdir)
    output = Path(args.output)

    if output.resolve().is_relative_to(workdir.resolve()):
        raise ValueError(
            "Output CSV must be outside the workspace directory."
        )

    prepare_workspace(
        args.max_edge,
        args.segment_size,
        workdir
    )

    segment_count = (
        args.max_edge + args.segment_size - 1
    ) // args.segment_size

    print(f"\nSegments: {segment_count}")

    completed_now = 0

    for segment_id in range(segment_count):
        processed, found = process_segment(workdir, segment_id)

        if processed:
            completed_now += 1

        if (
            (segment_id+1) % args.progress_every == 0
            or segment_id+1 == segment_count
        ):
            print(
                f"Segments: {segment_id+1}/{segment_count}, "
                f"newly completed: {completed_now}, "
                f"last segment bricks: {found}, "
                f"elapsed: {perf_counter()-start:.2f}s",
                flush=True
            )

    total, perfect_count, best = consolidate(
        workdir,
        segment_count,
        output,
        args.top
    )

    print("\n" + "="*64)
    print("EULER BRICK RESEARCH - SEGMENTED SEARCH v0.6")
    print("="*64)

    print(f"Max edge: {args.max_edge}")
    print(f"Segment size: {args.segment_size}")
    print(f"Primitive Euler bricks: {total}")
    print(f"Perfect cuboids: {perfect_count}")
    print(f"Total time: {perf_counter()-start:.3f}s")

    print("\nTOP CANDIDATES")

    for _, (a, b, c, gap, norm) in best:
        print(
            f"({a}, {b}, {c}) "
            f"gap={gap} "
            f"normalized={float(norm):.9f}"
        )

    print(f"\nResults: {output}")
    print(f"Workspace: {workdir}")

    if perfect_count:
        print("\n*** PERFECT CUBOID CANDIDATE DETECTED ***")
        print("Inspect and independently verify the CSV results.")
    else:
        print("No perfect cuboid found in this search.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--max-edge", type=int, default=1000
    )
    parser.add_argument(
        "--segment-size", type=int, default=10000
    )
    parser.add_argument(
        "--top", type=int, default=20
    )
    parser.add_argument(
        "--verify", type=int, default=300
    )
    parser.add_argument(
        "--progress-every", type=int, default=10
    )
    parser.add_argument(
        "--workdir", default="segment_workspace"
    )
    parser.add_argument(
        "--output", default="segmented_results.csv"
    )

    args = parser.parse_args()

    if (
        args.max_edge < 1
        or args.segment_size < 1
        or args.top < 1
        or args.progress_every < 1
        or args.verify < 0
        or args.verify > 1000
        or args.max_edge > 4_000_000_000
    ):
        parser.error("Invalid parameter values.")

    run(args)
