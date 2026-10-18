# EulerBrickResearch

Reproducible, exact-integer research into **Euler bricks** and the **perfect cuboid problem**, using Python's standard library.

**Project status:** stable segmented systematic search **v0.7.2**, exercised through a maximum edge of **100,000,000**; stable independent odd-leg search **v0.9.5**, benchmarked through **10,000,000**; completed experimental swarm-optimization phase **v0.8.0–v0.8.2**. The verified catalog contains **1,884 primitive Euler bricks** through 100M.

> **Scientific scope:** No perfect cuboid was found in the finite searches and experiments reported here. This is **not a proof of nonexistence**. Exact validation certifies the arithmetic properties of reported rows, but does not by itself establish that a search implementation has found every solution within its bound. Heuristic experiments make no completeness claim.

## Mathematical problem

For positive integer edges \(0<a<b<c\), an **Euler brick** has three integer face diagonals:

\[
x^2=a^2+b^2,\qquad y^2=a^2+c^2,\qquad z^2=b^2+c^2.
\]

A brick is **primitive** if \(\gcd(a,b,c)=1\). A **perfect cuboid** is an Euler brick whose space diagonal is also an integer:

\[
d^2=a^2+b^2+c^2.
\]

Final square tests use exact integer arithmetic (`math.isqrt`); floating-point fitness values are used only to guide heuristic searches, not to certify solutions.

## Repository layout

```text
src/
  segmented_search.py        # stable segmented systematic engine, v0.7.2
  odd_leg_search.py          # stable number-theoretic odd-leg engine, v0.9.5
  pso_search.py              # diversity-preserving PSO, v0.8.1
  aco_search.py              # discrete ACO, v0.8.2
tools/
  validate_bricks.py         # independent exact-arithmetic CSV validator
  update_verified_catalog.py # guarded catalog and manifest updater
  analyze_odd_edge.py        # structural analysis of the odd edge
data/
  verified_euler_bricks.csv  # verified systematic-search catalog
  verified_manifest.json    # bound, counts, checksum, and provenance
experiments/
  pso_080_runs.csv
  bricks_pso_080.csv
  pso_081_runs.csv
  bricks_pso_081.csv
  aco_082_runs.csv
  bricks_aco_082.csv
archive/
  v0.7.1/                   # previous systematic engine
  v0.7.2/                   # stable segmented engine snapshot
  v0.9.0/                   # earlier stable odd-leg engine
  v0.9.5/                   # stable odd-leg engine snapshot
```

This tree lists the main research files; local workspaces, raw outputs, backups, and other utilities may also exist. The v0.8.0 PSO **results** are committed, but `src/pso_search.py` contains the later v0.8.1 implementation. Full source-level reproduction of v0.8.0 requires preserving its original script separately (for example, under `archive/v0.8.0/`). Do not treat v0.8.1 as the v0.8.0 source.

## Stable systematic search: v0.7.2

The systematic engine generates integer Pythagorean leg pairs using Euclid's parametrization and integer multiples, stores them in segmented binary files, and examines compatible pairs of neighbors to identify Euler-brick candidates. The remaining face-diagonal condition, primitivity, and perfect-cuboid condition are checked using exact integer arithmetic.

Every Euler brick corresponds to three mutually compatible Pythagorean leg pairs: equivalently, a triangle in the graph whose vertices are positive integers and whose edges join \(u,v\) when \(u^2+v^2\) is a perfect square. This provides a mathematical route to complete bounded enumeration **provided** that pair generation, bounds, segmentation, and candidate enumeration are all implemented without omissions. A formal, implementation-level completeness audit is a planned research task; the validator described below checks the **correctness of reported solutions**, not completeness.

### Recorded systematic runs

| Maximum edge \(c\) | Primitive Euler bricks | Additional bricks vs. previous bound | Pythagorean graph edges | Segments | Total elapsed time | Perfect cuboids |
|---:|---:|---:|---:|---:|---:|---:|
| 10,000,000 | **704** | — | 26,809,924 | 1,000 | 109.960 s | **0** |
| 20,000,000 | **943** | +239 | 56,095,944 | 2,000 | approximately 320.6 s | **0** |
| 50,000,000 | **1,395** | +452 | 148,422,582 | 5,000 | 1,040.977 s | **0** |
| 100,000,000 | **1,884** | +489 | 309,224,756 | 10,000 | 2,132.598 s | **0** |

The 20M timing is approximate because its initial run encountered a missing reference file at the optional output-comparison step; completed workspace data were then reused to consolidate the result. The other timings are as reported by the engine. Timings are machine- and storage-dependent.

The **100M** run reported 231.096 s for pair generation, 1,899.320 s for segment processing, and 2.174 s for consolidation. The independent CSV validator reported **1,884 rows, 1,884 unique primitive Euler bricks, zero perfect cuboids**, and confirmed that all **1,395** entries in the 50M catalog occur in the 100M result. These checks establish row-level arithmetic validity and preservation of the previous catalog; they are not an independent proof of enumeration completeness.

The final verified 100M catalog is maintained at `data/verified_euler_bricks.csv`, with metadata and a SHA-256 checksum in `data/verified_manifest.json`. It contains **1,884** unique primitive bricks. Raw outputs such as `bricks_100m.csv` are separate from the canonical catalog.

### Reproduce a bounded search

From the repository root in PowerShell:

```powershell
python src/segmented_search.py `
  --max-edge 100000000 `
  --segment-size 10000 `
  --memory-limit-mb 2048 `
  --progress-every 1000 `
  --workdir work_100m `
  --output bricks_100m.csv
```

This search can require substantial disk space and processing time. The `--memory-limit-mb` option governs pair-file buffering, **not** a hard limit on the process's total memory. A matching, completed pair-generation workspace can be reused, and finished segment outputs can be skipped when resuming. Preserve the workspace until output validation is complete; omit `--cleanup` if you intend to retain it.

**Important:** `--verify-output` is for comparing against an **existing reference CSV** for the same bound; it is not a destination for a verification report. Do not specify a nonexistent file there.

See `python src/segmented_search.py --help` for all options. The historical v0.7.3 optimization trial was slower and was **not accepted** as a release; v0.7.2 remains stable.

### Independently validate and update the catalog

First validate the new output and check that it contains every previously cataloged brick:

```powershell
python tools/validate_bricks.py `
  --input bricks_100m.csv `
  --max-edge 100000000 `
  --subset data/verified_euler_bricks.csv `
  --subset-max-edge 50000000
```

The `--subset-max-edge 50000000` command above documents the **historical 50M-to-100M upgrade** and is not a current update instruction: the canonical catalog is already at **100M**. For any future update, use the actual catalog bound recorded in `data/verified_manifest.json`. The validator checks sorted positive edges, bound, primitivity, all three integer face diagonals, uniqueness, and any supplied CSV metadata (including the space-diagonal tests and normalized gap).

After `VALIDATION PASSED`, preserve a backup of the current catalog and manifest, then run:

```powershell
python tools/update_verified_catalog.py `
  --input bricks_100m.csv `
  --max-edge 100000000 `
  --catalog data/verified_euler_bricks.csv `
  --manifest data/verified_manifest.json
```

The updater independently checks every incoming triple, validates the existing catalog against its manifest and SHA-256 checksum, rejects a decreasing bound, and requires the incoming set to include **all** previously cataloged bricks. It then writes a canonical, deduplicated catalog and updated manifest. It does **not** silently repair a missing old result by taking a union.

Finally, validate the updated catalog:

```powershell
python tools/validate_bricks.py `
  --input data/verified_euler_bricks.csv `
  --max-edge 100000000
```

For the 100M dataset, the expected successful result is `rows=1884; unique=1884; perfect=0` and `VALIDATION PASSED`. Only then review and commit the catalog and manifest. The updater's two-file replacement is not a single atomic transaction; if interrupted, its checksum check can detect an inconsistent catalog/manifest pair on a subsequent run.

## Experimental metaheuristics: v0.8.0–v0.8.2

These methods use two Euclidean Pythagorean triples, scaled to share a leg, to construct candidates with **at least two exact integer face diagonals**. The remaining face condition and space diagonal are checked using exact arithmetic. Optimization is heuristic: no completeness or existence/nonexistence guarantee is claimed.

- **v0.8.0:** initial particle swarm optimization (PSO).
- **v0.8.1:** PSO with neighborhoods, stagnation tracking, and particle restarts to improve diversity.
- **v0.8.2:** discrete ant colony optimization (ACO) with pheromone reinforcement, evaporation, and exploration.
- **RANDOM:** independently seeded random sampling under the same per-run evaluation budget, used as a baseline.

Each experiment used **30 independent runs per method**, `--max-edge 10000000`, `--max-m 120`, and **64,320 candidate evaluations per run** for each method. The baseline is repeated in the three experiment files; it is not three independent sets of random-baseline findings.

### Observed results

| Method | Mean primitive bricks / run | Mean unique candidates / run | Distinct bricks across 30 runs |
|---|---:|---:|---:|
| PSO v0.8.0 | 5.47 | 25,883 | 60 |
| PSO v0.8.1 | 8.10 | 29,052 | 67 |
| ACO v0.8.2 | 5.47 | 19,823 | 42 |
| **RANDOM baseline** | **17.43** | **52,007** | **91** |

These are descriptive results for the tested implementations, parameters, and search space. They do **not** establish that random search is universally superior to PSO, ACO, or other metaheuristics.

All reported Euler-brick rows in the three experimental candidate CSV files were checked against exact integer conditions in the corresponding experiment review. None was a perfect cuboid. Candidate CSV rows can repeat a brick across runs; the **distinct bricks** column deduplicates by `(a, b, c)` within each method's 30 runs. Experimental discoveries should not enter the stable catalog without independent verification and a deliberate catalog-update process.

### Reproduce PSO v0.8.1

```powershell
python src/pso_search.py --runs 30 --max-edge 10000000 --max-m 120 --particles 80 --iterations 200 --stagnation 12 --restart-fraction 0.30 --neighborhoods 5 --seed 42 --output bricks_pso_081.csv --summary-output pso_081_runs.csv
```

### Reproduce ACO v0.8.2

```powershell
python src/aco_search.py --runs 30 --max-edge 10000000 --max-m 120 --ants 80 --iterations 200 --evaporation 0.20 --elite-fraction 0.20 --exploration 0.15 --seed 42 --output bricks_aco_082.csv --summary-output aco_082_runs.csv
```

The scripts require no third-party Python packages. Use `python src/pso_search.py --help` and `python src/aco_search.py --help` for full parameter descriptions. The committed `experiments/` CSVs contain per-run metrics and candidate data. Execution times depend on the machine.

### Interpretation and limitations

The tested PSO and ACO configurations revisit many candidates and find fewer Euler bricks than the random baseline. One possible explanation is that a continuous-style fitness signal for near-square diagonals does not reliably predict exact integer solutions. This is a **hypothesis**, not a mathematical theorem.

Finding more Euler bricks is a useful benchmark, but it is **not equivalent** to finding a perfect cuboid. A small gap to a nearby square does not imply a nearby exact solution. New fitness functions or algorithms should be evaluated against random sampling with exact validation, matched evaluation budgets, and multiple independent runs.

## Number-theoretic odd-leg search: stable v0.9.5

Every primitive Euler brick has exactly one odd edge and two even edges. Fix an odd edge `o`. If an even edge `e` forms an integer face diagonal `h` with it, then

\[
(h-e)(h+e)=o^2.
\]

Enumerating factor pairs `u*v = o**2`, with `u < o`, yields `e = (v-u)//2`. The implementation uses a smallest-prime-factor (SPF) sieve and exact integer arithmetic to enumerate compatible even legs, then tests pairs of such legs for primitivity and the third integer face diagonal. Sorting the three edges produces canonical triples. This is a mathematically exhaustive candidate construction for a fixed maximum edge, subject to correct implementation and bounds.

### Proven modulo-3 partition

For any integer right triangle, both legs cannot be nonmultiples of 3, since nonzero squares are 1 modulo 3 and 1+1 is not a square modulo 3. Therefore at least two edges of any Euler brick are divisible by 3. In a **primitive** Euler brick all three cannot be divisible by 3, so **exactly two edges are divisible by 3**.

Consequently, when the fixed odd edge is divisible by 3, exactly one of the two even edges must be divisible by 3; otherwise both even edges must be divisible by 3. Version **v0.9.5** partitions candidate even legs accordingly, rejecting impossible pair classes before the innermost arithmetic tests.

### Recorded odd-leg benchmarks

| Maximum edge | v0.9.0 elapsed | v0.9.5 elapsed | Time reduction | Primitive bricks | Perfect cuboids | Catalog comparison |
|---:|---:|---:|---:|---:|---:|---|
| 1,000,000 | 5.453 s | **4.726 s** | **13.3%** | **242** | **0** | Exact set match |
| 10,000,000 | 74.742 s | **61.853 s** | **17.2%** | **704** | **0** | Exact set match |

At 1M, v0.9.5 reduced **7,827,990** possible even-leg pairs to **4,089,066** pairs (47.76% reduction), with **2,169,432** exact `isqrt` tests. At 10M, it reduced **134,138,852** pairs to **69,526,974** (48.17% reduction), with **33,697,155** `isqrt` tests. Both runs reported `missing=0; extra=0` against the verified catalog restricted to the requested bound. Timings are observations on the test machine, not hardware-independent performance guarantees.

These comparisons provide useful cross-checks between the segmented and odd-leg implementations on overlapping bounds. They do not replace a formal source-level completeness audit. The odd-leg implementation has **not** been reported as benchmarked through 100M; the 100M result belongs to the segmented engine.

### Reproduce the odd-leg benchmark

From the repository root in PowerShell:

```powershell
python src/odd_leg_search.py `
  --max-edge 10000000 `
  --reference data/verified_euler_bricks.csv `
  --output odd_leg_10m.csv `
  --progress-every 1000000
```

Expected: `Primitive Euler bricks: 704`, `Perfect cuboids: 0`, `REFERENCE: expected=704; missing=0; extra=0`, and `EXACT SET MATCH`. Use `--max-edge 1000000` for the faster 242-brick check. The stable source is archived at `archive/v0.9.5/odd_leg_search.py`; v0.9.0 is preserved separately at `archive/v0.9.0/odd_leg_search.py`.

### Odd-edge structural analysis

The independent analysis tool `tools/analyze_odd_edge.py` examined the **1,884** primitive bricks in the verified 100M catalog. These are **finite-catalog observations**, except where a general modular argument is explicitly given.

| Property | Catalog count |
|---|---:|
| Both even edges share a nontrivial gcd with the odd edge | 1,393 (73.94%) |
| Exactly one even edge is coprime to the odd edge | 486 (25.80%) |
| Both even edges are coprime to the odd edge | 5 (0.27%) |
| Exactly two edges divisible by 3 | 1,884 (100%; also proved generally) |
| Exactly two edges divisible by 5 | 1,201 |
| Exactly one edge divisible by 5 | 683 |

For example, `(140, 480, 693)` is primitive although `gcd(693,140)=7` and `gcd(693,480)=3`. The common gcd of **all three** edges, not pairwise coprimality, defines primitivity. All 1,884 catalog bricks have both even edges divisible by 4; this catalog observation should not be confused with a proof of the strongest possible universal 2-adic restriction.

### Next research tasks

1. Audit implementation-level completeness and cross-check the two independent bounded enumerators.
2. Investigate low-overhead modular filters beyond 3; require both exact catalog agreement and repeatable runtime gains before promoting a new stable version.
3. Analyze shared factors, parameter families, parity, edge ratios, and distributions without extrapolating finite observations into unproved universal laws.
4. Study exact space-diagonal square gaps as descriptive arithmetic data, not evidence of a perfect cuboid.
5. Preserve benchmark configurations and stable source snapshots for reproducibility.

No perfect cuboid was found within the reported finite bounds. This remains **a bounded computational result, not a proof of global nonexistence**.

## Reproducibility and integrity

- Verify primitive edges, all three face diagonals, and the space diagonal using exact `gcd` and `isqrt` checks.
- Preserve search bounds, segment settings, source versions, and validation logs for systematic runs.
- Maintain a canonical catalog with a checked manifest and SHA-256 digest; back up the catalog before updating it.
- Keep random seeds, evaluation counts, algorithm parameters, and per-run results alongside heuristic candidate CSVs.
- Distinguish **evaluations**, **unique candidates**, **per-run discoveries**, and **globally distinct discoveries**.
- Avoid treating duplicate discoveries or repeated baseline results as independent evidence.
- Preserve stable releases; do not replace a validated systematic engine with an unverified optimization.
- Never interpret absence of a perfect cuboid within a finite bound as a proof of global nonexistence.

## Project links

GitHub: https://github.com/profzivkovic/EulerBrickResearch
