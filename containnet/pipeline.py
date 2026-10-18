"""The full analysis, as functions. scripts/ and the Streamlit app both call these."""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from . import communities as cm
from . import report_plots as rp
from .config import DEFAULTS, RESULTS_DIR
from .data import backbone, build_and_save, load_graph
from .simulation import Draws, arc_probability, build_net, patient_zero_potential, run_ic, summarize
from .strategies import STRATEGY_INFO, Context, budget_curve, build_context, compare_strategies


def save(df: pd.DataFrame, name: str) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RESULTS_DIR / name, index=False)
    print(f"  saved results/{name}")


def step_graph():
    print("[00] Building contact graph")
    return build_and_save()


def step_communities(g=None, d=DEFAULTS):
    print("[01] Community detection + centrality")
    g = g if g is not None else load_graph()
    h = backbone(g, d["backbone_m"])
    table, parts = cm.compare_methods(g, h, d["louvain_runs"], d["cpm_k"])
    save(table, "community_comparison.csv")
    sweep = cm.cpm_sweep(g)
    save(sweep, "cpm_sweep.csv")
    ctx = build_context(g, d["backbone_m"], d["cpm_k"], d["louvain_runs"])
    save(ctx.table, "centrality_scores.csv")
    save(ctx.table[ctx.table.cpm_groups > 1], "overlap_people.csv")
    from .centrality import top_per_community

    save(top_per_community(ctx.table, "strength", 3), "top_people_per_group.csv")
    rp.community_map(g, ctx.h, ctx.louvain, ctx.cpm, ctx.overlap)
    rp.cpm_heatmap(sweep)
    return ctx, table, sweep


def step_baseline(ctx: Context, d=DEFAULTS):
    print("[02] No-intervention baseline (Independent Cascade, Monte Carlo)")
    draws = Draws.make(ctx.net, d["trials"], d["rng_seed"])
    rows = []
    for beta in [0.001, 0.0015, 0.002, 0.003, 0.004, 0.006, 0.008, 0.01, 0.015]:
        s = run_ic(ctx.net, arc_probability(ctx.net, beta), draws, n_seeds=d["n_seeds"])
        r = summarize(s)
        rows.append(dict(beta=beta, mean_infected=r["mean"], ci95=r["ci95"], pct_of_ward=100 * r["mean"] / ctx.net.n,
                         share_of_runs_fizzling=float((s <= 3).mean())))
    base = pd.DataFrame(rows)
    save(base, "baseline_outbreak.csv")
    rp.baseline_plot(base)

    p = arc_probability(ctx.net, d["beta"])
    pz = patient_zero_potential(ctx.net, p)
    pz = ctx.table.merge(pz, on="node")
    save(pz[["node", "person_id", "role", "contacts", "strength", "betweenness", "eigenvector",
             "bridge_score", "outbreak_if_patient_zero"]].sort_values("outbreak_if_patient_zero", ascending=False),
         "patient_zero_potential.csv")
    corr = {c: pz[c].rank().corr(pz["outbreak_if_patient_zero"].rank())
            for c in ["contacts", "strength", "betweenness", "eigenvector", "k_core", "participation", "bridge_score"]}
    corr_df = pd.DataFrame({"measure": list(corr), "spearman_with_simulated_spread": [round(v, 3) for v in corr.values()]}
                           ).sort_values("spearman_with_simulated_spread", ascending=False)
    save(corr_df, "centrality_vs_simulated_spread.csv")
    return base, pz, corr_df


def step_interventions(ctx: Context, d=DEFAULTS):
    print("[03] Intervention comparison")
    p = arc_probability(ctx.net, d["beta"])
    t0 = time.perf_counter()
    comp = compare_strategies(ctx, p, d["budget"], d["trials"], d["n_seeds"], d["rng_seed"], d["random_sets"],
                              include_greedy=True, greedy_trials=500)
    print(f"  compared {len(comp)} strategies in {time.perf_counter() - t0:.1f}s")
    save(comp, "intervention_comparison.csv")
    rp.strategy_bars(comp, f"{d['budget']} people protected, beta={d['beta']}, {d['trials']} paired runs")

    curve = budget_curve(ctx, p, range(0, 16), trials=800, n_seeds=d["n_seeds"], rng_seed=d["rng_seed"])
    save(curve, "budget_curve.csv")
    rp.budget_lines(curve)

    rows = []
    for beta in [0.002, 0.004, 0.01]:
        c = compare_strategies(ctx, arc_probability(ctx.net, beta), d["budget"], 800, d["n_seeds"], d["rng_seed"], 30)
        c["beta"] = beta
        rows.append(c)
    sens = pd.concat(rows)
    save(sens[["beta", "strategy", "label", "mean_infected", "reduction_pct", "reduction_ci"]], "disease_sensitivity.csv")
    return comp, curve, sens


def step_scalability(sizes=(100, 500, 1000, 2500, 5000)):
    print("[04] Scalability on synthetic networks")
    import networkx as nx

    rows = []
    for n in sizes:
        blocks = max(2, n // 60)
        sizes_b = [n // blocks] * blocks
        sizes_b[-1] += n - sum(sizes_b)
        pin, pout = min(0.4, 12 / (n / blocks)), 5 / n
        g = nx.stochastic_block_model(sizes_b, [[pin if i == j else pout for j in range(blocks)] for i in range(blocks)], seed=1)
        g = nx.Graph(g)
        rng = np.random.default_rng(0)
        for u, v in g.edges():
            g[u][v]["weight"] = int(rng.geometric(0.08))
        g = nx.relabel_nodes(g, {v: str(v) for v in g.nodes()})
        t = time.perf_counter(); cm.louvain_best(g, runs=1); t_l = time.perf_counter() - t
        t = time.perf_counter(); nx.betweenness_centrality(g, k=min(100, n), seed=1); t_c = time.perf_counter() - t
        net = build_net(g)
        trials = 200 if n <= 1000 else 60
        t = time.perf_counter(); run_ic(net, arc_probability(net, 0.004), Draws.make(net, trials, 1)); t_s = (time.perf_counter() - t) * (200 / trials)
        rows.append(dict(nodes=n, edges=g.number_of_edges(), louvain_s=round(t_l, 3), centrality_s=round(t_c, 3), ic_s=round(t_s, 3)))
        print(f"  n={n}: {rows[-1]}")
    df = pd.DataFrame(rows)
    save(df, "scalability.csv")
    rp.scalability_plot(df)
    return df


def md_table(df: pd.DataFrame, floatfmt="{:.2f}") -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for i in range(len(df)):
        cells = []
        for c in cols:
            v = df[c].iloc[i]
            if v is None or (isinstance(v, (float, np.floating)) and np.isnan(v)):
                cells.append("")
            elif isinstance(v, (float, np.floating)):
                cells.append(floatfmt.format(v))
            else:
                cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def step_report(ctx, comm_table, comp, corr_df, scal, d=DEFAULTS):
    print("[05] Writing results/REPORT.md")
    c = comp.set_index("strategy")
    best_simple = comp[~comp.strategy.isin(["none", "greedy"])].sort_values("reduction_pct", ascending=False).iloc[0]
    comm_show = comm_table.copy()
    comp_show = comp[["label", "protected", "mean_infected", "ci95", "reduction_pct", "reduction_ci", "gain_over_random_pts"]].round(2)
    comp_show.columns = ["Strategy", "Protected", "Avg infected", "±95% CI", "Fewer infected (%)", "±CI (pts)", "Gain over random (pts)"]
    md = f"""# ContainNet results

Auto-generated by `python scripts/run_all.py`. Do not edit by hand; re-run the pipeline instead.

**Setup.** Hospital ward contact network (SocioPatterns, Lyon 2010): {ctx.net.n} people,
{ctx.g.number_of_edges()} contact pairs. Transmission hazard beta = {d['beta']} per 20-second contact interval,
{d['trials']} paired Monte Carlo runs per strategy, budget = {d['budget']} people protected,
{d['n_seeds']} random patient zero (never someone already protected).

## 1. Community structure: Louvain vs Girvan-Newman vs Clique Percolation

{md_table(comm_show, "{:.3f}")}

CPM on the raw graph merges all {ctx.net.n} people into one community because the ward graph is very dense
({100 * (2 * ctx.g.number_of_edges()) / (ctx.net.n * (ctx.net.n - 1)):.0f}% of all pairs are linked). Keeping each person's
{d['backbone_m']} strongest contacts (the *backbone*) lets CPM find {len(ctx.cpm)} overlapping communities with
{len(ctx.overlap)} people who belong to more than one.

![Community map](figures/community_map.png)

## 2. Outbreak size under each intervention (budget = {d['budget']})

{md_table(comp_show)}

Best practical strategy: **{best_simple.label}** ({best_simple.reduction_pct:.0f}% fewer infections vs. {c.loc['random', 'reduction_pct']:.0f}% for random).
Simulation-optimised benchmark: {c.loc['greedy', 'reduction_pct']:.0f}%.

![Strategies](figures/strategy_comparison.png)
![Budget curve](figures/budget_curve.png)

## 3. Which centrality predicts real spreading power?

Spearman correlation between each measure and the simulated outbreak size when that person is patient zero:

{md_table(corr_df, "{:.3f}")}

## 4. Scalability (synthetic networks)

{md_table(scal, "{:.3f}")}

![Scalability](figures/scalability.png)

## 5. Honest limitations

- One ward, 75 people, 4 days: the *ranking* of strategies is more trustworthy than the exact percentages.
- Weights are aggregated over four days, so timing (who met whom *when*) is ignored.
- CPM is very sensitive to graph density and to k (see `cpm_sweep.csv`); overlap alone is a weak spreader signal.
- Vaccination is modelled as perfect, instant removal.
"""
    (RESULTS_DIR / "REPORT.md").write_text(md, encoding="utf-8")
    print("  saved results/REPORT.md")


def run_all(skip_scalability=False):
    t0 = time.perf_counter()
    g = step_graph()
    ctx, comm_table, sweep = step_communities(g)
    base, pz, corr_df = step_baseline(ctx)
    comp, curve, sens = step_interventions(ctx)
    if skip_scalability:
        p = RESULTS_DIR / "scalability.csv"
        scal = pd.read_csv(p) if p.exists() else pd.DataFrame(columns=["nodes", "edges", "louvain_s", "centrality_s", "ic_s"])
    else:
        scal = step_scalability()
    step_report(ctx, comm_table, comp, corr_df, scal)
    print(f"\nDone in {time.perf_counter() - t0:.0f}s. Outputs are in results/")
