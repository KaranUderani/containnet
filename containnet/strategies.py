"""Intervention strategies: who gets vaccinated / isolated first?

Every strategy is a *ranking* of people. A budget of B people means "take the first B".
That makes the budget curve (outbreak size vs doses available) cheap to compute.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx
import numpy as np
import pandas as pd

from . import communities as cm
from .centrality import centrality_table
from .data import backbone
from .simulation import Draws, Net, build_net, run_ic, summarize

STRATEGY_INFO = {
    "none": ("No intervention", "Nobody is protected. This is the baseline everything is compared to."),
    "random": ("Random people", "Protect randomly chosen people. Averaged over many random draws, not one lucky pick."),
    "degree": ("Most contacts", "Protect the people with the most total contact time (weighted degree)."),
    "betweenness": ("Network chokepoints", "Protect people who sit on the most shortest contact paths (betweenness)."),
    "eigenvector": ("Well-connected hubs", "Protect people connected to other highly connected people (eigenvector)."),
    "community_degree": ("Top hub in every group", "Spread doses across Louvain groups: the busiest person in each group first."),
    "bridge_score": ("Group-linkers (bridge score)", "Protect people whose contact is spread across several Louvain groups."),
    "cpm_bridge": ("Overlap people (CPM)", "Protect people CPM places in 2+ overlapping groups; fall back to bridge score if CPM finds fewer."),
    "greedy": ("Simulation-optimised (benchmark)", "Greedy search that picks, one at a time, the person whose protection helps most in simulation. An approximate ceiling, not a practical plan."),
}
STRATEGY_ORDER = list(STRATEGY_INFO)


@dataclass
class Context:
    """Everything derived from the graph that strategies and the app need."""

    g: nx.Graph
    h: nx.Graph
    net: Net
    louvain: list
    louvain_q: float
    cpm: list
    table: pd.DataFrame
    backbone_m: int
    k: int
    rankings: dict = field(default_factory=dict)

    @property
    def overlap(self) -> list:
        return cm.overlap_nodes(self.cpm)


def build_context(g: nx.Graph, backbone_m: int = 4, k: int = 3, louvain_runs: int = 30) -> Context:
    h = backbone(g, backbone_m)
    lv, q, _ = cm.louvain_best(g, runs=louvain_runs)
    cp, _ = cm.cpm(h, k)
    tab = centrality_table(g, lv, cp)
    ctx = Context(g, h, build_net(g), lv, q, cp, tab, backbone_m, k)
    ctx.rankings = _all_rankings(ctx)
    return ctx


def _by(tab: pd.DataFrame, col: str) -> list:
    return tab.sort_values(col, ascending=False, kind="mergesort")["node"].tolist()


def _all_rankings(ctx: Context) -> dict:
    t = ctx.table
    r = {
        "degree": _by(t, "strength"),
        "betweenness": _by(t, "betweenness"),
        "eigenvector": _by(t, "eigenvector"),
        "bridge_score": _by(t, "bridge_score"),
    }

    # Top hub in each group, round-robin (largest group first), so any budget is spread across groups.
    by_group = {
        gid: grp.sort_values("strength", ascending=False)["node"].tolist()
        for gid, grp in t.groupby("louvain_group")
    }
    order = sorted(by_group, key=lambda gid: -len(by_group[gid]))
    rr, depth = [], 0
    while len(rr) < len(t):
        for gid in order:
            if depth < len(by_group[gid]):
                rr.append(by_group[gid][depth])
        depth += 1
    r["community_degree"] = rr

    # CPM overlap people first (most groups, then betweenness), then pad with bridge score.
    ov = t[t["cpm_groups"] > 1].sort_values(["cpm_groups", "betweenness"], ascending=False)["node"].tolist()
    r["cpm_bridge"] = ov + [n for n in r["bridge_score"] if n not in set(ov)]
    return r


def pick_targets(ctx: Context, key: str, budget: int, n_sets: int = 40, rng_seed: int = 7) -> list[list]:
    """Return a list of target sets (one set for deterministic strategies, many for random)."""
    if key == "none" or budget <= 0:
        return [[]]
    if key == "random":
        rng = np.random.default_rng(rng_seed)
        nodes = ctx.net.nodes
        return [list(rng.choice(nodes, size=min(budget, len(nodes)), replace=False)) for _ in range(n_sets)]
    return [ctx.rankings[key][:budget]]


def evaluate_targets(ctx, p_arc, draws, targets: list[list], n_seeds=1, takeoff_at: int = 10):
    """Per-trial outbreak size (averaged over target sets) and the share of runs that 'take off'."""
    acc = np.zeros(draws.trials)
    take = 0.0
    for t in targets:
        sz = run_ic(ctx.net, p_arc, draws, blocked=t, n_seeds=n_seeds)
        acc += sz
        take += float((sz >= takeoff_at).mean())
    return acc / len(targets), 100.0 * take / len(targets)


def greedy_plan(
    ctx: Context,
    p_arc: np.ndarray,
    budget: int,
    trials: int = 300,
    seed: int = 99,
    n_seeds: int = 1,
    pool: int = 30,
) -> list:
    """Greedy simulation-optimised protection list.

    Uses its own training draws (different from the evaluation draws) so the greedy plan is not
    unfairly tuned to the exact random numbers it is later scored on.
    """
    train = Draws.make(ctx.net, trials, seed)
    t = ctx.table
    cand = list(dict.fromkeys(_by(t, "strength")[:pool] + _by(t, "betweenness")[:pool]))
    chosen: list = []
    for _ in range(min(budget, len(cand))):
        best, best_val = None, np.inf
        for c in cand:
            if c in chosen:
                continue
            v = run_ic(ctx.net, p_arc, train, blocked=chosen + [c], n_seeds=n_seeds).mean()
            if v < best_val:
                best, best_val = c, v
        chosen.append(best)
    return chosen


def compare_strategies(
    ctx: Context,
    p_arc: np.ndarray,
    budget: int,
    trials: int = 1000,
    n_seeds: int = 1,
    rng_seed: int = 2026,
    random_sets: int = 40,
    include_greedy: bool = False,
    greedy_trials: int = 300,
) -> pd.DataFrame:
    """Score every strategy on the same random draws. Returns one row per strategy."""
    draws = Draws.make(ctx.net, trials, rng_seed)
    base = run_ic(ctx.net, p_arc, draws, n_seeds=n_seeds)
    keys = [k for k in STRATEGY_ORDER if k != "greedy"]
    plans = {k: pick_targets(ctx, k, budget, random_sets) for k in keys}
    if include_greedy:
        plans["greedy"] = [greedy_plan(ctx, p_arc, budget, greedy_trials, n_seeds=n_seeds)]
        keys.append("greedy")

    rows = []
    n = ctx.net.n
    for k in keys:
        if k == "none":
            sizes, takeoff = base, 100.0 * float((base >= 10).mean())
        else:
            sizes, takeoff = evaluate_targets(ctx, p_arc, draws, plans[k], n_seeds)
        s = summarize(sizes, base)
        rows.append(
            dict(
                strategy=k,
                label=STRATEGY_INFO[k][0],
                protected=0 if k == "none" else budget,
                mean_infected=s["mean"],
                ci95=s["ci95"],
                reduction_pct=s["reduction_pct"],
                reduction_ci=s["reduction_ci"],
                                people_spared=s["people_spared"],
                attack_rate_pct=100.0 * s["mean"] / n,
                attack_rate_unprotected_pct=100.0 * s["mean"] / (n - (0 if k == "none" else budget)),
                takeoff_pct=takeoff,
                example_targets=",".join(plans[k][0]) if k != "random" else "(40 random sets)",
            )
        )
    df = pd.DataFrame(rows)
    rnd = df.loc[df.strategy == "random", "reduction_pct"].iloc[0]
    df["gain_over_random_pts"] = df["reduction_pct"] - rnd
    df.loc[df.strategy == "none", "gain_over_random_pts"] = np.nan
    return df


def budget_curve(
    ctx: Context,
    p_arc: np.ndarray,
    budgets=range(0, 16),
    trials: int = 600,
    n_seeds: int = 1,
    rng_seed: int = 2026,
    random_sets: int = 20,
    keys=None,
) -> pd.DataFrame:
    """Mean outbreak size as a function of how many people can be protected."""
    draws = Draws.make(ctx.net, trials, rng_seed)
    keys = keys or [k for k in STRATEGY_ORDER if k not in ("none", "greedy")]
    rows = []
    base = run_ic(ctx.net, p_arc, draws, n_seeds=n_seeds)
    for b in budgets:
        for k in keys:
            if b == 0:
                sizes = base
            else:
                sizes, _ = evaluate_targets(ctx, p_arc, draws, pick_targets(ctx, k, b, random_sets), n_seeds)
            s = summarize(sizes, base)
            rows.append(dict(budget=b, strategy=k, mean_infected=s["mean"], ci95=s["ci95"], reduction_pct=s.get("reduction_pct", 0.0)))
    return pd.DataFrame(rows)
