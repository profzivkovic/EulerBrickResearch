# EulerBrickResearch

Reproducible, exact-integer research into **Euler bricks** and the **perfect cuboid problem**, using exact integer arithmetic in Python, with NumPy/Numba-accelerated global-SPF and segmented-SPF odd-leg engines.

**Project status (2026-10-25):** the experimental overflow-safe **v0.21.0** checkpointed odd-leg search completed the inclusive **20,000,000,000 (20B)** maximum-edge bound: **14,010 distinct primitive Euler bricks**, **100,000 segments**, and **10,000/10,000 durable checkpoints**. Reconstruction from sealed Google Drive checkpoints passed **10,000 SHA-256 checks**, exact Python-integer validation of all 14,010 triples, and **EXACT SET MATCH** for all **10,932** previous bricks through 10B; **3,078** additional bricks lie above 10B. The canonical CSV has SHA-256 `a810bbdd6280d5d7e5cc74665bc5b1388e6179abbb5f326f208a736a12bb3a41`. The stable segmented-SPF engine remains **v0.18.0**, separately audited to **2B**; v0.21.0 is experimental. Independent published triple-by-triple corroboration remains limited to **3,556** bricks strictly below 500M. This is a completed computational enumeration, **not** an independent proof of implementation-level completeness.

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
  odd_leg_search.py                  # stable independent odd-leg engine, v0.9.9
  odd_leg_numba.py                   # global-SPF engine, v0.10.4
  odd_leg_numba_segmented.py         # stable segmented-SPF engine, v0.18.0 (<=2B)
  segmented_factorization.py
  safe_square_10b.py                 # experimental overflow-safe helpers
  odd_leg_numba_10b_experimental.py
  safe_arithmetic_1000b.py           # experimental arithmetic, not a 1000B search result
  odd_leg_numba_1000b_experimental.py
  pso_search.py
  aco_search.py
tools/
  analysis/                           # distribution, growth, diagonal analyses
  audits/                             # validation, arithmetic and capacity audits
    int64_v0170/                     # historical three-phase signed-64-bit audit
  benchmarks/                         # segment, memory and parallel benchmarks
  catalog/                            # guarded catalog updater
  runners/
    checkpoint_parallel_v0180.py
    colab_checkpoint_sync_v0180.py
    checkpoint_parallel_v0200.py     # experimental resumable 10B runner
    colab_checkpoint_sync_v0200.py   # VM/Google Drive durable mirror
    checkpoint_parallel_v0210.py     # experimental resumable 20B runner
    colab_checkpoint_sync_v0210.py   # 20B VM/Google Drive durable mirror
data/
  verified_euler_bricks.csv           # canonical catalog (20B after promotion)
  verified_manifest.json             # check bound/hash before treating as current
experiments/metaheuristics/
archive/                               # preserved historical implementations
```

The tree highlights principal files, not every utility. Keep generated checkpoint directories and intermediate CSVs out of Git. The 10B and 20B Drive checkpoint mirrors are external reproducibility artifacts, not a committed repository directory. The previous 2B catalog remains recoverable through Git history. **Manifest consistency must be checked separately:** copying a new CSV does not update `data/verified_manifest.json`; its recorded bound, count and checksum must match the canonical CSV before calling the catalog/manifest pair synchronized.

## Historical systematic graph search: v0.7.2

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

The current verified catalog (extended from **10B** to **20B** in October 2026) is maintained at `data/verified_euler_bricks.csv`, with metadata and a SHA-256 checksum in `data/verified_manifest.json`. Raw outputs such as `bricks_100m.csv` are separate from the canonical catalog.

### Reproduce a bounded search

From the repository root in PowerShell:

```powershell
python archive/v0.7.2/segmented_search.py `
  --max-edge 100000000 `
  --segment-size 10000 `
  --memory-limit-mb 2048 `
  --progress-every 1000 `
  --workdir work_100m `
  --output bricks_100m.csv
```

This search can require substantial disk space and processing time. The `--memory-limit-mb` option governs pair-file buffering, **not** a hard limit on the process's total memory. A matching, completed pair-generation workspace can be reused, and finished segment outputs can be skipped when resuming. Preserve the workspace until output validation is complete; omit `--cleanup` if you intend to retain it.

**Important:** `--verify-output` is for comparing against an **existing reference CSV** for the same bound; it is not a destination for a verification report. Do not specify a nonexistent file there.

See `python archive/v0.7.2/segmented_search.py --help` for all options. The historical v0.7.3 optimization trial was slower and was **not accepted** as a release; v0.7.2 remains stable.

### Independently validate and update the catalog

Historical example: validate a 100M output against a prior 50M catalog:

```powershell
python tools/audits/validate_bricks.py `
  --input bricks_100m.csv `
  --max-edge 100000000 `
  --subset data/verified_euler_bricks.csv `
  --subset-max-edge 50000000
```

The subset bound above illustrates a **historical 50M-to-100M upgrade**. The current verified catalog is now at 20B; do not rerun this historical upgrade against the current catalog. For future updates, use the actual catalog bound recorded in `data/verified_manifest.json`. The validator checks sorted positive edges, bound, primitivity, all three integer face diagonals, uniqueness, and any supplied CSV metadata (including the space-diagonal tests and normalized gap).

Historical example only (do not run against the current 20B catalog):

```powershell
python tools/catalog/update_verified_catalog.py `
  --input bricks_100m.csv `
  --max-edge 100000000 `
  --catalog data/verified_euler_bricks.csv `
  --manifest data/verified_manifest.json
```

The updater independently checks every incoming triple, validates the existing catalog against its manifest and SHA-256 checksum, rejects a decreasing bound, and requires the incoming set to include **all** previously cataloged bricks. It then writes a canonical, deduplicated catalog and updated manifest. It does **not** silently repair a missing old result by taking a union.

Validate the current 20B catalog:

```powershell
python tools/audits/validate_bricks.py `
  --input data/verified_euler_bricks.csv `
  --max-edge 20000000000
```

The confirmed historical 2B result was `rows=6023; unique=6023; perfect=0` and `VALIDATION PASSED`. The former 1B catalog contained 4,631 rows. The updater's two-file replacement is not a single atomic transaction; if interrupted, its checksum check can detect an inconsistent catalog/manifest pair on a subsequent run.

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

The scripts require no third-party Python packages. Use `python src/pso_search.py --help` and `python src/aco_search.py --help` for full parameter descriptions. The committed `experiments/metaheuristics/aco/` and `experiments/metaheuristics/pso/` CSVs contain per-run metrics and candidate data. Execution times depend on the machine.

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

The promoted main accelerated engine `src/odd_leg_numba.py` (algorithm version v0.10.4) fuses compatible-even-leg generation, modulo-3 partitioning, primitivity checks, and the remaining face-diagonal square test into Numba-compiled kernels. It imports the **unchanged** stable v0.9.9 source for SPF construction, candidate verification, and reference loading. It requires **NumPy** and **Numba** (tested with Python 3.11.1 64-bit and Numba 0.68.0); the stable v0.9.9 engine remains standard-library-only. The v0.10.0–v0.10.3 prototypes are preserved in `archive/`.

The v0.10.4 source is the renamed, numerically hardened `v0.10.3-safe` variant. After the completed 500M run, the identical source was promoted to `src/odd_leg_numba.py`; its versioned original was preserved in `archive/v0.10.4/odd_leg_numba_v0104.py`. This was a file-organization change only, with no changes to the search algorithm. A post-promotion 1M regression test passed. Its complete runs were executed under the `v0.10.3-safe` display label before the version-string-only rename. A post-rename smoke test at 1M found 242 bricks and reported `EXACT SET MATCH`; no algorithmic changes were made by the rename.

| Maximum edge | Primitive bricks | Primitive candidate pairs | Perfect cuboids | v0.10.4 elapsed | Reference comparison |
|---:|---:|---:|---:|---:|---|
| 1,000,000 | 242 | 2,169,432 | 0 | 2.335 s (post-rename smoke test) | EXACT SET MATCH |
| 10,000,000 | 704 | 33,697,155 | 0 | 14.288 s | EXACT SET MATCH |
| 50,000,000 | 1,395 | 223,212,641 | 0 | 73.879 s | EXACT SET MATCH |
| 100,000,000 | 1,884 | 501,018,824 | 0 | 158.897 s | EXACT SET MATCH |
| 200,000,000 | **2,509** | **1,121,177,836** | **0** | **544.830 s** | **EXACT SET MATCH** |
| 500,000,000 | **3,556** | **3,237,540,952** | **0** | **979.899 s** | Independent row validation; 200M subset preserved |
| 1,000,000,000 | **4,631** | **7,198,444,485** | **0** | **1,833.040 s** | Independent row validation; 500M subset preserved; published count agrees |

These are recorded individual run times, not a controlled benchmark of v0.10.4. The 1M smoke-test time includes initial Numba compilation; the 10M–200M runs were performed before the display-label rename. The 500M and 1B runs used the released v0.10.4 label. At 200M, the fused kernel processed 100,000,000 odd values, and the SPF sieve took 38.595 s. The historical comparisons used the corresponding bounded reference sets; since the accelerated engine shares the odd-leg construction with v0.9.9, this is **regression evidence, not an independent enumeration-completeness proof**.

A controlled **three-cycle interleaved 10M benchmark** compared stable v0.9.9 with the earlier *original* v0.10.3 (not v0.10.4). The stable median was **55.066 s** and the original v0.10.3 median was **13.076 s**, a **4.21×** ratio. Do not attribute this controlled figure to v0.10.4. A separately recorded v0.10.4 run at 200M took 544.830 s versus an earlier v0.9.9 run of 2,015.158 s (3.70× ratio, **not** a controlled paired benchmark).

### Extended Numba search through 500M

On 2026-10-19 (UTC), experimental v0.10.4 completed a bounded search with maximum edge **500,000,000**. It found **3,556 distinct primitive Euler bricks**, **1,047 more** than the previous 200M catalog, and **zero perfect cuboids**.

| v0.10.4 metric | 500M |
|---|---:|
| Primitive candidate pairs | 3,237,540,952 |
| Rejected nonprimitive pairs | 4,346,788,291 |
| Odd-value kernel calls | 250,000,000 |
| SPF sieve time | 99.450 s |
| Numba compilation time | 1.127 s |
| Search time | 879.310 s |
| Fused kernel time (within search) | 807.922 s |
| Total elapsed (including compilation) | **979.899 s** |
| Primitive Euler bricks | **3,556** |
| Perfect cuboids | **0** |

The independent exact-arithmetic CSV validator reported `rows=3556; unique=3556; perfect=0` and `VALIDATION PASSED`. A subset check against the previous 200M catalog reported `rows=2509; unique=2509; missing=0`. After the guarded catalog update, `data/verified_euler_bricks.csv` was validated again with `rows=3556; unique=3556; perfect=0` and `VALIDATION PASSED`. The manifest records the 500M bound, row count, SHA-256 digest, source file, and verification limitation. The raw output `odd_leg_numba_104_500m.csv` is a local generated artifact, not part of the committed canonical catalog.

**Evidence boundary:** the segmented and stable odd-leg enumerators independently agreed through 100M. At 200M, stable v0.9.9 and experimental v0.10.4 agreed on the exact set. The 500M extension comes from the Numba odd-leg implementation; every reported row passed independent arithmetic validation and all previously cataloged 200M rows were preserved. These algorithm-internal checks do **not** independently prove enumeration completeness at 500M. Subsequently, an exact-set comparison against Giovanni Resta's published OEIS table independently corroborated all 3,556 triples for largest edge strictly below 500M (see below). The absence of a perfect cuboid in this finite run is not a proof of global nonexistence.

To reproduce the 500M search from the repository root in PowerShell (requires substantial available RAM):

```powershell
python -u src/odd_leg_numba.py `
  --source src/odd_leg_search.py `
  --max-edge 500000000 `
  --output odd_leg_numba_104_500m.csv `
  --progress-every 10000000
```

Do **not** pass a smaller-bound catalog as `--reference` when attempting to extend beyond its bound: an exact-set comparison would reject valid new rows. Validate the output and preserve the current catalog as a subset before any future update. At 500M, the SPF array alone occupies approximately 2 GB; peak process memory may be higher.

### Extended Numba search through 1B (2026-10-20 UTC)

The unchanged v0.10.4 engine completed a search with inclusive maximum edge **1,000,000,000**, finding **4,631 distinct primitive Euler bricks**, **1,075 additional bricks** beyond 500M, and **zero perfect cuboids**.

| v0.10.4 metric | 1B |
|---|---:|
| Primitive candidate pairs | 7,198,444,485 |
| Rejected nonprimitive pairs | 10,004,896,982 |
| Odd-value kernel calls | 500,000,000 |
| SPF sieve time | 207.534 s |
| Numba compilation time | 0.522 s |
| Search time | 1,624.970 s |
| Fused kernel time (within search) | 1,507.353 s |
| Total elapsed (including compilation) | **1,833.040 s** |
| Primitive Euler bricks | **4,631** |
| Perfect cuboids | **0** |

The independently implemented exact-arithmetic validator reported `rows=4631; unique=4631; perfect=0` and `VALIDATION PASSED`. The 500M backup subset check reported `rows=3556; unique=3556; missing=0`. The guarded catalog updater reported `previous=3556, added=1075, total=4631`; the canonical catalog was then validated again with the same successful results.

The manifest records `searched_max_edge=1000000000`, `brick_count=4631`, `perfect_cuboid_count=0`, source file `odd_leg_numba_104_1b.csv`, and catalog SHA-256:

```text
de0d93fdb306c503572d528cbeb1839b517e2bc9155a4367146c7a86e0491cd3
```

The total of **4,631** agrees with the published 1B count in [OEIS A239618](https://oeis.org/A239618). This is **count-level corroboration only**, not an independent exact-set comparison through 1B. The independently published triple-by-triple comparison remains limited to 500M. Neither row validation nor count agreement alone proves the search implementation complete, and zero perfect cuboids in this finite search does not prove global nonexistence.

Reproduce the 1B search from the repository root in PowerShell (requires 64-bit Python and substantial available RAM; the uint32 SPF buffer alone occupies approximately 3.73 GiB):

```powershell
python -u src/odd_leg_numba.py `
  --source src/odd_leg_search.py `
  --max-edge 1000000000 `
  --output odd_leg_numba_104_1b.csv `
  --progress-every 10000000
```

Validate the raw output against a preserved 500M catalog (not against the current 20B catalog as an unfiltered subset):

```powershell
python tools/audits/validate_bricks.py `
  --input odd_leg_numba_104_1b.csv `
  --max-edge 1000000000 `
  --subset backups/verified_euler_bricks_500m.csv `
  --subset-max-edge 500000000
```

The raw 1B CSV and local backup are workspace artifacts; the canonical committed artifacts are `data/verified_euler_bricks.csv` and `data/verified_manifest.json`. The script writes the output CSV only after the search finishes.

### Reproduce the 200M accelerated regression

From the repository root in PowerShell, after installing compatible NumPy and Numba versions:

```powershell
python src/odd_leg_numba.py `
  --source src/odd_leg_search.py `
  --max-edge 200000000 `
  --output odd_leg_numba_104_200m.csv
```

Expected result: 2,509 primitive bricks and zero perfect cuboids. **Do not use the current 20B catalog as `--reference` for this 200M run:** the reference comparison requires the same bound and will reject the additional catalog rows. To reproduce the historical `EXACT SET MATCH`, use a separately preserved 200M reference CSV. The SPF array alone occupies approximately 800 MB at 200M; total process memory is higher. The program currently restricts `--max-edge` to at most 1,000,000,000 for signed-64-bit arithmetic, and the 1B run completed successfully; adequate available RAM is still required for reproduction.

### Bounded audit of the stable odd-leg engine

`tools/audits/audit_odd_leg.py` checks v0.9.9 compatible legs against direct integer-square tests, tests sampled factorizations and divisors, and compares the complete small-bound result against an independent Pythagorean-pair graph enumerator. It also checks pair accounting and parity/modulo-3 constraints. For example:

```powershell
python tools/audits/audit_odd_leg.py --source src/odd_leg_search.py --max-edge 1000 --samples 150
python tools/audits/audit_odd_leg.py --source src/odd_leg_search.py --max-edge 3000 --samples 150
```

These are finite bounded checks, **not** formal proofs. This audit directly targets v0.9.9, not the Numba kernel. The latter is checked against the reference catalog and by the stable engine's exact candidate verifier.

## Segmented-SPF accelerated odd-leg search (v0.15.0–v0.18.0)

Two accelerated implementations remain **active in parallel**. `src/odd_leg_numba.py` uses a global smallest-prime-factor (SPF) table and prioritizes speed when sufficient RAM is available. `src/odd_leg_numba_segmented.py` uses bounded SPF segments and prioritizes memory efficiency at larger search limits. Neither supersedes the other. The segmented search imports `odd_spf_segment` and `primes_upto` from the active `src/segmented_factorization.py`, **not** from the archived v0.15.0 prototype.

### Development and correctness checks

- **v0.14.0:** profiled the existing Numba search at 10M, including 33,697,155 exact integer-square-root tests; the profiler is archived.
- **v0.14.1:** tested modular square-residue filters. Despite fewer `isqrt` calls, the measured 10M search was slower; this experiment was not promoted and is archived.
- **v0.15.0:** independently tested segmented SPF factorization against the original factorization (exhaustive odd values through 1M, plus samples across 100M). The original prototype is archived.
- **v0.15.1:** integrated segmented SPF with a fused Numba search kernel. Full **EXACT SET MATCH** against the verified catalog at 10M (704 bricks), 100M (1,884 bricks), and 500M (3,556 bricks), with zero missing and zero extra rows. All three bounds reported zero perfect cuboids.
- **v0.15.2:** compared segment sizes of 25,000, 100,000, and 400,000 odd values at 10M (two runs each). Search-time medians were 14.1095 s, 14.265 s, and 14.2275 s respectively, with exact-set agreement in all runs. No meaningful speed advantage was established; the default remains 100,000 odd values.
- **v0.15.3:** measured memory with a process-tree sampler on Windows, using the same 100,000-odd segment size. The memory tool remains active under `tools/benchmarks/measure_memory.py`. Completed global-SPF versus segmented-SPF measurements now cover 10M, 100M, and 500M.
- **v0.16.0 (2026-10-20, historical):** uses the smallest prime factor from the segment immediately when factoring each odd value, avoiding redundant trial division by smaller primes. Exact-set regression succeeded at 10M (704 bricks), 100M (1,884), and twice at 500M (3,556). All runs found zero perfect cuboids and matched the catalog with zero missing/extra rows. The 500M candidate counters were identical to v0.15.1. A Windows process-tree memory measurement also completed successfully. The tested prototype was promoted to the active source at the time; its final version is now preserved in `archive/v0.16.0/`.

### Recorded segmented-SPF results

| Bound | Primitive bricks | Exact-set comparison | Search time | Segment construction | Segments | Perfect cuboids |
|---:|---:|---|---:|---:|---:|---:|
| 10M | 704 | EXACT SET MATCH | 14.294 s | — | 50 | 0 |
| 100M | 1,884 | EXACT SET MATCH | 250.145 s | 14.983 s | 500 | 0 |
| 500M | **3,556** | **EXACT SET MATCH** | **1,787.602 s** | 90.309 s | 2,500 | **0** |

### v0.16.0 first-factor optimization: recorded regressions and timings

The v0.16.0 measurements below were collected using the pre-promotion prototype from `archive/v0.16.0/odd_leg_numba_segmented_v0160_prototype.py`, with `--segment-odds 100000` and the verified 1B catalog supplied as `--reference` (filtered by bound). The active source is the promoted equivalent; no post-promotion timing is claimed.

| Bound / run | Search time | Fused kernel | Segment construction | Total elapsed | Exact-set comparison |
|---|---:|---:|---:|---:|---|
| 10M | 13.557 s | 11.899 s | 0.785 s | 14.983 s | EXACT SET MATCH (704) |
| 100M | 196.772 s | 175.410 s | 9.524 s | 196.939 s | EXACT SET MATCH (1,884) |
| 500M, first run | 1,165.422 s | 1,037.371 s | 55.276 s | 1,165.708 s | EXACT SET MATCH (3,556) |
| 500M, memory-sampled run | **1,023.019 s** | **916.343 s** | 46.237 s | **1,023.200 s** | **EXACT SET MATCH (3,556)** |

Both 500M pre-promotion runs reported **3,237,540,952 primitive candidate pairs**, **4,346,788,291 rejected nonprimitive pairs**, **2,500 segments**, **249,999,999 kernel calls**, and **zero perfect cuboids**. Segment SPF allocation was at most **400,000 bytes per segment**, excluding overhead; this is **not** total process memory. The second 500M run completed under `tools/benchmarks/measure_memory.py` v0.15.3 with **99.14 MiB sampled peak process-tree RSS**, **99.15 MiB observed Windows peak working set**, 17,870 samples at nominal 50 ms, wrapper wall time **1,023.774 s**, and exit code 0.

Against the earlier v0.15.1 500M run (1,787.602 s search; 99.27 MiB peak RSS), the v0.16.0 memory-sampled run was **42.77% faster by search time** with effectively unchanged sampled peak memory. The two v0.16.0 500M search times themselves differ by approximately **12.2%**, so these are **observational single-run comparisons, not controlled paired benchmarks**. The decrease in segment-construction time cannot be attributed to the first-factor kernel change without further isolation.

**Fastest recorded comparison at 500M:** the global-SPF v0.10.4 memory-sampled run took **956.624 s search**, **1,060.678 s total**, and **3,768.12 MiB peak sampled RSS**. The v0.16.0 memory-sampled run took **1,023.019 s search** (**6.94% slower**; 66.395 s difference), but **1,023.200 s total** (**3.53% faster**; 37.478 s difference), using approximately **38.01× less sampled peak RSS** (about **97.37% less**). This comparison is between separate runs under potentially different system conditions; it is not proof that v0.16.0 is universally faster end-to-end.

To reproduce the promoted active engine from the repository root in PowerShell (the historical timings above were obtained with the pre-promotion prototype):

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -u tools/benchmarks/measure_memory.py -- `
  .\.venv\Scripts\python.exe -u src/odd_leg_numba_segmented.py `
  --source src/odd_leg_search.py `
  --max-edge 500000000 `
  --segment-odds 100000 `
  --reference data/verified_euler_bricks.csv `
  --output odd_leg_segmented_v0160_500m_memory.csv `
  --progress-every 10000000
```

At 100M the fused kernel took 220.712 s and the full program reported 250.313 s including compilation. The segment SPF allocation was at most 400,000 bytes (excluding overhead) with `--segment-odds 100000`. This figure describes the SPF segment buffer **only**, not total process memory. The 100M and 500M results are regression comparisons against the existing verified catalog, not new independent proofs of enumeration completeness. At 500M, the segmented fused kernel took 1,578.106 s over 249,999,999 calls; total program elapsed was 1,787.793 s. Both engines reported exactly 3,237,540,952 primitive candidate pairs and 4,346,788,291 rejected nonprimitive pairs. The global 500M run did not itself request `--reference`; its result count and pair counters matched the segmented run, whose exact-set comparison succeeded.

### Memory measurements (Windows, v0.15.3)

| Engine and bound | Peak sampled process-tree RSS | Observed Windows peak working set | Search time | Total program elapsed |
|---|---:|---:|---:|---:|
| Global SPF, 10M | 134.66 MiB | 137.97 MiB | 11.930 s | 13.837 s |
| Segmented SPF, 10M | 98.14 MiB | 98.23 MiB | 14.294 s | 14.462 s |
| Global SPF, 100M | **730.46 MiB** | 801.08 MiB | **136.639 s** | 156.174 s |
| Segmented SPF, 100M | **98.04 MiB** | 98.52 MiB | 250.145 s | 250.313 s |
| Global SPF, 500M | **3,768.12 MiB** | 3,847.56 MiB | 956.624 s | 1,060.678 s |
| Segmented SPF, 500M | **99.27 MiB** | 99.27 MiB | 1,787.602 s | 1,787.793 s |

At 10M, the segmented run used approximately **27.1% less sampled peak RSS** than the global-SPF run (36.52 MiB less). At 100M, it used **632.42 MiB less sampled peak RSS**, a reduction of approximately **86.6%**; the global-SPF peak sampled RSS was approximately **7.45 times** the segmented-SPF value. The tradeoff was slower execution: segmented search time was 250.145 s versus 136.639 s for global SPF (approximately 83.1% longer). Both 100M runs reported **1,884 primitive Euler bricks**, **zero perfect cuboids**, and `EXACT SET MATCH` against the existing verified catalog, with no missing or extra rows.

At 500M, the segmented run used **3,668.85 MiB less sampled peak RSS**, a **97.37% reduction**; the global peak was approximately **37.96 times** the segmented peak. Segmented search time was approximately **86.9% longer** (1,787.602 s versus 956.624 s, a **1.87×** ratio). The global run reported 103.714 s for its SPF sieve and 878.916 s for its fused kernel; the segmented run reported 90.309 s for segment construction and 1,578.106 s for its fused kernel. These breakdowns identify kernel work as the main *observed timing difference*, but do not isolate its underlying cause. Global memory-wrapper wall time was 1,061.756 s (17,933 samples); segmented wall time was 1,788.437 s (28,186 samples), both at a nominal 50 ms sampling interval. Both exited with code 0.

The global-SPF 100M run reported SPF sieve time 19.372 s, Numba compilation 0.147 s, fused kernel time 127.599 s, 501,018,824 primitive candidate pairs, and 616,535,617 rejected nonprimitive pairs. Its sampler reported 2,753 samples at 50 ms intervals, process-tree peak sampled RSS 730.46 MiB, and an observed process-tree Windows peak working set of 801.08 MiB; the memory-wrapper wall time was 156.744 s (versus the program's 156.174 s total elapsed). The segmented-SPF 100M run reported 500 segments and at most 400,000 bytes allocated for the SPF segment buffer alone (excluding overhead).

These are individual runs, **not controlled repeated timing trials**. The nearly unchanged segmented sampled RSS between 10M and 500M supports the intended bounded-segment memory advantage over the tested range; it **does not prove constant total-memory complexity**. The 50 ms sampler may miss short-lived peaks, and the sum of Windows per-process peak working sets need not represent simultaneous memory use. The observed Windows peak working-set figures should therefore not be interpreted as synchronized process-tree maxima. Exact-set agreement is regression evidence, not a proof of enumeration completeness.

Reproduce a 100M segmented search from the repository root using the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -u src/odd_leg_numba_segmented.py `
  --source src/odd_leg_search.py `
  --max-edge 100000000 `
  --segment-odds 100000 `
  --reference data/verified_euler_bricks.csv `
  --output odd_leg_segmented_100m.csv
```

The reference comparison filters the verified catalog to the requested bound. For a memory-sampled run, use the active wrapper:

```powershell
.\.venv\Scripts\python.exe -u tools/benchmarks/measure_memory.py -- `
  .\.venv\Scripts\python.exe -u src/odd_leg_numba_segmented.py `
  --source src/odd_leg_search.py `
  --max-edge 100000000 `
  --segment-odds 100000 `
  --reference data/verified_euler_bricks.csv `
  --output odd_leg_segmented_100m.csv
```

To reproduce the global-SPF 100M memory measurement with the same wrapper:

```powershell
.\.venv\Scripts\python.exe -u tools/benchmarks/measure_memory.py -- `
  .\.venv\Scripts\python.exe -u src/odd_leg_numba.py `
  --source src/odd_leg_search.py `
  --max-edge 100000000 `
  --reference data/verified_euler_bricks.csv `
  --output odd_leg_original_0153_100m.csv
```

Reproduce the 500M comparison with process-tree memory sampling (run sequentially, not concurrently):

```powershell
.\.venv\Scripts\python.exe -u tools/benchmarks/measure_memory.py -- `
  .\.venv\Scripts\python.exe -u src/odd_leg_numba.py `
  --source src/odd_leg_search.py `
  --max-edge 500000000 `
  --output odd_leg_global_500m.csv `
  --progress-every 10000000

.\.venv\Scripts\python.exe -u tools/benchmarks/measure_memory.py -- `
  .\.venv\Scripts\python.exe -u src/odd_leg_numba_segmented.py `
  --source src/odd_leg_search.py `
  --max-edge 500000000 `
  --segment-odds 100000 `
  --reference data/verified_euler_bricks.csv `
  --output odd_leg_segmented_500m.csv `
  --progress-every 10000000
```

The global run requires several GiB of RAM. The reference option on the segmented run compares against the 500M subset of the current 20B catalog. The two generated output files are separate local artifacts, not replacements for the canonical catalog.

Use `tools/benchmarks/benchmark_segments.py` for segment-size comparisons. Generated benchmark CSVs and run outputs are local artifacts, separate from the canonical verified catalog. Neither a finite exact-set match nor the absence of perfect cuboids resolves the perfect cuboid problem.

### v0.17.0: audited 2B extension (2026-10-20 UTC)

The promoted v0.17.0 segmented-SPF engine preserves the v0.16.0 enumeration algorithm while raising the signed-64-bit bound to **2,000,000,000**, after targeted numerical audits. Pairwise squared-edge sums remain at most 8e18, below the signed-64-bit maximum; the three-edge space-diagonal test uses Python arbitrary-precision integers. The option `--confirm-2b` is mandatory for bounds above 1B. This audit is specific to 2B and **does not establish safety at 10B**.

| Maximum edge | Primitive bricks | Search time | Total elapsed | Primitive candidate pairs | Rejected nonprimitive | Perfect cuboids |
|---:|---:|---:|---:|---:|---:|---:|
| 10M | 704 | 13.575 s | 14.955 s | 33,697,155 | 35,829,819 | 0 |
| 100M | 1,884 | 156.907 s | 157.072 s | 501,018,824 | 616,535,617 | 0 |
| 500M | 3,556 | 1,376.382 s | 1,376.547 s | 3,237,540,952 | 4,346,788,291 | 0 |
| **2B** | **6,023** | **6,423.759 s** | **6,423.927 s** | **15,965,415,902** | **22,935,147,525** | **0** |

The 10M, 100M and 500M v0.17.0 prototype runs returned `EXACT SET MATCH` against the existing catalog subsets, with no missing or extra triples. The 2B run used 10,000 SPF segments, 999,999,999 kernel calls, 303.454 s segment construction, and 5,758.004 s fused kernel time. Its SPF **segment allocation** was at most 400,000 bytes per segment (excluding overhead); **total process memory was not independently sampled for v0.17.0**. The earlier v0.16.0 sampled 500M peak was 99.14 MiB; it must not be reported as a v0.17.0 measurement. The v0.17.0 500M time was slower than the previously recorded v0.16.0 run, but these are not controlled paired benchmarks.

The existing `tools/audits/validate_bricks.py` returned `INPUT: ... rows=6023; unique=6023; perfect=0`, `SUBSET: ... rows=4631; unique=4631; missing=0`, and `VALIDATION PASSED` for the 2B output against the 1B catalog. The 2B output has 4,631 rows at or below 1B, so the old and new 1B subsets agree exactly (no missing and no extra). The new interval (1B, 2B] contributes **1,392** primitive bricks. A post-promotion 10M CSV is present in the local test inventory; its console regression outcome should be confirmed separately before claiming a post-promotion `EXACT SET MATCH`. Row-level arithmetic validity and preservation of the old catalog are established; independent complete enumeration of all triples through 2B has **not** been established. No perfect cuboid was found within this finite bound; this does not prove global nonexistence.

Reproduce the extended search from the repository root:

```powershell
python -u src/odd_leg_numba_segmented.py `
  --max-edge 2000000000 `
  --confirm-2b `
  --source src/odd_leg_search.py `
  --progress-every 50000000 `
  --output local_results/v0.17.0/v0170_test_2b.csv
```

Validate a newly generated 2B output against a **preserved 1B backup** (not the updated 2B catalog):

```powershell
python tools/audits/validate_bricks.py `
  --input local_results/v0.17.0/v0170_test_2b.csv `
  --max-edge 2000000000 `
  --subset backups/verified_euler_bricks_1b.csv `
  --subset-max-edge 1000000000
```

The catalog and manifest **were updated and validated**: previous=4,631, added=1,392, total=6,023; perfect cuboids=0. The canonical catalog SHA-256 reported by the updater is `e06394157055c226ff0074dbb246b9888a34b1293c5c284673fe14ecd33d42ab`. The former 1B catalog and manifest were preserved in local `backups/`. The 2B result is a validated bounded computational search, not a formal completeness proof.

### v0.18.0: segment-level Numba dispatch (2026-10-21)

The active v0.18.0 engine keeps the v0.17.0 odd-leg factorization, modulo-3 partition, primitivity filtering, and exact square tests. The main optimization moves the iteration over odd values into a Numba-compiled **segment-level wrapper** (`fused_segment_kernel`), reducing Python-to-Numba calls from one per odd value to one per SPF segment in normal search mode. The default segment size remains **100,000 odd values**. The optional `--progress-every` mode retains the historical per-odd dispatch and progress output; its timing and kernel-call counts are **not comparable** to the optimized default mode.

The v0.17.0 signed-64-bit safety audit still defines the supported upper bound: **2,000,000,000**, with `--confirm-2b` required above 1B. v0.18.0 does not extend that bound. The source is maintained at `src/odd_leg_numba_segmented.py`, with a byte-identical archived copy at `archive/v0.18.0/odd_leg_numba_segmented.py` (SHA-256 equality checked during promotion). The prior v0.17.0 source remains archived.

#### Recorded results and comparison with v0.17.0

| Maximum edge | Primitive bricks | v0.17.0 search | v0.18.0 search | Search-time reduction | v0.18.0 total elapsed | Exact-set comparison |
|---:|---:|---:|---:|---:|---:|---|
| 10M | 704 | 13.575 s | **9.300 s** | **31.5%** | 10.981 s | EXACT SET MATCH |
| 100M | 1,884 | 156.907 s | **118.065 s*** | **24.8%*** | — | EXACT SET MATCH |
| 500M | 3,556 | 1,376.382 s | **703.406 s** | **48.9%** | 703.573 s | EXACT SET MATCH |
| **2B** | **6,023** | **6,423.759 s** | **3,373.770 s** | **47.5%** | **3,374.145 s** | **EXACT SET MATCH** |

*At 100M, the v0.18.0 search figure is the arithmetic mean of three repeated/profiled runs (116.129 s, 115.855 s, and 122.210 s), excluding an earlier 176.057 s run that showed substantial timing variability. That outlying run also passed exact-set regression. The 100M comparison is therefore a descriptive, non-paired measurement rather than a controlled speedup estimate. Other comparisons are recorded runs under potentially differing system loads. The 10M final-regression total includes 1.665 s Numba compilation; the 500M and 2B totals include cached compilation.*

At **2B**, the completed v0.18.0 run reported **15,965,415,902 primitive candidate pairs**, **22,935,147,525 rejected nonprimitive pairs**, **10,000 segments**, **10,000 fused segment-kernel calls**, **210.666 s SPF segment construction**, and **3,162.985 s fused kernel time**. It found **zero perfect cuboids**. The reference comparison against the canonical 2B catalog reported `REFERENCE expected=6023 missing=0 extra=0` and `EXACT SET MATCH`. The same candidate-pair and rejection counters were recorded in v0.17.0. At 500M, the counters were 3,237,540,952 and 4,346,788,291, respectively, also with exact-set agreement.

The final 10M regression after removing temporary profiling reported **704 bricks**, **33,697,155 primitive candidate pairs**, **35,829,819 rejected nonprimitive pairs**, **50 segment-kernel calls**, and `EXACT SET MATCH`. A separate 10,000-edge `--progress-every 1000` smoke test exercised the per-odd progress path, found **19 bricks** and zero perfect cuboids, and completed successfully; this small smoke test did not request a reference comparison. Segment-size experiments at 10M (25,000, 100,000 and 400,000 odd values) showed no meaningful difference in single-run timings, so the default was retained.

**Memory evidence:** at the default segment size, the SPF `uint32` array uses at most **400,000 bytes per segment**, excluding allocation overhead. This is **not a total process-memory bound**: Numba-generated match lists, other arrays, and runtime overhead also consume memory. No instrumented peak RAM measurement was made for v0.18.0 at 2B; the run completed without significant memory problems being observed. Do not transfer the measured v0.16.0 500M peak to v0.18.0.

Reproduce the optimized 2B run from the repository root in PowerShell (this is a long-running search):

```powershell
python -u src/odd_leg_numba_segmented.py `
  --max-edge 2000000000 `
  --confirm-2b `
  --source src/odd_leg_search.py `
  --reference data/verified_euler_bricks.csv `
  --output local_results/v0180_final_2b.csv
```

The `--reference` check compares the generated set with the matching bound-filtered catalog and is a **regression check, not independent proof of complete enumeration**. The canonical catalog and its SHA-256 manifest were **not changed** by the v0.18.0 optimization. No perfect cuboid was found within the tested bound; this is not a proof of nonexistence.

## v0.19.0: bounded completeness audit (documentation phase)

The v0.19.0 research review examines the active segmented-SPF v0.18.0 engine, `src/segmented_factorization.py`, and the stable `src/odd_leg_search.py` v0.9.9. **This is an audit of the existing implementation, not a new search engine, a new catalog, or a claim of formal software verification.** No v0.19.0 source change is required.

The mathematical enumeration argument has three parts:

1. Every primitive Euler brick has exactly one odd edge `o`. The search covers all odd `o` from 3 through the inclusive maximum-edge bound (the value 1 cannot participate in a positive Euler brick).
2. For an integer face diagonal `h` and compatible even edge `e`, `(h-e)(h+e) = o²`. Each positive divisor `d < o` of `o²` yields `e = (o²/d - d)/2`; conversely, every such compatible positive even edge arises from one of these divisors. The code generates divisors using the prime factorization of `o` and retains only `0 < e <= bound`.
3. In a primitive Euler brick exactly two edges are divisible by 3. Thus, when `3 | o`, a valid pair has exactly one even edge divisible by 3; otherwise both even edges must be divisible by 3. The kernel then checks the common GCD and the remaining face diagonal. `verify_brick` independently checks the final triple with exact Python integer arithmetic.

**Signed-64-bit arithmetic, inclusive bound 2B:** for `B = 2,000,000,000`, both `o² <= B² = 4 × 10¹⁸` and `e1² + e2² <= 2B² = 8 × 10¹⁸` fit in signed `int64` (maximum `2⁶³ − 1`). The space-diagonal check is performed in Python arbitrary-precision integers. A conservative divisor-count bound, `τ(o²) <= 3√o` for odd `o`, gives fewer than 67,083 compatible even legs per odd value at 2B. Therefore, even an overestimate of one billion odd values times all `C(67,082, 2)` leg pairs is `2,249,963,821,000,000,000`, below `2⁶³ − 1`. This bounds the candidate/rejection counters as well as the tested pair sums. The existing three-phase v0.17.0 `int64` audit remains the historical implementation-level evidence; this argument does not authorize bounds above 2B.

**Evidence boundary:** the mathematical construction and static code review support completeness of the enumeration *method*, subject to correct implementation. The previously recorded v0.18.0 2B `EXACT SET MATCH` is regression evidence against the existing catalog, not an independent proof that the catalog is exhaustive. A small-bound independent comparison using Pythagorean-pair enumeration and SPF segment sizes 1, 7, and 31 was reported during the v0.19.0 review (19 bricks through 10,000), but its runnable test and raw log are **not part of this repository**; it should not be presented as a committed or independently reproducible test. Full formal verification of Numba behavior, compiler assumptions, and every implementation path remains outside this audit.

No verified catalog, manifest, source file, or archive is changed by this documentation update.

## Experimental 10B checkpointed search: v0.20.0 (2026-10-24)

The experimental `src/odd_leg_numba_1000b_experimental.py` and `src/safe_arithmetic_1000b.py` use overflow-safe arithmetic for edge-square calculations beyond the stable signed-64-bit range. The arithmetic audit reported **6,091 exact square checks**, **12,182 two-word (`u128`) square checks**, and **60 exact compatible-leg-set comparisons** across selected 10B, 100B and 1000B cases. These are *targeted arithmetic checks*, **not** full searches at 100B or 1000B. The v0.20.0 runner's checkpoint/resume and counter-capacity checks were also exercised; checkpoint disk capacity, actual runtime at higher bounds, and full completeness were not established by those audits.

A real Google Colab CPU run completed the **inclusive 10B bound** using `tools/runners/checkpoint_parallel_v0200.py` and the live Google Drive mirror `tools/runners/colab_checkpoint_sync_v0200.py`:

| Recorded 10B metric | Value |
|---|---:|
| Maximum edge | **10,000,000,000** |
| Unique primitive Euler bricks | **10,932** |
| Additional bricks over 2B | **4,909** |
| Primitive candidate pairs tested | **100,581,596,185** |
| Nonprimitive candidate pairs rejected | **155,208,132,880** |
| SPF segments | **50,000** |
| Durable checkpoint chunks | **5,000 / 5,000** |
| Parallel CPU workers | **2** |
| Segment size / segments per chunk | **100,000 / 10** |
| Final resumed run | `resumed=5000 pending=0` |
| Runner verification | `PASS BRICKS VERIFIED (NO CATALOG)` |
| Drive verification | `PASS DURABLE MIRROR bricks=10932 chunks=5000` |

The reported `wall_this_run=9732.953s` refers to the last substantial Colab invocation (**2,191 new chunks**), **not** to the aggregate time of all sessions. The subsequent all-resumed check took 0.027s and performed no new enumeration. No full independent triple-by-triple external comparison at 10B is claimed.

### 10B CSV integrity and validation

The Colab checkpoint reconstruction created `euler_bricks_10b_verified_candidate.csv` (327,118 bytes), with SHA-256:

```text
67e0a37f71041dc2b1e6d2c6ab65998b705f828001b42b8144890f2d97b376a5
```

The locally downloaded CSV matched that digest. An independent exact-set check normalized `(a,b,c)` triples and compared the **entire old 2B set** against the new 10B subset with `c <= 2,000,000,000`: **6,023 versus 6,023; missing=0; extra=0**. Separate Python `math.gcd`/`math.isqrt` validation found **10,932 unique primitive bricks**, three integral face diagonals per row, and all edges `<= 10B`. These checks establish file integrity, continuity with the previous catalog, and arithmetic correctness of every reported triple. They do **not**, by themselves, establish that the enumerator omitted no valid brick.

**Historical 10B catalog:** the promoted 10B CSV had the SHA-256 above. The earlier 2B digest was `e06394157055c226ff0074dbb246b9888a34b1293c5c284673fe14ecd33d42ab`. The canonical catalog has since advanced to 20B; its manifest must be checked against the 20B bound, 14,010 rows, and the 20B SHA-256 recorded below.

### Resume on Google Colab

Run from the repository root with Drive mounted. The following is the **recorded successful configuration**; adapt the Drive mount if necessary. It is a resume command: with all chunks present it completes immediately without recomputing the search.

```bash
python -u tools/runners/colab_checkpoint_sync_v0200.py \
  --max-edge 10000000000 \
  --workers 2 \
  --segment-odds 100000 \
  --chunk-segments 10 \
  --local-dir /content/ebr_10b_v0200 \
  --drive-dir /content/drive/MyDrive/EulerBrickResearch/checkpoints_10b_v0200 \
  --confirm-10b \
  --experimental-no-reference \
  --progress-seconds 30 \
  --sync-seconds 2
```

The runner writes to the VM disk, restores durable chunks from Drive on startup, and mirrors new sealed checkpoints to Drive during execution. Keep the same search parameters and source/checkpoint identity when resuming; preserve the original Drive directory. `--experimental-no-reference` means the 10B result was **not** compared with a pre-existing full 10B reference set. The checkpoint files were needed to reconstruct the CSV because the original run did not separately publish a final CSV. Downloading a Drive *folder* as ZIP was observed to omit files; reconstructing one checked CSV on Colab and downloading that single file avoided the incomplete-folder transfer.

The stable `src/odd_leg_numba_segmented.py` remains capped at 2B; do not apply this 10B command to the stable v0.18.0 engine. Neither 100B nor 1000B has been fully searched.

## Experimental 20B checkpointed search: v0.21.0 (2026-10-25)

The v0.21.0 experimental runner (`tools/runners/checkpoint_parallel_v0210.py`) and Google Drive mirror (`tools/runners/colab_checkpoint_sync_v0210.py`) extend the v0.20.0 checkpoint workflow to an inclusive **20B** maximum edge. The arithmetic kernel remains `src/odd_leg_numba_1000b_experimental.py` with `src/safe_arithmetic_1000b.py`; the stable v0.18.0 engine and its audited 2B limit are unchanged. The v0.21.0 runner requires `--confirm-20b --experimental-no-reference` above 10B. Its checkpoint format/source identity is separate from the 10B run.

Before the full run, a 1M regression found **242** bricks with `PASS EXACT SET MATCH`, and a second invocation resumed **1/1** chunks with **0** pending and no recomputation. An arithmetic audit (`tools/audits/audit_arithmetic_1000b.py --src-dir src --random-pairs 10000`) completed with exit code **0** after using a separate Numba cache; its square-check stage reported **30,091** exact-square checks and **60,182** `u128` square checks. A separate Drive test mirrored the 1M result and restored **3** files into an empty VM directory, resuming **1/1** chunks. These are bounded tests, not proof of full implementation correctness.

The complete 20B Google Colab CPU run used **2 workers**, **100,000 odd values per segment**, and **10 segments per chunk**. It began with a deliberately stopped **3-chunk** run and then resumed using the same checkpoint identity. The final log reported:

| Recorded 20B metric | Value |
|---|---:|
| Inclusive maximum edge | **20,000,000,000** |
| Distinct primitive Euler bricks | **14,010** |
| Additional bricks above 10B | **3,078** |
| Primitive candidate pairs tested | **221,421,449,822** |
| Nonprimitive candidate pairs rejected | **351,680,484,640** |
| SPF segments | **100,000** |
| Durable checkpoint chunks | **10,000 / 10,000** |
| Parallel CPU workers | **2** |
| Segment size / segments per chunk | **100,000 / 10** |
| Final invocation | `new=2838; wall_this_run=36854.205s` |
| Runner result | `PASS BRICKS VERIFIED (NO CATALOG)` |
| Drive result | `PASS DURABLE MIRROR bricks=14010 chunks=10000` |

The **36,854.205 s** wall time is for the final invocation, **not** the aggregate wall time across all Colab sessions. `NO CATALOG` means the 20B run had no pre-existing full 20B reference; its reported triples were verified, but no full external 20B set comparison occurred.

### 20B checkpoint reconstruction and exact validation

The completed Drive checkpoint directory is `/content/drive/MyDrive/EulerBrickResearch/checkpoints_20b_v0210`. Reconstruction read all **10,000** sealed chunk JSON files, checked each SHA-256, verified the recorded intervals and aggregate counters, and independently checked every resulting triple for sorted positive edges, `gcd(a,b,c)=1`, and three integral face diagonals using Python `math.isqrt`. The results were **14,010 unique primitive Euler bricks** and the same tested/rejected counters as the final runner log.

The subset with `c <= 10,000,000,000` contained **10,932** triples and matched the entire previous 10B catalog exactly: **missing=0, extra=0**. The interval `(10B, 20B]` contributes **3,078** new triples. This establishes catalog continuity and arithmetic validity of the stored rows; it does **not** independently prove completeness of the search implementation. A separate 20B space-diagonal audit should be recorded before asserting a 20B perfect-cuboid count.

The reconstructed candidate CSV is `euler_bricks_20b_verified_candidate.csv`, **431,960 bytes**, with SHA-256:

```text
a810bbdd6280d5d7e5cc74665bc5b1388e6179abbb5f326f208a736a12bb3a41
```

After byte-identical promotion, `data/verified_euler_bricks.csv` should have the same SHA-256. **Manifest synchronization is a separate step**: `data/verified_manifest.json` must record `searched_max_edge=20000000000`, `brick_count=14010`, and the digest above before the pair is treated as synchronized. Keep the 10B and 20B Drive checkpoints unchanged and outside Git.

### Resume completed 20B checkpoints on Colab

With Google Drive mounted, from `/content/EulerBrickResearch`:

```bash
python -u tools/runners/colab_checkpoint_sync_v0210.py \
  --max-edge 20000000000 \
  --workers 2 \
  --segment-odds 100000 \
  --chunk-segments 10 \
  --local-dir /content/ebr_20b_v0210 \
  --drive-dir /content/drive/MyDrive/EulerBrickResearch/checkpoints_20b_v0210 \
  --src-dir /content/EulerBrickResearch/src \
  --confirm-20b \
  --experimental-no-reference \
  --progress-seconds 30 \
  --sync-seconds 2
```

This is a **resume/verification command**, not a request to repeat the completed search. It must use the same runner, source identity, and segmentation parameters. Do not delete the durable checkpoint directory or rerun the full computation to recreate the CSV.

## Independent published-catalog comparison (500M)

On 2026-10-19 (UTC), the local verified catalog was compared, **triple by triple**, with Giovanni Resta's table linked from [OEIS A031173](https://oeis.org/A031173). The comparison used the **strict** bound `c < 500000000` (largest edge), whereas the search engine accepts an inclusive maximum edge. All 3,556 local rows and all 3,556 reference rows were below the strict bound; hence no boundary discrepancy occurred.

| Exact-set comparison | Result |
|---|---:|
| Local catalog: total / below bound | 3,556 / 3,556 |
| OEIS reference: total / below bound | 3,556 / 3,556 |
| Missing from local catalog | **0** |
| Extra in local catalog | **0** |
| Outcome | **EXACT SET MATCH** |

External reference URL: https://oeis.org/A031173/a031173.txt

SHA-256 of the downloaded reference file:

```text
 e6e7cdd287fd151e9dd7516d1e3c86beb656f22fa9e02de39fdd844240fd3945
```

The external table is **not committed to this repository**. Download it locally using PowerShell (avoids a Python 3.11/Windows certificate-store error observed in the original HTTPS download attempt):

```powershell
New-Item -ItemType Directory -Force references | Out-Null
Invoke-WebRequest `
  -Uri "https://oeis.org/A031173/a031173.txt" `
  -OutFile "references/resta_a031173.txt"
Get-FileHash references/resta_a031173.txt -Algorithm SHA256
```

Compare against the canonical catalog:

```powershell
python tools/audits/compare_oeis_resta.py `
  --input data/verified_euler_bricks.csv `
  --resta-file references/resta_a031173.txt `
  --max-edge 500000000
```

The recorded 500M comparison output was `MISSING_FROM_LOCAL: 0`, `EXTRA_IN_LOCAL: 0`, and `EXACT SET MATCH`. The comparison script filters the current 20B canonical catalog to the strict 500M bound, so the same historical comparison remains reproducible. The checksum identifies the exact external reference snapshot used. This **independently corroborates the catalog against a published enumeration**; it is not a formal proof of completeness of either enumerator or a resolution of the perfect cuboid problem. Keep `references/resta_a031173.txt` excluded from Git (see `.gitignore`).

## Empirical distribution analysis (v0.11.0)

`tools/analysis/analyze_brick_distribution.py` reads the canonical catalog without modifying it and reports cumulative counts, new bricks per million edge units, and local log-log exponents. The historical v0.11.0 analysis through 500M used these counts (the current 20B catalog contains later bounds; the table stops at 1B):

| Largest-edge bound | Cumulative primitive bricks |
|---:|---:|
| 10,000,000 | 704 |
| 20,000,000 | 943 |
| 50,000,000 | 1,395 |
| 100,000,000 | 1,884 |
| 200,000,000 | 2,509 |
| 500,000,000 | 3,556 |
| 1,000,000,000 | **4,631** |

A **historical** descriptive power-law fit to the five cumulative counts from 10M through 200M gave `N(B) ≈ 0.73913352 × B^0.425514`. The held-out prediction at 500M was **3,717.5**, compared with **3,556** observed (relative error **+4.54%**). The final three of twelve logarithmic intervals gave local exponents **0.4069**, **0.3884**, and **0.3878**. The additional 500M–1B interval contains 1,075 new bricks (2.15 per million edge units), with a local log-log exponent of approximately 0.381. The historical fit was **not refitted** on the 1B data. These are finite-range empirical observations, not an established asymptotic law. Cumulative observations are dependent, and a single held-out extrapolation is not an uncertainty estimate.

Reproduce the historical 500M holdout analysis (the current catalog also contains 1B data, but `--predict-at` selects the historical evaluation point):

```powershell
python tools/analysis/analyze_brick_distribution.py `
  --input data/verified_euler_bricks.csv `
  --log-bins 12 `
  --train-max 200000000 `
  --predict-at 500000000
```

## Growth-model comparison and robustness (v0.12.0–v0.12.1)

The read-only analysis scripts `tools/analysis/compare_growth_models.py` (v0.12.0) and `tools/analysis/compare_growth_robustness.py` (v0.12.1) use the canonical **4,631-row catalog through 1B** to compare descriptive models for the cumulative number of primitive Euler bricks with largest edge at most \(B\):

\[
N(B)=CB^\alpha,\qquad
N(B)=CB^\alpha\log B,\qquad
N(B)=CB^\alpha(\log B)^\beta.
\]

The second model fixes the logarithmic exponent to \(\beta=1\); the third estimates \(\beta\) from the training data. Historical holdout tests train on bounds no larger than 50M, 100M, 200M, or 500M and predict counts at larger bounds (100M, 200M, 500M, or 1B). The 200M-trained models are also evaluated at 1B. Neither script changes the catalog.

### Historical holdout forecasts (v0.12.0)

The signed percentage errors below are \(100(\widehat N-N)/N\), so positive values mean overprediction. This initial experiment compared the ordinary power law against the model with a *free* logarithmic exponent, with the lower training cutoff fixed at 1M.

| Training upper bound | Prediction bound | Power-law error | Free-log error |
|---:|---:|---:|---:|
| 50M | 100M | +3.32% | −2.62% |
| 100M | 200M | +4.00% | −1.46% |
| 200M | 500M | +8.12% | +1.23% |
| 200M | 1B | +12.65% | +1.95% |
| 500M | 1B | +8.77% | +0.80% |

Across these five **overlapping** tests, the mean absolute cumulative forecast error was **7.37%** for the power law and **1.61%** for the free-log model. This apparent advantage motivated a sensitivity analysis; it is not an independent statistical validation.

### Training-window sensitivity and interval increments (v0.12.1)

The robustness analysis varies the **lower** training cutoff and compares all three models. `MAE_N` is the mean absolute percentage error in cumulative counts. `MAE_dN` evaluates the predicted number of **new** bricks between the training upper bound and the target bound, calculated as the difference of fitted cumulative predictions, not as a separately fitted interval model.

| Lower training cutoff | Number of tests | Power MAE_N | Fixed-log MAE_N | Free-log MAE_N | Power MAE_dN | Fixed-log MAE_dN | Free-log MAE_dN |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1M | 5 | 7.37% | 5.65% | **1.61%** | 17.09% | 13.11% | **5.05%** |
| 2M | 5 | 5.92% | 4.59% | **1.75%** | 14.27% | 11.06% | **5.63%** |
| 5M | 5 | 3.58% | **2.90%** | 3.45% | 9.92% | **8.08%** | 9.40% |
| 10M | 4 | 4.44% | 3.61% | **3.50%** | 12.06% | 9.91% | **9.58%** |

The **fixed-log model improved on the plain power law for every tested lower cutoff**, for both cumulative and increment errors. The free-log model performed especially well when 1M or 2M observations were included, but was sensitive to the training window. For example, with training ending at 200M, the fitted free-log parameters changed from \(\alpha=0.1918,\beta=4.0658\) (starting at 1M) to \(\alpha=0.4587,\beta=-0.5971\) (starting at 5M). Even the sign of \(\beta\) changed.

For a free-log fit, the local effective slope is

\[
\frac{d\log N(B)}{d\log B}=\alpha+\frac{\beta}{\log B}.
\]

This can describe a decreasing local slope over the measured range without identifying a stable asymptotic exponent. **These results support finite-range descriptive and forecasting utility, not a proven asymptotic law or statistically significant superiority.** Cumulative counts are dependent; the rolling tests share training data and targets; the number of evaluation points is small; and no full independent exact-set verification has been performed at 1B.

Reproduce the analyses from the repository root:

```powershell
python tools/analysis/compare_growth_models.py `
  --input data/verified_euler_bricks.csv `
  --catalog-bound 1000000000 `
  --output growth_model_comparison.csv

python tools/analysis/compare_growth_robustness.py `
  --input data/verified_euler_bricks.csv `
  --catalog-bound 1000000000 `
  --output growth_robustness_0121.csv
```

The generated CSV reports are reproducible local outputs and need not be committed with the scripts. These analyses check input CSV structure and uniqueness but do not replace independent exact-arithmetic row validation or establish completeness.

## Space-diagonal gap analysis (v0.13.0–v0.13.1)

The read-only scripts `tools/analysis/analyze_space_diagonal.py` and `tools/analysis/analyze_space_diagonal_stability.py` examine the **4,631 primitive Euler bricks** in the historical 1B subset of the current 20B catalog. For each triple, let

\[
S=a^2+b^2+c^2,\qquad k=\lfloor\sqrt{S}\rfloor,
\]

and define the exact nearest-square gap and its normalized form by

\[
\Delta=\min(S-k^2,(k+1)^2-S),\qquad
\delta=\frac{\Delta}{2k+1}.
\]

The square comparisons use exact integer arithmetic. The normalized gap is a useful finite-range scale measure, **not** an exact equality to the distance between `sqrt(S)` and the nearest integer. A perfect cuboid would have `Delta = 0`; none occurs in this catalog.

### Whole-catalog findings (v0.13.0)

| Metric | Recorded result |
|---|---:|
| Primitive bricks analyzed | **4,631** |
| Perfect cuboids | **0** |
| Nearest-square gap: minimum / median / maximum | 120 / 65,927,125 / 1,366,004,675 |
| Normalized gap: minimum / median / maximum | 0.00006476 / 0.24678356 / 0.49980462 |

The ten equal-width normalized-gap bins over `[0, 0.5]` contained **506, 462, 463, 449, 471, 485, 432, 444, 454, and 465** bricks, respectively (463.1 per bin under an exactly uniform descriptive benchmark). The smallest normalized gap was recorded for **(37,835, 269,280, 1,244,484)**: `Delta = 165`, normalized gap approximately `0.0000647645`, nearest integer space diagonal `1,273,846`. This is **not** a perfect cuboid.

### Stability across disjoint edge intervals (v0.13.1)

Intervals are defined by `lower < c <= upper` (the first includes all positive `c`). The reference proportion below `delta = 0.05` for a uniform distribution on `[0, 0.5]` is 10%.

| Largest-edge interval | Bricks | Median normalized gap | Mean normalized gap | Fraction with `delta < 0.05` | Descriptive chi-square |
|---|---:|---:|---:|---:|---:|
| (0, 10M] | 704 | 0.23959078 | 0.24255610 | 12.36% | 9.892 |
| (10M, 50M] | 691 | 0.24082981 | 0.24311686 | 11.87% | 7.944 |
| (50M, 100M] | 489 | 0.23020471 | 0.23521187 | 11.45% | 7.299 |
| (100M, 200M] | 625 | 0.24182626 | 0.24970011 | 8.48% | 7.464 |
| (200M, 500M] | 1,047 | 0.25664057 | 0.25139362 | 12.13% | 15.359 |
| (500M, 1B] | 1,075 | 0.25395388 | 0.25156316 | 9.40% | 4.619 |

The distributions are **approximately uniform in a descriptive sense** across the observed finite catalog, without a clear monotonic increase in near-square concentration as the largest edge grows. The chi-square numbers are descriptive diagnostics, **not significance tests**: the catalog is a deterministic arithmetic set, not a sample of independent random observations. Neither apparent uniformity nor a small positive gap establishes existence or nonexistence of a perfect cuboid. As elsewhere, arithmetic validity of the stored rows does not independently prove exhaustive enumeration through 1B.

Reproduce from the repository root in PowerShell:

```powershell
python tools/analysis/analyze_space_diagonal.py `
  --input data/verified_euler_bricks.csv `
  --max-edge 1000000000 `
  --output space_diagonal_analysis_0130.csv

python tools/analysis/analyze_space_diagonal_stability.py `
  --input data/verified_euler_bricks.csv `
  --max-edge 1000000000 `
  --output space_diagonal_stability_0131.csv
```

Both CSV reports are generated outputs and can remain local rather than being committed. These analyses do not modify the canonical catalog or manifest.

## Next research steps

1. **Synchronize 20B metadata:** confirm the canonical CSV SHA-256 `a810bbdd6280d5d7e5cc74665bc5b1388e6179abbb5f326f208a736a12bb3a41`, 14,010 rows, and manifest bound of 20B before committing the catalog/manifest/README together on `main`.
2. **Preserve completed evidence:** retain the 10B (5,000 chunks) and 20B (10,000 chunks) durable Google Drive checkpoints, run logs, candidate CSV digests, and exact prior-subset comparisons. Avoid committing duplicate candidate CSVs or checkpoint directories.
3. **Complete a dedicated 20B space-diagonal check** and record the result without inferring it solely from the runner's face-diagonal validation.
4. **Profile before 50B:** isolate segmented factorization, fused Numba kernel time, multiprocessing overhead, and Drive mirroring; test optimizations separately from the completed v0.21.0 checkpoints. Targeted arithmetic tests through 1000B do not authorize a full 50B, 100B, or 1000B search without further testing.
5. **Strengthen completeness evidence:** seek an independently implemented enumerator or an external full-triple comparison beyond 500M, and audit implementation-level arithmetic, counters, and checkpoint semantics. Preserve v0.18.0 as the stable 2B baseline.

## Reproducibility and integrity

- Verify primitive edges, all three face diagonals, and the space diagonal using exact `gcd` and `isqrt` checks.
- Preserve search bounds, segment settings, source versions, and validation logs for systematic runs.
- Maintain a canonical catalog with a checked manifest and SHA-256 digest; back up the catalog before updating it.
- Record independent reference URLs, checksums, and exact-set comparison results; do not commit the downloaded OEIS table.
- Keep random seeds, evaluation counts, algorithm parameters, and per-run results alongside heuristic candidate CSVs.
- Distinguish **evaluations**, **unique candidates**, **per-run discoveries**, and **globally distinct discoveries**.
- Avoid treating duplicate discoveries or repeated baseline results as independent evidence.
- Preserve stable releases; do not replace a validated systematic engine with an unverified optimization.
- Never interpret absence of a perfect cuboid within a finite bound as a proof of global nonexistence.

## Project links

GitHub: https://github.com/profzivkovic/EulerBrickResearch
