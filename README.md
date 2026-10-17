# Euler Brick Research

Computational research into Euler bricks and the perfect cuboid problem.

## Mathematical problem

An Euler brick is a triple of positive integers \((a,b,c)\) for which all three face diagonals are integers:

- \(a^2+b^2=x^2\)
- \(a^2+c^2=y^2\)
- \(b^2+c^2=z^2\)

A perfect cuboid additionally requires an integer space diagonal:

\[
a^2+b^2+c^2=d^2.
\]

A brick is primitive when \(\gcd(a,b,c)=1\).

## Method

The search generates Pythagorean pairs using Euclid's parametrization and searches for compatible triples of edges.

The segmented implementation stores intermediate pairs on disk, processes segments independently, and supports result verification and optional temporary-file cleanup.

All integrality tests use exact integer arithmetic.

## Verified baseline

Search bound: maximum edge ≤ 1,000,000.

- Primitive Euler bricks found: **242**
- Perfect cuboids found: **0**
- Independent direct verification performed at bound 300
- Segmented output matches the reference CSV containing 242 bricks

### Benchmark

Environment: Python 3.11, Windows, local execution.

Version v0.6.2:

- Pair generation: 12.083 seconds
- Segment processing: 9.602 seconds
- Consolidation: 0.018 seconds
- Total runtime: 21.715 seconds

These are machine-dependent experimental measurements.

## Important limitation

A finite search does not prove that perfect cuboids do not exist. The existence of a perfect cuboid remains an open mathematical problem.

## Roadmap

1. Stabilize and validate local search implementations.
2. Improve performance and memory efficiency.
3. Extend exact searches to larger bounds.
4. Prepare reproducible cloud execution.
5. Investigate hybrid ACO/PSO methods and compare them against exact-search baselines.

## Dependencies

Python 3.11 or later. Standard library only.