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
