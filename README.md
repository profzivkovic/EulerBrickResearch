# EulerBrickResearch

Reproducible, exact-integer research into **Euler bricks** and the **perfect cuboid problem**, using Python's standard library.

**Project status:** stable systematic search **v0.7.2**; completed experimental swarm-optimization phase **v0.8.0–v0.8.2**; number-theoretic research phase **v0.9.0 planned, not implemented**.

> **Scientific scope:** A finite search, even one that finds no perfect cuboid, is **not a proof of nonexistence**. Heuristic experiments do not establish completeness. No perfect cuboid has been found in the experiments reported here.

## Mathematical problem

For positive integer edges \(0<a<b<c\), an **Euler brick** has three integer face diagonals:

\[
x^2=a^2+b^2,\qquad y^2=a^2+c^2,\qquad z^2=b^2+c^2.
\]

A brick is **primitive** if \(\gcd(a,b,c)=1\). A **perfect cuboid** is an Euler brick whose space diagonal is also an integer:

\[
d^2=a^2+b^2+c^2.
\]

All final square tests use exact integer arithmetic (`math.isqrt`); floating-point fitness values are used only to guide heuristic searches, not to certify solutions.

## Repository layout

```text
src/
  segmented_search.py        # stable systematic engine, v0.7.2
  pso_search.py              # diversity-preserving PSO, v0.8.1
  aco_search.py              # discrete ACO, v0.8.2
tools/
  validate_bricks.py         # independent catalog validation
data/
  verified_euler_bricks.csv  # verified systematic-search catalog
  verified_manifest.json    # catalog provenance, where present
experiments/
  pso_080_runs.csv
  bricks_pso_080.csv
  pso_081_runs.csv
  bricks_pso_081.csv
  aco_082_runs.csv
  bricks_aco_082.csv
archive/
  v0.7.1/                   # previous systematic engine
```

The tree above describes the relevant project files; some additional utilities may exist. The v0.8.0 PSO **results** are committed, but `src/pso_search.py` is the later v0.8.1 implementation. For full source-level reproduction of v0.8.0, its original script must also be preserved separately (for example, under `archive/v0.8.0/`). Do not treat v0.8.1 as the v0.8.0 source.

## Stable systematic search: v0.7.2

The systematic engine enumerates candidate integer relationships using Pythagorean structure and segmented processing, with exact final verification.

Reported reference run:

| Quantity | Result |
|---|---:|
| Maximum edge bound | 10,000,000 |
| Primitive Euler bricks | **704** |
| Pythagorean graph edges | 26,809,924 |
| Segments processed | 1,000 |
| Total elapsed time | 109.960 s |
| Perfect cuboids found | **0** |

The catalog is stored in `data/verified_euler_bricks.csv`. These numbers describe the recorded run and its search bounds, not an unbounded mathematical theorem. Runtime depends on the machine and environment.

Example command (adjust memory and workspace settings for your machine):

```powershell
python src/segmented_search.py --max-edge 10000000 --segment-size 10000 --memory-limit-mb 32 --output bricks_072_10m.csv
```

Consult `python src/segmented_search.py --help` for all options. Validate any new catalog independently using `tools/validate_bricks.py` and its supported CLI options (`--help`). The historical v0.7.3 optimization trial was slower and was **not accepted** as a release; v0.7.2 remains the stable version.

## Experimental metaheuristics: v0.8.0–v0.8.2

These methods use two Euclidean Pythagorean triples, scaled to share a leg, to construct candidates with **at least two exact integer face diagonals**. The remaining face condition and space diagonal are checked using exact arithmetic. Optimization is heuristic: no completeness or existence/nonexistence guarantee is claimed.

- **v0.8.0:** initial particle swarm optimization (PSO).
- **v0.8.1:** PSO with neighborhoods, stagnation tracking and particle restarts to improve diversity.
- **v0.8.2:** discrete ant colony optimization (ACO) with pheromone reinforcement, evaporation and exploration.
- **RANDOM:** independently seeded random sampling under the same per-run evaluation budget, used as a baseline.

Each experiment used **30 independent runs per method**, `--max-edge 10000000`, `--max-m 120`, and **64,320 candidate evaluations per run** for each method. The baseline is repeated in the three experiment files; it is not three independent sets of random-baseline findings.

### Observed results

| Method | Mean primitive bricks / run | Mean unique candidates / run | Distinct bricks across 30 runs |
|---|---:|---:|---:|
| PSO v0.8.0 | 5.47 | 25,883 | 60 |
| PSO v0.8.1 | 8.10 | 29,052 | 67 |
| ACO v0.8.2 | 5.47 | 19,823 | 42 |
| **RANDOM baseline** | **17.43** | **52,007** | **91** |

These are descriptive results for the tested implementations, parameter settings and search space; they do **not** establish that random search is universally superior to PSO, ACO or other metaheuristics.

All reported Euler-brick rows in the three experimental candidate CSV files were checked against the exact integer conditions in the corresponding experiment review. None was a perfect cuboid. Candidate CSV rows can contain the same brick in different runs; the **distinct bricks** column deduplicates by the triple `(a, b, c)` within each method's 30 runs. Experimental discoveries should not be added to the stable catalog without independent verification and a deliberate catalog-update process.

### Reproduce PSO v0.8.1

```powershell
python src/pso_search.py --runs 30 --max-edge 10000000 --max-m 120 --particles 80 --iterations 200 --stagnation 12 --restart-fraction 0.30 --neighborhoods 5 --seed 42 --output bricks_pso_081.csv --summary-output pso_081_runs.csv
```

### Reproduce ACO v0.8.2

```powershell
python src/aco_search.py --runs 30 --max-edge 10000000 --max-m 120 --ants 80 --iterations 200 --evaporation 0.20 --elite-fraction 0.20 --exploration 0.15 --seed 42 --output bricks_aco_082.csv --summary-output aco_082_runs.csv
```

The scripts require no third-party Python packages. Use `python src/pso_search.py --help` and `python src/aco_search.py --help` for the full parameter descriptions. CSV files contain per-run metrics and exact candidate data; use the committed `experiments/` files for comparison. Execution times are machine-dependent.

### Interpretation and limitations

The tested PSO and ACO configurations revisit many candidates and find fewer Euler bricks than the random baseline. A possible explanation is that the continuous-style fitness signal for near-square diagonals does not reliably predict exact integer solutions. This is a **hypothesis**, not a demonstrated mathematical law.

Finding more Euler bricks is a useful benchmark, but it is **not equivalent** to finding a perfect cuboid. A smaller gap between an integer and a squared diagonal does not imply a nearby exact solution. Any newly proposed fitness function or algorithm must therefore be assessed against the random baseline using exact validation and multiple independent runs.

## Next research phase: v0.9.0 (planned)

The next proposed direction emphasizes mathematics over further routine PSO/ACO parameter tuning:

1. Analyze the structure of the 704 verified primitive Euler bricks and known parameter families.
2. Study exact parametrizations and number-theoretic constraints, including modular restrictions.
3. Develop structured candidate generators that satisfy as many integer-diagonal conditions as possible by construction.
4. Evaluate constraint-solving approaches and compare any new search against the v0.7.2 engine and an equal-budget random baseline.
5. Keep mathematical claims, exhaustive bounded results and heuristic evidence explicitly separate.

This is a research plan, **not** a claim that v0.9.0 has been implemented or that a perfect cuboid exists.

## Reproducibility and integrity

- Use exact `gcd` and `isqrt` checks to verify primitive edges, all three face diagonals and the space diagonal.
- Keep random seeds, evaluation counts, algorithm parameters and per-run results alongside candidate CSVs.
- Distinguish *evaluations*, *unique candidates*, *per-run discoveries* and *globally distinct discoveries*.
- Avoid treating duplicate discoveries or repeated baseline runs as independent evidence.
- Preserve stable releases; do not replace a validated systematic engine with an unverified optimization.
- Treat the absence of a perfect cuboid within any finite bound as a bounded computational observation only.

## Project links

GitHub: <https://github.com/profzivkovic/EulerBrickResearch>
