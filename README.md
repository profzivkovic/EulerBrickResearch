# Euler Brick Research

**Exact computational research into Euler bricks and the perfect cuboid problem**

A Python research project dedicated to generating, validating, cataloging, and analyzing primitive Euler bricks using exact integer arithmetic.

The project focuses on:

- Mathematically correct enumeration
- Reproducible computational experiments
- Independent result validation
- Performance optimization
- Version-controlled verified datasets
- Investigation of the open perfect cuboid problem

**Current search engine:** v0.7.1  
**Largest completed search:** 10,000,000  
**Primitive Euler bricks found:** 704  
**Perfect cuboids found:** 0  
**Implementation:** Python 3.11, standard library only

---

## 1. Mathematical Background

An **Euler brick** is a rectangular cuboid with positive integer edges \(a,b,c\), such that all three face diagonals are integers:

\[
a^2+b^2=x^2
\]

\[
a^2+c^2=y^2
\]

\[
b^2+c^2=z^2
\]

An Euler brick is **primitive** if:

\[
\gcd(a,b,c)=1
\]

A **perfect cuboid** is an Euler brick whose space diagonal is also an integer:

\[
a^2+b^2+c^2=d^2
\]

The existence of a perfect cuboid remains an open mathematical problem.

A finite computational search cannot prove that perfect cuboids do not exist.

---

## 2. Research Objectives

The project has several long-term objectives:

1. Generate primitive Euler bricks efficiently.
2. Search for perfect cuboids using exact integer arithmetic.
3. Independently validate generated results.
4. Maintain a persistent, version-controlled catalog of verified Euler bricks.
5. Compare the correctness and performance of successive search engines.
6. Extend the computational search to increasingly large bounds.
7. Explore mathematical constraints and computational optimizations.
8. Investigate heuristic approaches such as ACO and PSO, with exact arithmetic verification.

---

## 3. Repository Structure

```text
EulerBrickResearch/
│
├── README.md
├── .gitignore
│
├── src/
│   └── segmented_search.py
│
├── tools/
│   ├── validate_bricks.py
│   └── update_verified_catalog.py
│
├── archive/
│   ├── v0.1/
│   │   └── generator.py
│   ├── v0.2/
│   │   └── graph_generator.py
│   ├── v0.5/
│   │   └── search_engine.py
│   ├── v0.6/
│   │   └── segmented_search.py
│   ├── v0.6.1/
│   │   └── segmented_search.py
│   └── v0.6.2/
│       └── segmented_search.py
│
├── tests/
│   └── test_regression.py
│
└── data/
    ├── verified_euler_bricks.csv
    └── verified_manifest.json
```

### Directory responsibilities

| Directory | Purpose |
|---|---|
| `src/` | Current stable search engine |
| `tools/` | Validation and verified-catalog management |
| `archive/` | Historical search implementations |
| `tests/` | Automated regression tests |
| `data/` | Version-controlled verified results and metadata |

Experimental CSV outputs and temporary workspaces are excluded from Git.

Early archive labels `v0.1` and `v0.2` are organizational labels and do not necessarily correspond to formal releases.

---

## 4. Search Methodology

The search is based on exact generation of Pythagorean edge pairs and enumeration of compatible triples.

### 4.1 Pythagorean pair generation

Primitive Pythagorean triples are generated using Euclid's parametrization:

\[
u=m^2-n^2
\]

\[
v=2mn
\]

\[
w=m^2+n^2
\]

where:

\[
m>n>0,\quad \gcd(m,n)=1
\]

and \(m,n\) have opposite parity.

Positive integer multiples of the primitive legs provide compatible pairs of Euler brick edges.

### 4.2 Graph interpretation

The search can be interpreted as a graph problem:

- Vertices represent positive integer edge lengths.
- Two vertices are connected if the sum of their squares is a perfect square.
- A triangle corresponds to an Euler brick.

The search retains primitive bricks with ordered edges:

\[
0<a<b<c\leq B
\]

where \(B\) is the maximum edge bound.

### 4.3 Disk-backed segmented search

The implementation distributes generated Pythagorean pairs into disk-backed segments.

This avoids storing the entire graph in memory and allows larger searches with bounded write buffers.

### 4.4 Exact verification

Integer square tests use Python's `math.isqrt`.

No floating-point approximation is used to decide whether a brick or a perfect cuboid is valid.

Floating-point calculations are used only for reporting and ranking approximate numerical gaps.

---

## 5. Search Engine Development

| Version | Description |
|---|---|
| Early prototypes | Initial Euler brick generators |
| v0.5 | In-memory graph-based enumeration |
| v0.6 | Disk-backed segmented search |
| v0.6.1 | Buffered disk writing |
| v0.6.2 | Bounded buffers, reference-output verification, workspace cleanup |
| **v0.7.1** | **Optimized pair generation and faster segmented processing** |

The current implementation is:

`src/segmented_search.py`

Historical implementations are preserved in `archive/`.

Git history provides an additional record of project development.

Baseline tag: `v0.6.2-baseline`.

---

## 6. Computational Results

All searches use primitive Euler bricks with maximum edge \(c\leq B\).

### 6.1 Enumeration results

| Maximum edge | Pythagorean graph edges | Primitive Euler bricks | Perfect cuboids |
|---|---:|---:|---:|
| 1,000,000 | 2,269,788 | 242 | 0 |
| 2,000,000 | 4,787,097 | 331 | 0 |
| 5,000,000 | 12,786,105 | 528 | 0 |
| **10,000,000** | **26,809,924** | **704** | **0** |

The search through 10,000,000 found **176 additional primitive Euler bricks** compared with the 5,000,000 search.

### 6.2 Performance benchmarks

Benchmarks were measured during local Windows executions.

| Bound | Engine | Pair generation | Segment processing | Total runtime |
|---|---|---:|---:|---:|
| 1,000,000 | v0.6.2 | 12.083 s | 9.602 s | 21.715 s |
| 2,000,000 | v0.6.2 | 32.661 s | 21.176 s | 53.880 s |
| 5,000,000 | v0.6.2 | 86.577 s | 64.953 s | 151.612 s |
| 5,000,000 | v0.7.1 | 6.558 s | 38.122 s | 44.758 s |
| **10,000,000** | **v0.7.1** | **23.015 s** | **144.395 s** | **167.596 s** |

At the 5,000,000 bound, v0.7.1 was approximately **3.39 times faster overall** than v0.6.2.

At the 10,000,000 bound, segment processing accounted for approximately **86% of total runtime**.

This makes segment processing the primary optimization target for the next search-engine version.

Runtime measurements are machine-dependent.

### 6.3 Search verification

The v0.7.1 search through 5,000,000 produced an identical set of 528 Euler bricks compared with v0.6.2:

```text
OUTPUT IDENTICAL: True; expected=528, actual=528, rows=528
```

The 10,000,000 run completed with:

```text
VERIFICATION PASSED: bound=300, pairs=249, primitive bricks=2

Pythagorean graph edges: 26809924
Primitive Euler bricks: 704
Perfect cuboids: 0

Pair generation: 23.015s
Segment processing: 144.395s
Consolidation: 0.176s
Total time: 167.596s
```

The small-bound verification passed during the 10,000,000 run.

Independent CSV validation of the 10,000,000 result and its inclusion in the verified catalog are separate steps.

Agreement between search implementations and arithmetic validation increase confidence in the results but do not constitute a general proof of completeness.

---

## 7. Numerical Candidate Analysis

For an Euler brick, define:

\[
S=a^2+b^2+c^2
\]

Let \(k\) be the nearest integer to \(\sqrt S\).

The square gap is:

\[
\Delta=|S-k^2|
\]

The approximate distance between the space diagonal and the nearest integer can be ranked using:

\[
\delta=\frac{|S-k^2|}{\lfloor\sqrt S\rfloor+k}
\]

This provides a numerical ranking metric, not a criterion for mathematical existence.

### 7.1 Best candidate through 10,000,000

```text
Edges: (37835, 269280, 1244484)
Square gap: 165
Approximate diagonal distance: 0.000064765
```

### 7.2 Additional notable candidates

| Edges | Square gap | Approximate distance |
|---|---:|---:|
| (318175, 3357792, 6431880) | 1272 | 0.000087572 |
| (330165, 672220, 3502992) | 647 | 0.000090309 |
| (108108, 250800, 486875) | 1760 | 0.001576376 |
| (28083, 43056, 105820) | 400 | 0.001700030 |

The first candidate remains the closest found through 10,000,000 under this ranking metric.

None is a perfect cuboid.

A small numerical gap does not imply that a perfect cuboid exists.

---

## 8. Independent Validation

The independent validation utility is:

`tools/validate_bricks.py`

It verifies:

- Positive integer edge lengths
- Strict ordering \(a<b<c\)
- Primitivity
- Integral face diagonals
- Maximum-edge constraints
- Absence of duplicate records
- Perfect cuboid status
- Inclusion of previously validated datasets

A small-bound independent cross-check at \(B=300\) confirmed:

```text
Pythagorean pairs: 249
Primitive Euler bricks: 2
```

Validation of the records confirms their arithmetic correctness.

It does not independently prove that every possible Euler brick within a large bound was found.

---

## 9. Verified Euler Brick Catalog

The repository maintains two version-controlled files:

```text
data/verified_euler_bricks.csv
data/verified_manifest.json
```

The CSV stores unique, arithmetically validated primitive Euler bricks.

The manifest records catalog metadata, including the verified search bound, dataset count, integrity hash, and update history.

The catalog is updated using:

`tools/update_verified_catalog.py`

### Catalog update procedure

1. Complete the new search.
2. Validate the output independently.
3. Verify that the previous catalog is a subset of the new results.
4. Merge the new records into the catalog.
5. Validate the updated catalog.
6. Commit the updated CSV and manifest to Git.

**Latest completed search:** 10,000,000, with 704 primitive Euler bricks.

**Catalog status:** The 10,000,000 results are ready for independent validation and catalog update. The committed catalog should not be described as containing 704 records until those steps succeed.

---

## 10. Requirements

- Python 3.11 or a compatible Python 3 version
- Python standard library only
- Sufficient free disk space for intermediate search segments
- Windows, Linux, or macOS

Development and benchmark measurements have primarily been performed locally on Windows using PyCharm.

---

## 11. Running the Search

Run all commands from the repository root.

### 11.1 Small verification run

```powershell
python src/segmented_search.py --max-edge 300 --segment-size 10000 --memory-limit-mb 32 --verify 300 --workdir work_test --output bricks_test.csv --cleanup
```

Expected:

```text
Primitive Euler bricks: 2
Perfect cuboids: 0
```

### 11.2 Search through 10,000,000

```powershell
python src/segmented_search.py --max-edge 10000000 --segment-size 10000 --memory-limit-mb 32 --verify 300 --workdir work_10m --output bricks_10m.csv --cleanup
```

The completed v0.7.1 search found 704 primitive Euler bricks and no perfect cuboids.

### 11.3 Independently validate the 10,000,000 output

For the existing output file:

```powershell
python tools/validate_bricks.py --input bricks_071_10m.csv --max-edge 10000000 --subset data/verified_euler_bricks.csv --subset-max-edge 5000000
```

The subset bound assumes that the existing verified catalog covers 5,000,000.

Expected result counts, if the existing catalog contains 528 records:

```text
INPUT: bricks_071_10m.csv; rows=704; unique=704; perfect=0
SUBSET: data/verified_euler_bricks.csv; rows=528; unique=528; missing=0
VALIDATION PASSED
```

### 11.4 Update the catalog

Only after validation succeeds:

```powershell
python tools/update_verified_catalog.py --input bricks_071_10m.csv --max-edge 10000000
```

If the previous catalog contains 528 records, the expected update is:

```text
previous=528, added=176, total=704
```

### 11.5 Validate the updated catalog

```powershell
python tools/validate_bricks.py --input data/verified_euler_bricks.csv --max-edge 10000000
```

The expected final status is:

```text
VALIDATION PASSED
```

### 11.6 Run automated regression tests

```powershell
python -m unittest discover -s tests -v
```

The regression suite is intended to detect changes that break known search and validation behavior.

---

## 12. Reproducibility and Version Control

Every major computational milestone should record:

1. Search-engine version
2. Maximum edge bound
3. Search configuration
4. Number of generated Pythagorean pairs
5. Number of primitive Euler bricks
6. Number of perfect cuboids
7. Runtime breakdown
8. Independent validation results
9. Catalog update information
10. Git commit or release tag

Historical implementations remain available under `archive/`.

Verified data remains under `data/`.

Experimental CSV outputs and temporary search workspaces are excluded from Git.

---

## 13. Development Roadmap

### Completed

- Exact Pythagorean pair generation
- Graph-based Euler brick enumeration
- Disk-backed segmented search
- Bounded write buffers
- Independent arithmetic validator
- Version-controlled verified catalog infrastructure
- Repository reorganization
- v0.7.1 search-engine optimization
- Search through 10,000,000

### Next steps

1. Independently validate the 10,000,000 dataset.
2. Extend the verified catalog to 704 records.
3. Commit the new catalog and updated documentation.
4. Profile segment processing.
5. Develop v0.7.2 with further performance improvements.
6. Add stronger regression and completeness cross-checks.

### Future research

- Resumable searches and checkpointing
- Parallel segment processing
- Larger search bounds
- Mathematical pruning techniques
- Cloud execution
- ACO/PSO experimental methods with exact verification

---

## 14. Scientific Limitations

No perfect cuboid has been found in the completed search through maximum edge 10,000,000.

This is a finite computational result.

It is **not** a proof that perfect cuboids do not exist.

Independent validation confirms arithmetic correctness of recorded candidates, while small-bound cross-checks and agreement between implementations provide additional evidence of search correctness.

They do not replace a general mathematical proof.

The perfect cuboid problem remains open.

---

## 15. Project Status

| Item | Current status |
|---|---|
| Search engine | v0.7.1 |
| Largest completed bound | 10,000,000 |
| Primitive Euler bricks found | 704 |
| Perfect cuboids found | 0 |
| Latest runtime | 167.596 s |
| Main performance bottleneck | Segment processing |
| Next planned engine | v0.7.2 |

**Repository:** https://github.com/profzivkovic/EulerBrickResearch

---

*Euler Brick Research — exact computation, reproducible experiments, and verified mathematical data.*