# QOO-157 P2 — source pinned GPMC native search/cache/TD width and max RSS

**Only scientific/structural and memory evidence, not a second performance
benchmark.** After P0 shared signed-SCC quotient and P1 source-pinned
BiPe native statistics, record GPMC native counters on the original vs
**same independently reduced** four weighted CNFs, TD-on and TD-off, all
with GPMC pinned `a1bda348...`, `-mode=1 -prec=38 -vs=1 -cs=4000`.

Native unmodified `Counter::printStats` / `ComponentCache::printStats`
already report `Components`, `Split`, `Cache lookup`, `Cache hit`,
`Cache reduce`, decisions, propagations and conflicts.
When TD-on, GPMC's `-tdout` native tree-decomposition file has header
`s td <bags> <maxBag> <nodes>`; width = maxBag − 1, **actual width
of emitted heuristic decomposition**, not an arbitrary guessed value.
Record actual `FlowCutter`, `skip td`, `ignore td` flags.
GNU `/usr/bin/time -f %M` is permitted **only to collect maximum RSS
in KB**, and does not emit or rank walltime in this workflow.

Use exact original and reduced CNF SHA from science artifact 13331140565.
Each variant must preserve original complex WMC under the prior printed
count-scale screen; GPMC MPFR actual 127-bit, 38 effective digits.
No native solver source patch and no QuPRS dev/main CI changes.
**Official CodSpeed source remains P0 Actions #41846122379**; do not
infer performance causality from cache-hit counts alone. These counters
may help determine if SCC input changes component decomposition and
cache efficiency, or if TD has benefits independent of source EE.


## Native results: 16/16 full-source GPMC component/TD/cache/RSS admitted

**PASS** [Actions #41849175510](https://github.com/PhysicsQoo/QuPRS/actions/runs/41849175510), [artifact #13332049775](https://github.com/PhysicsQoo/QuPRS/actions/runs/41849175510/artifacts/13332049775), measured SHA `1535f0013e31cc19ebe23475c99a9cbc729ca42f`; pinned GPMC binary `b4169bce97c995accfca5ef2246d7283af0ded3370391dec7cd852eb3fcb67ce`. All four cases × original/reduced shared SCC input × TD enabled/disabled = **16/16 printed complex WMC count screens passed** (1e-12 count-scale; not exact internal arithmetic certification). TD-on genuinely ran FlowCutter and was not ignored, and the native TD file was archived. No solver source modifications or performance timing occurred; GNU time emitted **only max RSS KB**.

| Source | TD state | Decisions | Components / splits | Cache lookups / hits / reductions | Propagations | Native TD width | Max RSS KB |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Grover4 EQ | on | **2,508** | 2,509 / 2,329 | 6,397 / 6,381 / 0 | 14,247 | **9** | 15,152 |
| Grover4 EQ | off | 165,683 | 165,684 / 165,377 | 635,578 / 621,083 / 0 | 1,003,681 | n/a | 75,028 |
| QAOA7 genuine NEQ | on | **1,004** | 1,005 / 857 | 2,529 / 2,522 / 0 | 5,268 | **6** | 14,780 |
| QAOA7 genuine NEQ | off | 2,648 | 2,649 / 2,431 | 8,473 / 8,448 / 0 | 15,247 | n/a | 15,236 |
| QPE exact8 EQ | on | **2,765** | 2,766 / 2,444 | 9,239 / 9,234 / 0 | 24,148 | **10** | 15,084 |
| QPE exact8 EQ | off | 4,815 | 4,816 / 4,579 | 12,592 / 12,575 / 0 | 43,433 | n/a | 15,432 |
| QFT16 EQ | on | **66,695** | 66,696 / 66,041 | 136,141 / 133,648 / 0 | 1,275,496 | **15** | 37,504 |
| QFT16 EQ | off | 72,169 | 72,170 / 70,569 | 152,448 / 149,622 / 0 | 1,510,872 | n/a | 38,984 |

**Key identity:** Across **all four sources and both TD flags**, every GPMC native search counter (Components, Split, Cache lookup/hit/reduce, decisions, propagations, conflicts) is **identical for original versus independent signed SCC-reduced source CNFs**. Native FlowCutter TD width is also identical on original vs reduced input: Grover4 9, QAOA7 6, QPEexact8 10, QFT16 15. Peak RSS is modestly different as memory usage is not a deterministic search-work identity. This is strong structural evidence that original GPMC EE internally reaches an equivalent effective search problem to the externally reduced CNF; **not bytewise proof of the internal post-EE formula or heap allocation identity**.

**TD mechanism:** activating TD reduces native decisions by 98.49% on Grover4 (165,683→2,508), by 62.08% on QAOA7 (2,648→1,004), by 42.57% on QPEexact8 (4,815→2,765), and by 7.59% on QFT16 (72,169→66,695). Grover4's max RSS drops from 75,028 to 15,152 KB (roughly 73.3→14.8 MiB), consistent with huge component/search-work reductions. This is structural and memory evidence, **not directly a CodSpeed time ratio**.

Cache lookup/hit ratios are very high (Grover TD-on 6,381/6,397; QFT TD-on 133,648/136,141) and `Cache reduce=0` in all eight distinct source×TD modes. These counters show substantial cache reuse but do not prove its standalone causal time gain, since dynamic cache access is coupled to branching/split behavior; test source-pinned cache-size variants and/or an explicit bounded cache-disabled control with the **same science gate and official CodSpeed** before reporting a distinct cache contribution.

**Critical provenance repair:** prior [run #41849078988](https://github.com/PhysicsQoo/QuPRS/actions/runs/41849078988) wrote TD-on file then read it as if it belonged to TD-off; fixed [commit 1535f001](https://github.com/PhysicsQoo/QuPRS/commit/1535f0013e31cc19ebe23475c99a9cbc729ca42f). Its results **must not** be used; only successful corrected #41849175510 counts. The older P0 **official CodSpeed** [#41846122379](https://github.com/PhysicsQoo/QuPRS/actions/runs/41846122379) remains sole timing evidence for original→reduced, and previous [VS×TD official CodSpeed #41836818679](https://github.com/PhysicsQoo/QuPRS/actions/runs/41836818679) supports QAOA7/QFT16 timing direction. No new hosted-runner time estimates are extracted here.

**Next scoped step:** only if stronger time attribution is needed, try fixed GPMC `-cs` cache-size controls (not a naïve `-cs=0`, as pinned GPMC validates minimum 1 MB) and official same-run CodSpeed, or retain cache contribution as **MECHANISM_SUPPORTED_CAUSAL_SHARE_UNKNOWN**. Ganak pinned 2.8.0 mode6 remains separate precision-qualification owner QOO-98.
