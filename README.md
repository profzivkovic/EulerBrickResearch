# Euler Brick Research

Computational research into Euler bricks and the open perfect cuboid problem.

## Mathematical definitions

An **Euler brick** is a triple of positive integers \(a,b,c\) for which all three face diagonals are integers:

\[
a^2+b^2=x^2,\qquad
a^2+c^2=y^2,\qquad
b^2+c^2=z^2.
\]

A **perfect cuboid** additionally requires an integer space diagonal:

\[
a^2+b^2+c^2=d^2.
\]

A brick is **primitive** if \(\gcd(a,b,c)=1\).

The existence of a perfect cuboid remains an open mathematical problem.

## Search approach

The project uses exact integer arithmetic and Pythagorean-pair generation based on Euclid's parametrization.

The segmented search implementation:

- Generates compatible Pythagorean edge pairs.
- Stores intermediate pairs in disk-backed segments.
- Enumerates Euler brick candidates.
- Uses `math.isqrt` for exact square tests.
- Supports bounded write buffers and optional workspace cleanup.
- Produces CSV output for subsequent validation.

The project uses Python 3.11 and the standard library.

## Computational results

| Maximum edge | Primitive Euler bricks | Perfect cuboids | Runtime |
|---|---:|---:|---:|
| 1,000,000 | 242 | 0 | 21.715 s |
| 2,000,000 | 331 | 0 | 53.880 s |
| 5,000,000 | 528 | 0 | 151.612 s |

These runtimes were measured locally on Windows using `segmented_search_v062.py`. They are machine-dependent.

### Best numerical candidate

Within the search bound of 5,000,000, the candidate with the smallest approximate absolute difference between its space diagonal and the nearest integer is:

**(37835, 269280, 1244484)**

Its squared-space-diagonal gap from the nearest integer square is **165**, corresponding to an approximate diagonal difference of **0.000064765**.

This is not a perfect cuboid, and numerical closeness does not imply existence.

## Validation

The project includes `validate_bricks_v07.py`, which independently checks CSV records for:

- Positive, strictly ordered integer edges.
- All three integral face diagonals.
- Primitivity.
- Duplicate records.
- Maximum-edge bounds.
- Integral space diagonals.
- Inclusion of previously validated results.

Direct enumeration cross-checks have also been performed for small bounds.

CSV validation confirms the correctness of recorded bricks, but does not independently establish that the generator found every possible brick within a search bound.

## Verified catalog

The repository maintains a growing catalog:

- `data/verified_euler_bricks.csv`
- `data/verified_manifest.json`

The catalog contains unique, arithmetically validated primitive Euler bricks.

After a new search passes validation, `update_verified_catalog.py` merges its results into the catalog and updates the manifest.

The catalog is version-controlled, while large experimental outputs and temporary workspaces are excluded from Git.

## Running a search

Example: search up to 5,000,000.

```powershell
python segmented_search_v062.py --max-edge 5000000 --segment-size 10000 --memory-limit-mb 32 --verify 300 --workdir work_062_5m --output bricks_062_5m.csv --cleanup
```

Validate the result against the existing catalog:

```powershell
python validate_bricks_v07.py --input bricks_062_5m.csv --max-edge 5000000 --subset data/verified_euler_bricks.csv --subset-max-edge 2000000
```

Update the catalog after successful validation:

```powershell
python update_verified_catalog.py --input bricks_062_5m.csv --max-edge 5000000
```

## Version history

- **v0.5:** In-memory graph search and reference results.
- **v0.6:** Disk-backed segmented search.
- **v0.6.1:** Buffered disk writing.
- **v0.6.2:** Bounded buffers, output comparison, and optional cleanup.
- **v0.7:** Independent CSV validation and a persistent verified catalog.

Baseline Git tag: `v0.6.2-baseline`.

## Roadmap

1. Improve local search performance and reproducibility.
2. Extend exact searches to larger bounds.
3. Strengthen independent completeness