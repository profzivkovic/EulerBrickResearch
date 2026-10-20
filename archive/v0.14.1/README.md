# Modular-filter experiment v0.14.1–v0.14.2

Status: completed; not adopted.

Bound: 10,000,000
Reference: verified_euler_bricks.csv
Expected primitive Euler bricks: 704

All experimental filter modes passed exact-set regression
(missing=0, extra=0).

## Controlled benchmark (v0.14.2)

Median search times over three runs:

| Mode | Median search time |
|---|---:|
| Original v0.10.4 | 11.672 s |
| Experimental baseline | 13.050 s |
| mod64 | 13.334 s |
| mod256+5 | 13.339 s |

The mod256+5 filter rejected 22,513,898 of 33,697,155
primitive candidate pairs (66.8125%) before integer sqrt.

Conclusion: modular filtering reduced integer-sqrt calls but
did not improve runtime compared with the original v0.10.4.

Decision: retain v0.10.4 unchanged. Do not adopt the filters.
Next direction: segmented factorization.
