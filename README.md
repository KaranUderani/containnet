# ContainNet

**Community-aware outbreak containment planning on a real hospital contact network.**

A ward has a few vaccine doses or isolation beds and an infection is about to start. Who should get them first?
ContainNet detects the tight groups in the ward (Louvain, Girvan-Newman, Clique Percolation), scores everyone
(degree, betweenness, eigenvector, bridge score), simulates thousands of outbreaks (Independent Cascade, Monte Carlo)
and measures how much each protection plan shrinks the outbreak.

**Live app:** _add your Streamlit URL here after deploying_

## Headline results

Dataset: SocioPatterns hospital ward (Lyon 2010): 75 people, about 32,000 face-to-face contacts over four days.
Setting: 8 people protected, flu-like spread, 1,000 paired outbreaks per plan. Full tables in
[`results/REPORT.md`](results/REPORT.md).

| Plan | Fewer people infected |
|---|---|
| Random people | 16% |
| CPM overlap people | 29% |
| Top hub in every group (Louvain) | 46% |
| Network chokepoints (betweenness) | 52% |
| Most contact time | 58% |
| **Group-linkers (bridge score)** | **59%** |
| Simulation-optimised benchmark | 59% |

What the experiments show:

- On the full ward graph, CPM merges all 75 people into one community (41% of all pairs were in contact). Keeping each person's
  strongest ties first gives 5 overlapping communities with 9 people in more than one.
- Overlapping membership alone is a weak target: it beats random but loses to simple hubs. The **bridge score** (group-spread
  times contact volume) matches a greedy search over simulations, and picks the same 8 people.
- Total contact time predicts real spreading power almost perfectly (Spearman 0.99), betweenness much less (0.71).

## Run it

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

streamlit run app.py              # the app
python scripts/run_all.py         # regenerate every table, figure and results/REPORT.md (~1 min)
python tests/test_core.py         # sanity tests
```

Step-by-step VS Code, GitHub and Streamlit Cloud instructions: [`docs/GUIDE.md`](docs/GUIDE.md).

## Project layout

```
app.py                  Streamlit app (Plan, Replay, Groups, Evidence, About)
ui/                     theme (CSS), Plotly charts, HTML components
containnet/
  data.py               download + build graph, backbone sparsification
  communities.py        Louvain, Girvan-Newman, CPM, bridge/participation scores, layout
  centrality.py         degree, strength, betweenness, eigenvector, bridge score
  simulation.py         vectorised Independent Cascade (all trials at once, common random numbers)
  strategies.py         9 protection plans, paired comparison, budget curve, greedy benchmark
  pipeline.py           the full analysis as functions
  report_plots.py       static matplotlib figures
scripts/                00_build_graph ... 04_scalability, run_all
results/                CSV tables, figures, REPORT.md (committed so the app works instantly)
data/                   raw zip + cleaned graph
tests/                  pytest-style sanity tests
```

## Method notes

- **Transmission.** Each contact gets one chance to pass the infection with probability `1 - exp(-beta * w)`, where `w` is
  the number of 20-second intervals the two people were together. Longer contact is riskier.
- **Fair comparison.** All plans are scored on the same random numbers (common random numbers), so differences are not
  Monte Carlo noise, and 95% intervals are paired. Patient zero is always someone who is not protected.
- **Greedy benchmark.** Picks people one at a time by simulated benefit, using separate random draws from the evaluation.
- **Validated.** The vectorised simulator matches a plain per-trial Python loop (see `tests/`).

## Limitations

One ward, 75 people, four days: trust the order of the plans more than exact percentages. Contacts are summed over time
(no timing), and protection is perfect and instant.

## Data and credit

Vanhems et al., "Estimating potential infection transmission routes in hospital wards using wearable proximity sensors",
PLoS ONE 8(9): e73970 (2013). Dataset via [Netzschleuder](https://networks.skewed.de/net/sp_hospital).
MIT licence, see `LICENSE`.
