# EulerBrickResearch

Reproducible, exact-integer research into **Euler bricks** and the **perfect cuboid problem**, using exact integer arithmetic in Python, with an optional NumPy/Numba-accelerated experimental engine.

**Project status:** stable segmented systematic search **v0.7.2**, exercised through a maximum edge of **100,000,000**; stable independent odd-leg search **v0.9.9**, independently cross-checked through **100,000,000** and extended with exact row validation through **200,000,000**; completed experimental swarm-optimization phase **v0.8.0–v0.8.2**; experimental fused Numba odd-leg engine **v0.10.4**, regression-tested through **200,000,000**. The verified catalog contains **2,509 primitive Euler bricks** through 200M (625 additional bricks beyond 100M).

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
  segmented_search.py        # stable systematic engine, v0.7.2
  odd_leg_search.py          # stable independent odd-leg engine, v0.9.9
  odd_leg_numba_v0104.py     # experimental fused Numba odd-leg engine, v0.10.4
  pso_search.py              # diversity-preserving PSO, v0.8.1
  aco_search.py              # discrete ACO, v0.8.2
tools/
  validate_bricks.py         # independent exact-arithmetic CSV validator
  update_verified_catalog.py # guarded catalog and manifest updater
  audit_odd_leg.py           # bounded independent audit of stable v0.9.9
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
  v0.9.5/                   # earlier odd-leg release
  v0.9.8/                   # earlier odd-leg release
  v0.9.9/                   # current stable odd-leg release
  v0.10.0/ ... v0.10.3/     # archived experimental Numba prototypes
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

The current verified **200M** catalog is maintained at `data/verified_euler_bricks.csv`, with metadata and a SHA-256 checksum in `data/verified_manifest.json`. Raw outputs such as `bricks_100m.csv` are separate from the canonical catalog.

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

Historical example: validate a 100M output against a prior 50M catalog:

```powershell
python tools/validate_bricks.py `
  --input bricks_100m.csv `
  --max-edge 100000000 `
  --subset data/verified_euler_bricks.csv `
  --subset-max-edge 50000000
```

The subset bound above illustrates a **historical 50M-to-100M upgrade**. The current verified catalog is already at 200M; do not rerun this historical upgrade against the current catalog. For future updates, use the actual catalog bound recorded in `data/verified_manifest.json`. The validator checks sorted positive edges, bound, primitivity, all three integer face diagonals, uniqueness, and any supplied CSV metadata (including the space-diagonal tests and normalized gap).

Historical example only (do not run against the current 200M catalog):

```powershell
python tools/update_verified_catalog.py `
  --input bricks_100m.csv `
  --max-edge 100000000 `
  --catalog data/verified_euler_bricks.csv `
  --manifest data/verified_manifest.json
```

The updater independently checks every incoming triple, validates the existing catalog against its manifest and SHA-256 checksum, rejects a decreasing bound, and requires the incoming set to include **all** previously cataloged bricks. It then writes a canonical, deduplicated catalog and updated manifest. It does **not** silently repair a missing old result by taking a union.

Validate the current 200M catalog:

```powershell
python tools/validate_bricks.py `
  --input data/verified_euler_bricks.csv `
  --max-edge 200000000
```

For the current 200M dataset, the expected successful result is `rows=2509; unique=2509; perfect=0` and `VALIDATION PASSED`. Only then review and commit the catalog and manifest. The updater's two-file replacement is not a single atomic transaction; if interrupted, its checksum check can detect an inconsistent catalog/manifest pair on a subsequent run.

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

## Stable independent odd-leg search: v0.9.9

The odd-leg engine (`src/odd_leg_search.py`) provides a second, number-theoretically structured bounded enumerator, independent of the segmented Pythagorean graph implementation. It uses exact integer arithmetic and the Python standard library.

Every **primitive Euler brick** has exactly one odd edge, denoted \(o\), and two even edges \(e_1,e_2\). For any even edge \(e\) sharing an integer face diagonal with \(o\), factorization gives

\[
o^2+e^2=h^2,\qquad (h-e)(h+e)=o^2.
\]

Thus, for positive divisors \(u,v\) satisfying \(uv=o^2\), \(u<v\), and \(u\equiv v\pmod 2\), a compatible even edge is \(e=(v-u)/2\). Because \(o\) is odd, all divisors of \(o^2\) are odd, so the parity condition is automatic. The engine factors each odd \(o\) with a smallest-prime-factor (SPF) sieve, generates eligible divisors \(u<o\), constructs compatible even edges up to the requested bound, and tests their pairs. It checks primitivity, the remaining face diagonal, and the space diagonal with exact `math.gcd` and `math.isqrt` operations.

### Proven modulo-3 pair partition

For any integer right triangle, if neither leg is divisible by 3, the sum of their squares is 2 modulo 3 and cannot be a square. Consequently, in a primitive Euler brick **exactly two of the three edges are divisible by 3**: at least two are required by the three face-diagonal conditions, while all three would contradict primitivity. Therefore:

- If \(3\mid o\), exactly one of the two even edges must be divisible by 3.
- If \(3\nmid o\), both even edges must be divisible by 3.

The engine partitions compatible even legs accordingly and enumerates only allowed pairs. This is a mathematically justified filter, not an empirical heuristic.

### Version history and benchmarks

- **v0.9.5:** stable modulo-3 pair partition, using divisor generation from prime factorization.
- **v0.9.8:** iterative bounded divisor generation; retained the exact candidate set and improved normal-run performance.
- **v0.9.9 (current stable):** combines divisor generation with construction of compatible even legs, avoiding an intermediate final divisor list; also caches `gcd(odd, e1)` outside the inner pair loop when `odd` is divisible by 3.

| Maximum edge | Primitive bricks | Perfect cuboids | v0.9.8 median | v0.9.9 median | Improvement |
|---:|---:|---:|---:|---:|---:|
| 1,000,000 | **242** | **0** | 4.303 s | **4.044 s** | **6.02%** |
| 10,000,000 | **704** | **0** | 59.393 s | **54.821 s** | **7.70%** |

The 1M figures are medians of **five interleaved runs per version**; the 10M figures are medians of **three interleaved runs per version**. Timings are environment-dependent, and earlier 10M sessions exhibited considerable variability. These are empirical speed comparisons, not complexity guarantees.

At 10M, v0.9.9 examined **134,138,852** possible pairs, retained **69,526,974** after modulo-3 partitioning (48.17% reduction), and performed **33,697,155** integer-square-root tests on primitive candidate pairs.

### Independent cross-validation through 100M

The stable v0.9.9 implementation was subsequently run at 20M, 50M, and 100M without changing the algorithm. Every run produced `EXACT SET MATCH` against the corresponding subset of `data/verified_euler_bricks.csv`, with **zero missing rows, zero extra rows, and zero perfect cuboids**.

| Maximum edge | Primitive bricks | v0.7.2 elapsed | v0.9.9 elapsed | v0.7.2 / v0.9.9 |
|---:|---:|---:|---:|---:|
| 10,000,000 | 704 | 109.960 s | 54.821 s* | 2.01x |
| 20,000,000 | 943 | ~320.6 s† | 122.196 s | ~2.62x |
| 50,000,000 | 1,395 | 1,040.977 s | 393.047 s | 2.65x |
| 100,000,000 | **1,884** | 2,132.598 s | **1,119.861 s** | **1.90x** |

*The 10M v0.9.9 figure is the median of three interleaved benchmark runs; the 20M, 50M, and 100M v0.9.9 figures are single runs. †The 20M segmented timing is approximate for the reason documented in the systematic-search section. These are recorded timings, not controlled head-to-head benchmarks; hardware load and storage conditions may vary.*

| v0.9.9 metric | 20M | 50M | 100M |
|---|---:|---:|---:|
| All possible pairs | 311,733,835 | 943,628,669 | 2,170,029,622 |
| Pairs after modulo-3 partition | 161,245,073 | 486,850,846 | 1,117,554,441 |
| Primitive candidate pairs / `isqrt` calls | 76,248,717 | 223,212,641 | 501,018,824 |
| Rejected nonprimitive pairs | 84,996,356 | 263,638,205 | 616,535,617 |
| Pair reduction | 48.27% | 48.41% | 48.50% |
| SPF sieve time | 3.474 s | 8.874 s | 19.023 s |
| Search time | 118.715 s | 384.162 s | 1,100.810 s |
| Total elapsed | 122.196 s | 393.047 s | 1,119.861 s |
| Reference comparison | EXACT SET MATCH | EXACT SET MATCH | EXACT SET MATCH |

At 100M, odd-leg v0.9.9 took approximately **18 minutes 40 seconds**, versus **35 minutes 33 seconds** for segmented v0.7.2, an observed **47.49% reduction in elapsed time**. At the time of these 100M comparisons, the reference was the systematic-search catalog. These runs provide an independent enumerator cross-check, not a formal implementation-level proof of completeness. No perfect cuboid was found within the tested bound.

### Extended odd-leg search through 200M

The unchanged stable v0.9.9 engine was run at a maximum edge of **200,000,000** without a reference comparison. It reported **2,509 primitive Euler bricks**, **zero perfect cuboids**, and an elapsed time of **2,015.158 s** (33 min 35 s). This is **625 more bricks** than the 100M catalog.

| v0.9.9 metric | 200M |
|---|---:|
| All possible pairs | 4,970,604,761 |
| Pairs after modulo-3 partition | 2,555,512,427 |
| Primitive candidate pairs / `isqrt` calls | 1,121,177,836 |
| Rejected nonprimitive pairs | 1,434,334,591 |
| Pair reduction | 48.59% |
| SPF sieve time | 41.221 s |
| Search time | 1,973.898 s |
| Total elapsed | **2,015.158 s** |
| Perfect cuboids | **0** |

The independent exact-arithmetic CSV validator reported `rows=2509; unique=2509; perfect=0` and `VALIDATION PASSED`. A subset check against the previous 100M catalog reported `rows=1884; unique=1884; missing=0`. After catalog updating, validation of `data/verified_euler_bricks.csv` again reported `rows=2509; unique=2509; perfect=0` and `VALIDATION PASSED`.

**Evidence boundary:** through 100M, two independently implemented enumerators produced identical sets. Between 100M and 200M, the result currently comes from the odd-leg enumerator, with independent validation of every reported triple and preservation of the prior catalog. Row validation does **not** independently prove enumeration completeness. No perfect cuboid was found within this finite search bound; this does not prove global nonexistence.

### Reproduce the odd-leg search

From the repository root in PowerShell:

```powershell
python src/odd_leg_search.py `
  --max-edge 200000000 `
  --output odd_leg_200m_v099.csv `
  --progress-every 10000000
```

Expected output includes `Primitive Euler bricks: 2509` and `Perfect cuboids: 0`. No reference comparison is requested for this command. The script writes canonical `(a,b,c)` triples to the specified CSV. Its CLI options are listed by `python src/odd_leg_search.py --help`. At 200M the SPF array alone requires approximately 800 MB; total process memory can be higher. Use 64-bit Python and adequate available RAM.

## Experimental Numba odd-leg engine: v0.10.4

The experimental `src/odd_leg_numba_v0104.py` fuses compatible-even-leg generation, modulo-3 partitioning, primitivity checks, and the remaining face-diagonal square test into Numba-compiled kernels. It imports the **unchanged** stable v0.9.9 source for SPF construction, candidate verification, and reference loading. It requires **NumPy** and **Numba** (tested with Python 3.11.1 64-bit and Numba 0.68.0); the stable v0.9.9 engine remains standard-library-only. The v0.10.0–v0.10.3 prototypes are preserved in `archive/`.

The v0.10.4 source is the renamed, numerically hardened `v0.10.3-safe` variant. Its complete runs were executed under the `v0.10.3-safe` display label before the version-string-only rename. A post-rename smoke test at 1M found 242 bricks and reported `EXACT SET MATCH`; no algorithmic changes were made by the rename.

| Maximum edge | Primitive bricks | Primitive candidate pairs | Perfect cuboids | v0.10.4 elapsed | Reference comparison |
|---:|---:|---:|---:|---:|---|
| 1,000,000 | 242 | 2,169,432 | 0 | 2.335 s (post-rename smoke test) | EXACT SET MATCH |
| 10,000,000 | 704 | 33,697,155 | 0 | 14.288 s | EXACT SET MATCH |
| 50,000,000 | 1,395 | 223,212,641 | 0 | 73.879 s | EXACT SET MATCH |
| 100,000,000 | 1,884 | 501,018,824 | 0 | 158.897 s | EXACT SET MATCH |
| 200,000,000 | **2,509** | **1,121,177,836** | **0** | **544.830 s** | **EXACT SET MATCH** |

These are recorded individual run times, not a controlled benchmark of v0.10.4. The 1M smoke-test time includes initial Numba compilation; the larger runs were performed before the display-label rename. At 200M, the fused kernel processed 100,000,000 odd values, and the SPF sieve took 38.595 s. The comparison uses the existing verified catalog; since the accelerated engine shares the odd-leg construction with v0.9.9, this is **regression evidence, not an independent enumeration-completeness proof**.

A controlled **three-cycle interleaved 10M benchmark** compared stable v0.9.9 with the earlier *original* v0.10.3 (not v0.10.4). The stable median was **55.066 s** and the original v0.10.3 median was **13.076 s**, a **4.21×** ratio. Do not attribute this controlled figure to v0.10.4. A separately recorded v0.10.4 run at 200M took 544.830 s versus an earlier v0.9.9 run of 2,015.158 s (3.70× ratio, **not** a controlled paired benchmark).

### Reproduce the accelerated search

From the repository root in PowerShell, after installing compatible NumPy and Numba versions:

```powershell
python src/odd_leg_numba_v0104.py `
  --source src/odd_leg_search.py `
  --max-edge 200000000 `
  --reference data/verified_euler_bricks.csv `
  --output odd_leg_numba_104_200m.csv
```

Expected result: 2,509 primitive bricks, zero perfect cuboids, and `EXACT SET MATCH`. The SPF array alone occupies approximately 800 MB at 200M; total process memory is higher. The program currently restricts `--max-edge` to at most 1,000,000,000 for signed-64-bit arithmetic, but running near that limit requires adequate RAM and additional large-bound operational testing.

### Bounded audit of the stable odd-leg engine

`tools/audit_odd_leg.py` checks v0.9.9 compatible legs against direct integer-square tests, tests sampled factorizations and divisors, and compares the complete small-bound result against an independent Pythagorean-pair graph enumerator. It also checks pair accounting and parity/modulo-3 constraints. For example:

```powershell
python tools/audit_odd_leg.py --source src/odd_leg_search.py --max-edge 1000 --samples 150
python tools/audit_odd_leg.py --source src/odd_leg_search.py --max-edge 3000 --samples 150
```

These are finite bounded checks, **not** formal proofs. This audit directly targets v0.9.9, not the Numba kernel. The latter is checked against the reference catalog and by the stable engine's exact candidate verifier.

## Next research steps

1. **Preserve the 200M evidence:** retain the stable and accelerated logs, independently validated 2,509-row catalog, manifest checksum, and independent cross-validation through 100M.
2. **Audit bounded completeness:** extend implementation-level review of divisor generation, numerical bounds, and candidate enumeration; distinguish finite tests from formal proofs.
3. **Plan 500M, then 1B:** assess SPF memory and runtime, validate new rows independently, preserve the previous catalog as a subset, and record provenance before updating the canonical catalog.
4. **Investigate arithmetic structure:** analyze parity, prime-factor distributions, modular constraints, and exact space-diagonal square gaps; distinguish proofs from finite-data observations.

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
