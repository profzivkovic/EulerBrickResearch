# Euler Brick Research

**Computational research into Euler bricks and the perfect cuboid problem**

A Python research project for generating, validating, cataloging, and analyzing primitive Euler bricks using exact integer arithmetic.

The project emphasizes reproducibility, independent validation, performance benchmarking, and preservation of verified computational results.

**Current search engine:** v0.7.1  
**Largest completed search:** 5,000,000  
**Primitive Euler bricks found:** 528  
**Perfect cuboids found:** 0  
**Language:** Python 3.11 (standard library only)

---

## 1. Mathematical background

An **Euler brick** is a rectangular cuboid with positive integer edges \(a,b,c\) such that all three face diagonals are integers:

\[
a^2+b^2=x^2
\]

\[
a^2+c^2=y^2
\]

\[
b^2+c^2=z^2
\]

A brick is **primitive** when:

\[
\gcd(a,b,c)=1
\]

A **perfect cuboid** is an Euler brick whose space diagonal is also an integer:

\[
a^2+b^2+c^2=d^2
\]

The existence of a perfect cuboid is an unsolved mathematical problem.

A finite computational search cannot establish nonexistence in general.

---

## 2. Research objectives

The main goals of this project are:

1. Generate primitive Euler bricks efficiently.
2. Search for perfect cuboid candidates using exact arithmetic.
3. Validate all generated results independently.
4. Maintain a version-controlled catalog of verified Euler bricks.
5. Benchmark successive search-engine implementations.
6. Extend searches to larger integer bounds.
7. Investigate mathematical and computational improvements to the search process.

Future experimental directions may include heuristic methods such as ant colony optimization (ACO) and particle swarm optimization (PSO), evaluated against exact-search baselines.

---

## 3. Repository structure

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
└── data/
    ├── verified_euler_bricks.csv
    └── verified_manifest.json
```

### Directory responsibilities

| Directory | Purpose |
|---|---|
| `src/` | Current stable search implementation |
| `tools/` | Independent validation and catalog-management utilities |
| `archive/` | Historical implementations preserved for reproducibility |
| `data/` | Verified Euler brick catalog and metadata |

Experimental CSV outputs and temporary search workspaces are not committed to Git.

The labels `v0.1` and `v0.2` in the archive are organizational labels for early implementations, not necessarily historical release tags.

---

## 4. Search methodology

The current implementation uses a disk-backed segmented search.

### 4.1 Pythagorean pair generation

Compatible integer edge pairs are generated using Euclid's parametrization of primitive Pythagorean triples and their positive integer multiples.

For integers \(m>n>0\), with:

\[
\gcd(m,n)=1
\]

and opposite parity, the primitive Pythagorean triple is:

\[
(m^2-n^2,\ 2mn,\ m^2+n^2)
\]

The two legs provide a pair of compatible cuboid edges.

### 4.2 Graph-based brick construction

A graph is constructed conceptually in which:

- Each vertex represents an integer edge length.
- An edge connects two lengths when the sum of their squares is a perfect square.
- A triangle corresponds to an Euler brick.

The search enumerates compatible triples, retaining only primitive bricks with strictly ordered edges:

\[
0<a<b<c\leq B
\]

where \(B\) is the configured maximum edge.

### 4.3 Segmented processing

Rather than retaining the complete graph in memory, the implementation distributes intermediate pairs into disk-backed segments.

This enables larger searches with bounded in-memory write buffers.

### 4.4 Exact arithmetic

All square checks use Python's `math.isqrt`.

No floating-point approximation is used to determine whether a candidate is an Euler brick or a perfect cuboid.

Floating-point values are used only for optional numerical ranking and reporting.

---

## 5. Search engine versions

| Version | Main development |
|---|---|
| Early prototypes | Initial Euler brick generation and graph exploration |
| v0.5 | In-memory graph-based search |
| v0.6 | Disk-backed segmented search |
| v0.6.1 | Buffered disk writing |
| v0.6.2 | Globally bounded buffers, reference comparison, optional cleanup |
| **v0.7.1** | **Optimized Pythagorean pair generation and segment processing** |

The current stable implementation is:

`src/segmented_search.py`

Earlier implementations are preserved in `archive/`.

Git commits and tags preserve the history of the entire repository.

Existing baseline tag: `v0.6.2-baseline`.

---

## 6. Computational results

All reported searches use primitive Euler bricks with maximum edge \(c\leq B\).

### 6.1 Search results

| Maximum edge | Pythagorean graph edges | Primitive Euler bricks | Perfect cuboids |
|---|---:|---:|---:|
| 1,000,000 | 2,269,788 | 242 | 0 |
| 2,000,000 | 4,787,097 | 331 | 0 |
| 5,000,000 | 12,786,105 | 528 | 0 |

The 5,000,000 search found 197 additional primitive Euler bricks compared with the 2,000,000 search.

### 6.2 Performance benchmarks

The following measurements were obtained from local Windows executions.

| Search bound | Engine | Pair generation | Segment processing | Total runtime |
|---|---|---:|---:|---:|
| 1,000,000 | v0.6.2 | 12.083 s | 9.602 s | 21.715 s |
| 2,000,000 | v0.6.2 | 32.661 s | 21.176 s | 53.880 s |
| 5,000,000 | v0.6.2 | 86.577 s | 64.953 s | 151.612 s |
| **5,000,000** | **v0.7.1** | **6.558 s** | **38.122 s** | **44.758 s** |

At the 5,000,000 bound, v0.7.1 achieved:

- Approximately **13.20× faster pair generation**.
- Approximately **1.70× faster segment processing**.
- Approximately **3.39× faster overall execution**.

These are observed benchmark results, not guaranteed speedups on other systems.

### 6.3 Result equivalence

The v0.7.1 search at 5,000,000 produced:

```text
VERIFICATION PASSED: bound=300, pairs=249, primitive bricks=2

Pythagorean graph edges: 12786105

OUTPUT IDENTICAL: True; expected=528, actual=528, rows=528

Primitive Euler bricks: 528
Perfect cuboids: 0
Total time: 44.758s
```

The result set was identical to the v0.6.2 reference output.

This confirms agreement between the two implementations for that search, but is not an independent proof of completeness.

---

## 7. Numerical candidates

For an Euler brick, define:

\[
S=a^2+b^2+c^2
\]

Let \(k\) be the nearest integer to \(\sqrt S\).

The square gap is:

\[
\Delta=|S-k^2|
\]

A useful normalized ranking quantity is:

\[
\delta=\frac{|S-k^2|}{\lfloor\sqrt S\rfloor+k}
\]

This approximates the absolute distance between the space diagonal and the nearest integer.

### Best candidate found through 5,000,000

```text
a = 37835
b = 269280
c = 1244484

Square gap = 165
Approximate diagonal distance = 0.000064765
```

Another notable candidate:

```text
a = 330165
b = 672220
c = 3502992

Square gap = 647
Approximate diagonal distance = 0.000090309
```

Neither candidate is a perfect cuboid.

A small numerical gap does not imply that a perfect cuboid exists or that the open problem is close to being solved.

---

## 8. Independent validation

The validation utility is:

`tools/validate_bricks.py`

It checks:

- Positive integer edge lengths.
- Strict ordering \(a<b<c\).
- Primitivity.
- All three face diagonals using exact integer arithmetic.
- Maximum-edge bounds.
- Duplicate records.
- Perfect cuboid status.
- Inclusion of previously validated subsets.

A small-bound cross-check against independent brute-force enumeration has been performed at \(B=300\):

```text
Pythagorean pairs: 249
Primitive Euler bricks: 2
```

This provides a useful correctness check for the generator.

Arithmetic validation of output records does not by itself prove that the search found every Euler brick within a larger bound.

---

## 9. Verified Euler brick catalog

The project maintains a persistent catalog of verified primitive Euler bricks:

```text
data/verified_euler_bricks.csv
data/verified_manifest.json
```

The CSV stores the verified brick records.

The JSON manifest records catalog metadata, including search bounds and integrity information.

The catalog is updated only after a successful independent validation of a new search result.

At the completed 5,000,000 bound, the verified dataset contains **528 unique primitive Euler bricks**.

The catalog is tracked in Git, allowing changes to be inspected and historical versions to be recovered.

---

## 10. Requirements

- Python 3.11 or compatible Python 3 version.
- No third-party Python dependencies.
- Sufficient free disk space for intermediate search segments.
- Windows, Linux, or macOS.

The project is developed and benchmarked primarily on Windows using PyCharm.

---

## 11. Running the search

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

### 11.2 Search up to 5,000,000

```powershell
python src/segmented_search.py --max-edge 5000000 --segment-size 10000 --memory-limit-mb 32 --verify 300 --workdir work_5m --output bricks_5m.csv --cleanup
```

Expected:

```text
Primitive Euler bricks: 528
Perfect cuboids: 0
```

### 11.3 Validate a search result

```powershell
python tools/validate_bricks.py --input bricks_5m.csv --max-edge 5000000
```

Expected final status:

```text
VALIDATION PASSED
```

### 11.4 Compare against an existing catalog

```powershell
python tools/validate_bricks.py --input bricks_5m.csv --max-edge 5000000 --subset data/verified_euler_bricks.csv --subset-max-edge 5000000
```

This verifies that the previously cataloged bricks are present in the new output.

For a new, larger search, the subset bound should match the previous verified catalog bound.

### 11.5 Update the verified catalog

Only after validation succeeds:

```powershell
python tools/update_verified_catalog.py --input bricks_5m.csv --max-edge 5000000
```

The catalog updater merges verified results and updates its manifest.

Do not use a new search output to update the catalog before checking its validity.

---

## 12. Reproducibility

Each research milestone should preserve:

1. The exact search-engine version.
2. The maximum edge bound.
3. The search parameters.
4. The number of generated Pythagorean pairs.
5. The number of primitive Euler bricks.
6. The number of perfect cuboids.
7. Runtime measurements.
8. Validation results.
9. The corresponding Git commit or tag.

Temporary workspaces and large experimental CSV outputs are excluded from version control.

Verified catalog files remain tracked.

---

## 13. Roadmap

### Phase 1 — Completed

- Exact Euler brick generation.
- Graph-based enumeration.
- Disk-backed segmented processing.
- Bounded memory buffers.
- Independent arithmetic validation.
- Persistent verified catalog.
- Search through 5,000,000.
- Performance optimization in v0.7.1.

### Phase 2 — Next

- Reorganize the repository into `src/`, `tools/`, `archive/`, and `data/`.
- Add automated regression tests.
- Extend the search to 10,000,000.
- Validate and merge new results into the catalog.
- Investigate further segment-processing optimizations.

### Phase 3 — Future

- Resumable and checkpointed searches.
- More systematic performance profiling.
- Parallel and cloud-based experiments.
- Mathematical filtering and candidate analysis.
- Experimental ACO/PSO approaches with exact verification.

---

## 14. Scientific limitations

The search has not found a perfect cuboid through the tested maximum-edge bound of 5,000,000.

This result is computational and finite.

It does **not** establish that perfect cuboids do not exist.

Similarly, agreement between two search implementations, independent arithmetic validation, and small-bound brute-force checks increase confidence in the computational results but do not constitute a general mathematical proof.

The perfect cuboid problem remains open.

---

## 15. Project status

**Current stable engine:** v0.7.1  
**Maximum completed search:** 5,000,000  
**Verified primitive Euler bricks:** 528  
**Perfect cuboids discovered:** 0  
**Next planned search:** 10,000,000  

Repository: https://github.com/profzivkovic/EulerBrickResearch

---

*Euler Brick Research — exact computation, reproducible experiments, and verified mathematical data.*