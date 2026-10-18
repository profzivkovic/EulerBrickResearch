# EulerBrickResearch

Reproducible, exact-integer research into **Euler bricks** and the **perfect cuboid problem**, using Python's standard library.

**Project status (October 2026):** stable segmented systematic search **v0.7.2**, exercised through a maximum edge of **100,000,000**; stable independent odd-leg search **v0.9.8**, verified through **10,000,000**; completed experimental swarm-optimization phase **v0.8.0–v0.8.2**. The verified catalog contains **1,884 primitive Euler bricks** through 100M.

## Mathematical definitions

An **Euler brick** is a triple of positive integer edges \(a<b<c\) for which all three face diagonals are integers:

\[
\sqrt{a^2+b^2},\quad \sqrt{a^2+c^2},\quad \sqrt{b^2+c^2}\in\mathbb Z.
\]

A brick is **primitive** when \(\gcd(a,b,c)=1\). A **perfect cuboid** is an Euler brick whose space diagonal \(\sqrt{a^2+b^2+c^2}\) is also an integer.

All candidate checks use integer arithmetic, including `math.isqrt`; floating-point square-root comparisons are not used as proofs of integrality.

## Verified results

| Maximum edge | Primitive Euler bricks | Search |
| ---: | ---: | --- |
| 1,000,000 | 242 | Odd-leg v0.9.8; exact catalog match |
| 10,000,000 | 704 | Odd-leg v0.9.8; exact catalog match |
| 20,000,000 | 943 | Segmented search v0.7.2 |
| 50,000,000 | 1,395 | Segmented search v0.7.2 |
| 100,000,000 | **1,884** | Segmented search v0.7.2 |

**No perfect cuboid was found in these bounded searches.** This is not a proof that no perfect cuboid exists.

The canonical catalog is `data/verified_euler_bricks.csv`, with metadata in `data/verified_manifest.json`. Validation and catalog maintenance utilities are in `tools/validate_bricks.py` and `tools/update_verified_catalog.py`.

## Search implementations

### Segmented systematic search — v0.7.2

Source: `src/segmented_search.py`  
Archived release: `archive/v0.7.2/segmented_search.py`

This implementation builds a segmented graph of integer Pythagorean relationships and searches for triples with all three face diagonals integral. It provides the reference bounded catalog through a maximum edge of 100M.

Recorded benchmarks:

| Maximum edge | Primitive bricks | Graph edges | Elapsed |
| ---: | ---: | ---: | ---: |
| 10,000,000 | 704 | 26,809,924 | 109.960 s |
| 20,000,000 | 943 | — | — |
| 50,000,000 | 1,395 | — | — |
| 100,000,000 | 1,884 | 309,224,756 | 2,132.598 s |

### Independent odd-leg search — v0.9.8 (stable)

Source: `src/odd_leg_search.py`  
Archived release: `archive/v0.9.8/odd_leg_search.py`  
Previous stable release: `archive/v0.9.5/odd_leg_search.py`

Every primitive Euler brick has exactly one odd edge \(o\) and two even edges. For each odd edge, the algorithm factors \(o^2\) and enumerates divisor pairs

\[
u v=o^2,\qquad u<o<v,\qquad e=\frac{v-u}{2}.
\]

The resulting compatible even edges are paired and checked for primitiveness and for an integral remaining face diagonal. A smallest-prime-factor (SPF) sieve supports integer factorization.

**Modulo-3 partition:** exactly two edges of a primitive Euler brick are divisible by 3. Thus:

- If `3 | o`, exactly one of the two even edges is divisible by 3.
- If `3 ∤ o`, both even edges are divisible by 3.

This partitions candidate pairs without excluding any primitive Euler brick.

**Improvement in v0.9.8:** bounded **iterative divisor generation** stops extending a partial divisor once it reaches the odd edge. This avoids generating divisors that would later be discarded, while preserving all admissible divisors. The modulo-3 pairing and exact-integer tests remain unchanged.

#### v0.9.8 validation and benchmarks

| Maximum edge | Bricks | Pairs after mod 3 | Primitive candidate pairs / `isqrt` calls | Elapsed |
| ---: | ---: | ---: | ---: | ---: |
| 1,000,000 | 242 | 4,089,066 | 2,169,432 | 4.304 s |
| 10,000,000 | 704 | 69,526,974 | 33,697,155 | 60.250 s (initial run) |

Three additional 10M runs took **59.276 s**, **59.398 s**, and **58.708 s**, averaging **59.127 s**. All runs reported `EXACT SET MATCH` against the verified catalog and found zero perfect cuboids.

For comparison, recorded v0.9.5 timings were **4.726 s** at 1M and **61.853 s** at 10M. The 10M mean of three v0.9.8 repeat runs is approximately **4.41% lower** than the single recorded v0.9.5 timing. This is an indicative comparison, not a controlled paired benchmark.

The v0.9.8 10M search considered **134,138,852** possible pairs, reduced to **69,526,974** by the modulo-3 partition (48.17% reduction), with **33,697,155** primitive candidates tested by `isqrt`.

#### Reproduce odd-leg validation

Run from the repository root:

```powershell
python src/odd_leg_search.py `
  --max-edge 1000000 `
  --reference data/verified_euler_bricks.csv `
  --output odd_leg_1m.csv `
  --progress-every 100000
```

```powershell
python src/odd_leg_search.py `
  --max-edge 10000000 `
  --reference data/verified_euler_bricks.csv `
  --output odd_leg_10m.csv `
  --progress-every 1000000
```

Expected final checks: **242** or **704** primitive Euler bricks, respectively, `missing=0`, `extra=0`, and `EXACT SET MATCH`. Timing depends on hardware and runtime conditions.

## Experimental optimization phase

Versions **v0.8.0–v0.8.2** investigated swarm-based heuristic approaches (including PSO and ACO). These are experimental search strategies, not completeness proofs. The systematic segmented and odd-leg algorithms provide the reproducible bounded-enumeration results.

Unsuccessful intermediate odd-leg optimization experiments are not promoted or archived as stable releases. Version **v0.9.8** supersedes **v0.9.5** as the stable odd-leg implementation.

## Structural observations from the verified catalog

For the 1,884 primitive Euler bricks through 100M:

- All have exactly **two edges divisible by 3**.
- Both even edges are divisible by **4**.
- In **1,393** bricks, both even edges have a nontrivial gcd with the odd edge; in **486**, exactly one does; in **5**, neither does.
- In all cases, the gcd of those two individual gcd values is **1**, consistent with primitiveness.

These catalog observations are distinct from proofs about all Euler bricks. The modulo-3 condition used by the odd-leg algorithm has a mathematical justification independent of the catalog.

## Reproducibility and scope

- Python standard library; no floating-point tolerance tests for integer diagonals.
- Canonical primitive triples satisfy `0 < a < b < c`.
- Compare complete sets of triples against the verified reference, not just counts.
- Keep benchmark outputs, temporary CSV files, and catalog backups out of commits unless deliberately curated.
- A bounded negative search result does **not** resolve the perfect cuboid problem.

## Research directions

Future work may include independent verification, profiling-guided improvements, larger bounded searches, and mathematically justified modular restrictions. Every optimization must preserve completeness within the declared search bound and pass exact catalog comparisons before promotion.
