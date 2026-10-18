# What changed from the Colab version

## Why the old results were weak

| Problem in the Colab version | Effect |
|---|---|
| CPM ran on the raw graph (41% of all pairs linked) | One 75-person community, 0 overlap people, so "CPM bridge" removed **nobody** and showed -0.1% |
| Random baseline was a single fixed draw (`Random(7)`) | One lucky or unlucky pick stood in for "random" |
| Seeds that were protected "never started an outbreak" | A plan that happened to remove one of the 3 fixed seed people got a free win, so results depended on which seeds were drawn |
| Three fixed seed sets, 300 runs, no uncertainty | Differences of 1-2 people could not be told from noise |
| Constant infection probability per contact | Ignored that 8 seconds and 8 minutes of contact are different risks |
| One Python loop per trial | Slow, so the app needed a Run button and few trials |
| Four strategies, one budget | No view of how results change with doses or disease |

## What is new

**Core**
- Weight-aware transmission: `p = 1 - exp(-beta * contact intervals)`.
- Vectorised Independent Cascade: all trials at once with NumPy (about 60 ms for 1,000 runs), checked against a naive loop.
- Common random numbers plus paired 95% intervals for every comparison.
- Patient zero is chosen among unprotected people.
- Backbone sparsification so CPM yields real overlapping groups (5 communities, 9 overlap people).
- Girvan-Newman added (on the backbone), with modularity, contact-kept-inside-groups and agreement with job roles (NMI).
- Nine plans instead of four: random (averaged over 40 draws), degree, betweenness, eigenvector, top hub per group
  (your original proposal), bridge score, CPM overlap, and a greedy simulation-optimised benchmark.
- Budget curve (0 to 15 protected), disease-speed sensitivity, per-person patient-zero potential, and a check of which
  centrality predicts it.
- Scalability test on synthetic networks up to 5,000 people.

**Engineering**
- One package (`containnet/`) instead of copy-pasted logic; scripts and app share the same code.
- Config in one file; fixed seeds so `results/` is reproducible.
- `results/REPORT.md` generated automatically; tests; `.gitignore`; Colab junk (`sample_data`, `cloudflared`, `.config`) removed.

**App**
- Reactive (no Run button), five sections instead of four tabs, a verdict sentence and a 75-person strip as the first thing you see.
- Side-by-side outbreak replay using identical chance events.
- A ranked "protect these people first" list with a CSV download.
