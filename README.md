# Euler Brick Research

**Exact computational research into Euler bricks and the perfect cuboid problem**

EulerBrickResearch is a Python project for generating, validating, cataloging, and analyzing primitive Euler bricks using exact integer arithmetic.

The project emphasizes reproducible computation, independent arithmetic validation, version-controlled results, and performance optimization.

**Current experimental engine:** v0.7.2  
**Largest completed search:** 10,000,000  
**Primitive Euler bricks found:** 704  
**Perfect cuboids found:** 0  
**Implementation:** Python 3.11, standard library only

## 1. Mathematical Background

An Euler brick is a rectangular cuboid with positive integer edges \(a,b,c\) such that all three face diagonals are integers:

\[
a^2+b^2=x^2
\]

\[
a^2+c^2=y^2
\]

\[
b^2+c^2=z^2
\]

An Euler brick is primitive when:

\[
\gcd(a,b,c)=1
\]

A perfect cuboid is an Euler brick whose space diagonal is also an integer:

\[
a^2+b^2+c^2=d^2
\]

The existence of a perfect cuboid remains an open mathematical problem.

A finite computational search cannot establish nonexistence.

## 2. Research Objectives

The main objectives are:

- Generate primitive Euler bricks efficiently.
- Search for perfect cuboids using exact integer arithmetic.
- Validate every recorded candidate independently.
- Maintain a version-controlled verified catalog.
- Compare results across search-engine versions.
- Optimize performance while preserving mathematical correctness.
- Extend the maximum search bound.
- Explore mathematical pruning and alternative search methods.

## 3. Repository Structure

```text
EulerBrickResearch/
├── README.md
├── .gitignore
├── src/
│   ├── segmented_search.py
│   └── segmented_search_v072.py
├── tools/
│   ├── validate_bricks.py
│   └── update_verified_catalog.py
├── data/
│   ├── verified_euler_bricks.csv
│   └── verified_manifest.json
├── tests/
│   └── test_regression.py
└── archive/
    ├── v0.1/
    ├── v0.2/
    ├── v0.5/
    ├── v0.6/
    ├── v0.6.1/
    └── v0.6.2/
```

`src/segmented_search.py` is the preserved v0.7.1 implementation.

`src/segmented_search_v072.py` is the optimized v0.7.2 implementation.

Historical implementations are retained in `archive/`.

The verified dataset and its metadata are stored in `data/`.

Experimental outputs and temporary workspaces should remain excluded from Git.

The repository structure above describes the intended layout; optional regression-test files should be present before their corresponding commands are used.

## 4. Search Methodology

### 4.1 Pythagorean pair generation

Primitive Pythagorean triples are generated using Euclid's parametrization:

\[
u=m^2-n^2,\quad v=2mn
\]

with:

\[
m>n>0,\quad \gcd(m,n)=1
\]

and opposite parity for \(m,n\).

Integer multiples of the primitive legs generate Pythagorean edge pairs within the search bound.

### 4.2 Graph interpretation

The search represents integer edge lengths as graph vertices.

Two vertices are connected when the sum of their squares is a perfect square.

Three mutually compatible vertices form an Euler brick.

Only ordered primitive triples are retained:

\[
0<a<b<c\leq B
\]

where \(B\) is the maximum edge bound.

### 4.3 Segmented disk-backed processing

Generated Pythagorean pairs are written to disk-backed segments using bounded buffers.

Segments are processed independently, and their results are consolidated into a CSV file.

This approach avoids keeping the entire generated graph in memory.

### 4.4 Exact arithmetic

The engine uses `math.isqrt` for exact integer square tests.

Floating-point arithmetic is not used to decide whether an Euler brick or perfect cuboid is valid.

## 5. Search Engine Versions

| Version | Main development |
|---|---|
| Early prototypes | Initial Euler brick generators |
| v0.5 | In-memory graph enumeration |
| v0.6 | Disk-backed segmented processing |
| v0.6.1 | Buffered disk writes |
| v0.6.2 | Bounded buffering and output verification |
| v0.7.1 | Faster pair generation and segmented processing |
| **v0.7.2** | **Modular square-residue filters in segment processing** |

### 5.1 Optimization in v0.7.2

Profiling v0.7.1 at a maximum edge of 1,000,000 showed approximately 22.3 million calls to the square-testing function.

Version 0.7.2 introduces precomputed modular filters for moduli 64 and 63.

Before evaluating whether:

\[
b^2+c^2
\]

is a perfect square, the engine checks whether its residues are compatible with square residues modulo both moduli.

Candidates failing either filter are rejected without calling `math.isqrt`.

Candidates passing the filters are still checked using exact integer arithmetic.

The filters cannot reject a genuine perfect square because every integer square has an allowed residue.

The underlying enumeration and CSV output format remain unchanged.

## 6. Computational Results

### 6.1 Enumeration

| Maximum edge | Pythagorean graph edges | Primitive Euler bricks | Perfect cuboids |
|---|---:|---:|---:|
| 1,000,000 | 2,269,788 | 242 | 0 |
| 2,000,000 | 4,787,097 | 331 | 0 |
| 5,000,000 | 12,786,105 | 528 | 0 |
| **10,000,000** | **26,809,924** | **704** | **0** |

The search through 10,000,000 found 176 additional primitive Euler bricks compared with the search through 5,000,000.

### 6.2 Performance benchmarks

The following measurements come from local Windows executions.

| Bound | Version | Pair generation | Segment processing | Total runtime |
|---|---|---:|---:|---:|
| 1,000,000 | v0.6.2 | 12.083 s | 9.602 s | 21.715 s |
| 2,000,000 | v0.6.2 | 32.661 s | 21.176 s | 53.880 s |
| 5,000,000 | v0.6.2 | 86.577 s | 64.953 s | 151.612 s |
| 5,000,000 | v0.7.1 | 6.558 s | 38.122 s | 44.758 s |
| 10,000,000 | v0.7.1 | 23.015 s | 144.395 s | 167.596 s |
| 1,000,000 | v0.7.2 | 1.099 s | 5.639 s | 6.763 s |
| **10,000,000** | **v0.7.2** | **15.148 s** | **94.670 s** | **109.960 s** |

At the 10,000,000 bound, v0.7.2 completed approximately 1.52 times faster than the recorded v0.7.1 run.

The measured reduction in total runtime was approximately 34.4%.

Because pair generation also ran faster despite being unchanged, these measurements should not be interpreted as an isolated benchmark of the modular filtering optimization.

Runtime measurements depend on hardware and execution conditions.

### 6.3 Result comparison

The v0.7.1 search through 5,000,000 matched the reference output:

```text
OUTPUT IDENTICAL: True; expected=528, actual=528, rows=528
```

The v0.7.2 search through 10,000,000 matched the verified catalog:

```text
OUTPUT IDENTICAL: True; expected=704, actual=704, rows=704
```

The comparison checks the set of edge triples and the number of output rows.

Independent arithmetic validation of the v0.7.2 output is an additional verification step.

## 7. Candidate Analysis

For each Euler brick, define:

\[
S=a^2+b^2+c^2
\]

Let \(k\) be the nearest integer to \(\sqrt S\).

The square gap is:

\[
\Delta=|S-k^2|
\]

For ranking purposes, the engine reports a normalized gap based on:

\[
\delta=\frac{|S-k^2|}{\lfloor\sqrt S\rfloor+k}
\]

This is a numerical ranking measure, not a test for the existence of a perfect cuboid.

### Best candidate found through 10,000,000

```text
Edges: (37835, 269280, 1244484)
Square gap: 165
Normalized gap: 0.000064765
```

Additional notable candidates:

| Edges | Square gap | Normalized gap |
|---|---:|---:|
| (318175, 3357792, 6431880) | 1272 | 0.000087572 |
| (330165, 672220, 3502992) | 647 | 0.000090309 |
| (108108, 250800, 486875) | 1760 | 0.001576376 |
| (28083, 43056, 105820) | 400 | 0.001700030 |

None is a perfect cuboid.

A small numerical gap does not establish the existence of a perfect cuboid.

## 8. Verification and Validation

### 8.1 Small-bound cross-check

The engine independently compares generated Pythagorean pairs against direct enumeration at a small bound.

For \(B=300\):

```text
VERIFICATION PASSED: bound=300, pairs=249, primitive bricks=2
```

### 8.2 Independent CSV validator

The validator is:

```text
tools/validate_bricks.py
```

It checks:

- Positive integer edges
- Strict ordering
- Maximum-edge bound
- Primitivity
- Integral face diagonals
- Duplicate records
- Perfect cuboid status
- Inclusion of previously verified records

The catalog through 10,000,000 has passed arithmetic validation:

```text
INPUT: data\verified_euler_bricks.csv; rows=704; unique=704; perfect=0
VALIDATION PASSED
```

Arithmetic validation establishes correctness of the stored rows. It does not independently prove completeness