"""Static matplotlib figures for the written report (the app uses Plotly instead)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

from .communities import community_layout, labels_from_partition
from .config import FIG_DIR, STRATEGY_COLORS
from .strategies import STRATEGY_INFO

GROUP_COLORS = ["#0F7B8A", "#D2691E", "#5B7C99", "#7A6C9D", "#6B8E23", "#B5446E", "#C9A227", "#8A5A44"]
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False})


def _save(fig, name):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / name
    fig.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def community_map(g, h, louvain, cpm_comms, overlap, name="community_map.png"):
    """Left: Louvain groups. Right: CPM overlap people highlighted on the backbone."""
    pos = community_layout(h, louvain)
    lab = labels_from_partition(louvain)
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.4))
    for ax, title in zip(axes, ["Louvain groups (everyone in exactly one)", "CPM overlap people (red diamonds sit in 2+ groups)"]):
        nx.draw_networkx_edges(h, pos, ax=ax, edge_color="#C9D1D6", width=0.7)
        ax.set_title(title, fontsize=11, loc="left")
        ax.axis("off")
    cols = [GROUP_COLORS[lab[n] % len(GROUP_COLORS)] for n in h.nodes()]
    nx.draw_networkx_nodes(h, pos, ax=axes[0], node_color=cols, node_size=130, edgecolors="white", linewidths=1)

    ov = set(overlap)
    covered = {n for c in cpm_comms for n in c}
    rest = [n for n in h.nodes() if n not in ov]
    rc = [GROUP_COLORS[next(i for i, c in enumerate(cpm_comms) if n in c) % len(GROUP_COLORS)] if n in covered else "#D5DADD" for n in rest]
    nx.draw_networkx_nodes(h, pos, nodelist=rest, ax=axes[1], node_color=rc, node_size=110, edgecolors="white", linewidths=1)
    nx.draw_networkx_nodes(h, pos, nodelist=list(ov), ax=axes[1], node_color="#C2185B", node_shape="D", node_size=210, edgecolors="white", linewidths=1.2)
    nx.draw_networkx_labels(h, pos, labels={n: n for n in ov}, ax=axes[1], font_size=6.5, font_color="white")
    fig.tight_layout()
    return _save(fig, name)


def strategy_bars(df, title, name="strategy_comparison.png"):
    d = df.sort_values("mean_infected", ascending=False)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    colors = [STRATEGY_COLORS.get(k, "#555") for k in d.strategy]
    ax.barh(d.label, d.mean_infected, xerr=d.ci95, color=colors, ecolor="#333", capsize=3)
    for y, (m, c, r) in enumerate(zip(d.mean_infected, d.ci95, d.reduction_pct)):
        ax.text(m + c + 0.8, y, f"{m:.1f}  ({r:.0f}% fewer)" if r else f"{m:.1f}", va="center", fontsize=9)
    ax.set_xlabel("Average people infected (95% CI)")
    ax.set_title(title, fontsize=11, loc="left")
    ax.set_xlim(0, d.mean_infected.max() * 1.35)
    return _save(fig, name)


def budget_lines(curve, name="budget_curve.png"):
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    for k, grp in curve.groupby("strategy"):
        ax.plot(grp.budget, grp.mean_infected, marker="o", ms=3.5, lw=2 if k in ("bridge_score", "degree", "cpm_bridge") else 1.2,
                color=STRATEGY_COLORS.get(k), label=STRATEGY_INFO[k][0])
    ax.set_xlabel("People protected (vaccine doses / isolation beds)")
    ax.set_ylabel("Average people infected")
    ax.set_title("Outbreak size vs. resources available", fontsize=11, loc="left")
    ax.legend(fontsize=8, frameon=False)
    return _save(fig, name)


def baseline_plot(df, name="baseline_outbreak.png"):
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.plot(df.beta, df.mean_infected, marker="o", color="#0F7B8A", lw=2)
    ax.fill_between(df.beta, df.mean_infected - df.ci95, df.mean_infected + df.ci95, color="#0F7B8A", alpha=0.18)
    ax.set_xlabel("Transmission hazard per 20-second contact (beta)")
    ax.set_ylabel("Average people infected (no intervention)")
    ax.set_title("No-intervention baseline", fontsize=11, loc="left")
    return _save(fig, name)


def cpm_heatmap(sweep, name="cpm_sweep.png"):
    piv = sweep.pivot(index="backbone_m", columns="k", values="communities")
    fig, ax = plt.subplots(figsize=(5.4, 3.8))
    im = ax.imshow(piv.values, cmap="GnBu", aspect="auto")
    ax.set_xticks(range(len(piv.columns)), [f"k={c}" for c in piv.columns])
    ax.set_yticks(range(len(piv.index)), [f"top {m} ties" for m in piv.index])
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            ax.text(j, i, int(piv.values[i, j]), ha="center", va="center", fontsize=10)
    ax.set_title("CPM communities found\n(1 = everything merged into one blob)", fontsize=10, loc="left")
    fig.colorbar(im, ax=ax, shrink=0.8)
    return _save(fig, name)


def scalability_plot(df, name="scalability.png"):
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for col, lab, c in [("louvain_s", "Louvain", "#0F7B8A"), ("centrality_s", "Betweenness (approx.)", "#2F5D8A"), ("ic_s", "IC simulation (200 runs)", "#C2185B")]:
        ax.plot(df.nodes, df[col], marker="o", label=lab, color=c, lw=2)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Network size (people)"); ax.set_ylabel("Seconds")
    ax.set_title("Does the pipeline scale?", fontsize=11, loc="left")
    ax.legend(frameon=False)
    return _save(fig, name)
