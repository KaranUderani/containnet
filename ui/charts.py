"""Plotly figure builders. All figures share one look: transparent, Atkinson font, no gridline clutter."""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from containnet.config import ROLE_NAMES, STRATEGY_COLORS
from containnet.strategies import STRATEGY_INFO

from .theme import AMBER, FONT_BODY, GROUP_COLORS, INFECTED, INK, MUTED, SOFT, TEAL

ROLE_COLORS = {"NUR": "#0F7B8A", "PAT": "#D98324", "MED": "#3E4A89", "ADM": "#8A5A44", "UNKNOWN": "#8A97A0"}


def _base(fig, height=360, **kw):
    layout = dict(
        height=height,
        margin=dict(l=4, r=4, t=8, b=4),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_BODY, color=INK, size=13),
        colorway=GROUP_COLORS,
    )
    layout.update(kw)  # callers may override margin, legend, etc.
    fig.update_layout(**layout)
    return fig


def network(ctx, pos, groups, height=560, show_legend=True):
    """groups: list of dicts(name, nodes, color, symbol, size, line_color, line_width, labels)."""
    g = ctx.g
    ex, ey = [], []
    for u, v in ctx.h.edges():
        ex += [pos[u][0], pos[v][0], None]
        ey += [pos[u][1], pos[v][1], None]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines", hoverinfo="skip", showlegend=False,
                             line=dict(width=0.8, color="rgba(120,140,148,0.30)")))
    tab = ctx.table.set_index("node")
    for grp in groups:
        nodes = [n for n in grp["nodes"] if n in pos]
        if not nodes:
            continue
        hover = [
            f"<b>Person {n}</b><br>{ROLE_NAMES.get(tab.at[n, 'role'], '')}<br>{int(tab.at[n, 'contacts'])} contacts"
            f"<br>Group {int(tab.at[n, 'louvain_group'])}" for n in nodes
        ]
        fig.add_trace(go.Scatter(
            x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes],
            mode="markers+text" if grp.get("labels") else "markers",
            text=[n for n in nodes] if grp.get("labels") else None,
            textposition="middle center", textfont=dict(size=9, color="white"),
            name=f"{grp['name']} ({len(nodes)})",
            marker=dict(size=grp.get("size", 14), color=grp["color"], symbol=grp.get("symbol", "circle"),
                        line=dict(width=grp.get("line_width", 1.5), color=grp.get("line_color", "white"))),
            hovertext=hover, hoverinfo="text"))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, scaleanchor="x")
    _base(fig, height, showlegend=show_legend,
          legend=dict(orientation="h", yanchor="top", y=-0.01, x=0, font=dict(size=12)))
    return fig


def group_groups(ctx, protected=()):
    """Louvain groups as network groups, with protected people drawn as ink diamonds."""
    prot = set(protected)
    out = []
    for i, c in enumerate(ctx.louvain):
        nodes = [n for n in sorted(c) if n not in prot]
        out.append(dict(name=f"Group {i + 1}", nodes=nodes, color=GROUP_COLORS[i % len(GROUP_COLORS)], size=14))
    if prot:
        out.append(dict(name="Protected", nodes=sorted(prot), color=INK, symbol="diamond", size=19))
    return out


def cpm_groups(ctx):
    from containnet.communities import membership_counts

    mem = membership_counts(ctx.cpm)
    out = []
    for i, c in enumerate(ctx.cpm):
        only = [n for n in sorted(c) if mem[n] == 1]
        out.append(dict(name=f"Group {i + 1}", nodes=only, color=GROUP_COLORS[i % len(GROUP_COLORS)], size=14))
    ov = sorted(ctx.overlap)
    out.append(dict(name="In 2+ groups", nodes=ov, color=AMBER, symbol="diamond", size=24, labels=True, line_width=2))
    none = [n for n in ctx.net.nodes if n not in mem]
    out.append(dict(name="In no tight group", nodes=none, color=MUTED, size=10))
    return out


def outbreak_state(ctx, rounds, upto, protected, seed_nodes):
    """Colour people by whether the infection has reached them by round `upto`."""
    idx = ctx.net.index
    prot, seeds = set(protected), set(seed_nodes)
    inf = [n for n in ctx.net.nodes if 0 <= rounds[idx[n]] <= upto and n not in seeds and n not in prot]
    rest = [n for n in ctx.net.nodes if n not in set(inf) and n not in prot and n not in seeds]
    return [
        dict(name="Not infected", nodes=rest, color=MUTED, size=12),
        dict(name="Infected", nodes=inf, color=INFECTED, size=15),
        dict(name="Patient zero", nodes=sorted(seeds - prot), color="#7A0F1E", symbol="star", size=24),
        dict(name="Protected", nodes=sorted(prot), color=INK, symbol="diamond", size=19),
    ]


def leaderboard(comp, selected: str, height=None):
    d = comp[comp.strategy != "none"].sort_values("reduction_pct")
    colors = [STRATEGY_COLORS.get(k, "#888") if k == selected else "#B7C4C9" for k in d.strategy]
    fig = go.Figure(go.Bar(
        x=d.reduction_pct, y=d.label, orientation="h", marker_color=colors,
        error_x=dict(type="data", array=d.reduction_ci, color="#44575F", thickness=1.2, width=4),
        text=[f"{v:.0f}%" for v in d.reduction_pct], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>%{x:.1f}% fewer infected<extra></extra>"))
    fig.update_xaxes(title="Fewer people infected than with no plan (%)", range=[0, max(100, float(d.reduction_pct.max()) * 1.18)],
                     gridcolor=SOFT, zeroline=False)
    fig.update_yaxes(title=None)
    return _base(fig, height or (60 + 38 * len(d)), margin=dict(l=4, r=40, t=8, b=4))


def budget_curve(curve, selected: str):
    fig = go.Figure()
    for k, grp in curve.groupby("strategy"):
        sel = k == selected
        fig.add_trace(go.Scatter(
            x=grp.budget, y=grp.mean_infected, mode="lines+markers", name=STRATEGY_INFO[k][0],
            line=dict(width=3.4 if sel else 1.6, color=STRATEGY_COLORS.get(k)), marker=dict(size=5 if sel else 3),
            opacity=1 if sel else 0.75,
            hovertemplate="%{x} protected: %{y:.1f} infected<extra>" + STRATEGY_INFO[k][0] + "</extra>"))
    fig.update_xaxes(title="People protected (doses / isolation beds)", gridcolor=SOFT, dtick=2)
    fig.update_yaxes(title="Average people infected", gridcolor=SOFT, rangemode="tozero")
    return _base(fig, 400, legend=dict(font=dict(size=11)))


def cascade_curves(rounds_a, rounds_b, label_a, label_b):
    r = int(max(rounds_a.max(), rounds_b.max()))
    xs = list(range(r + 1))
    ya = [int(((rounds_a >= 0) & (rounds_a <= x)).sum()) for x in xs]
    yb = [int(((rounds_b >= 0) & (rounds_b <= x)).sum()) for x in xs]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=ya, name=label_a, mode="lines+markers", line=dict(color=INFECTED, width=3)))
    fig.add_trace(go.Scatter(x=xs, y=yb, name=label_b, mode="lines+markers", line=dict(color=INK, width=3)))
    fig.update_xaxes(title="Transmission round", gridcolor=SOFT, dtick=1)
    fig.update_yaxes(title="People infected so far", gridcolor=SOFT, rangemode="tozero")
    return _base(fig, 300, legend=dict(orientation="h", y=1.12, x=0))


def role_stack(ctx):
    tab = ctx.table
    groups = sorted(tab.louvain_group.unique())
    fig = go.Figure()
    for role in ["NUR", "PAT", "MED", "ADM"]:
        fig.add_bar(x=[f"Group {g}" for g in groups],
                    y=[int(((tab.louvain_group == g) & (tab.role == role)).sum()) for g in groups],
                    name=ROLE_NAMES[role], marker_color=ROLE_COLORS[role])
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title="People", gridcolor=SOFT)
    return _base(fig, 300, legend=dict(orientation="h", y=1.15, x=0))


def sweep_heatmap(sweep, value="communities", title=""):
    piv = sweep.pivot(index="backbone_m", columns="k", values=value)
    fig = go.Figure(go.Heatmap(
        z=piv.values, x=[f"k = {c}" for c in piv.columns], y=[f"{m} strongest ties" for m in piv.index],
        text=piv.values.astype(int), texttemplate="%{text}", colorscale=[[0, "#EAF3F4"], [1, TEAL]],
        showscale=False, hovertemplate="%{y}, %{x}: %{z}<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    return _base(fig, 300, margin=dict(l=4, r=4, t=26, b=4), title=dict(text=title, font=dict(size=13), x=0))


def potential_bars(df, top=15):
    d = df.sort_values("outbreak_if_patient_zero", ascending=False).head(top).iloc[::-1]
    fig = go.Figure(go.Bar(
        x=d.outbreak_if_patient_zero, y=[f"Person {n}" for n in d.node], orientation="h",
        marker_color=[ROLE_COLORS.get(r, "#888") for r in d.role],
        hovertemplate="%{y}<br>~%{x:.1f} infected if patient zero<extra></extra>"))
    fig.update_xaxes(title="Average outbreak size if this person is patient zero", gridcolor=SOFT)
    return _base(fig, 120 + top * 22)


def correlation_bars(corr_df):
    d = corr_df.sort_values("spearman_with_simulated_spread")
    names = {"strength": "Total contact time", "bridge_score": "Bridge score", "eigenvector": "Eigenvector",
             "contacts": "Number of contacts", "k_core": "k-core", "betweenness": "Betweenness", "participation": "Group-mixing only"}
    fig = go.Figure(go.Bar(
        x=d.spearman_with_simulated_spread, y=[names.get(m, m) for m in d.measure], orientation="h",
        marker_color=[TEAL if v >= 0 else INFECTED for v in d.spearman_with_simulated_spread],
        text=[f"{v:.2f}" for v in d.spearman_with_simulated_spread], textposition="outside", cliponaxis=False))
    fig.update_xaxes(title="Rank correlation with simulated spreading power", range=[-0.4, 1.15], gridcolor=SOFT)
    return _base(fig, 300, margin=dict(l=4, r=30, t=8, b=4))


def scalability(df):
    fig = go.Figure()
    for col, name, color in [("louvain_s", "Louvain", TEAL), ("centrality_s", "Betweenness (sampled)", "#2F5D8A"),
                             ("ic_s", "200 outbreak simulations", INFECTED)]:
        fig.add_trace(go.Scatter(x=df.nodes, y=df[col], mode="lines+markers", name=name, line=dict(color=color, width=3)))
    fig.update_xaxes(title="People in the network", type="log", gridcolor=SOFT)
    fig.update_yaxes(title="Seconds", type="log", gridcolor=SOFT)
    return _base(fig, 320, legend=dict(orientation="h", y=1.15, x=0))


def disease_sensitivity(sens):
    names = {0.002: "Slow spreader", 0.004: "Seasonal flu-like", 0.01: "Fast spreader"}
    fig = go.Figure()
    d = sens[~sens.strategy.isin(["none"])]
    for beta, grp in d.groupby("beta"):
        grp = grp.sort_values("reduction_pct")
        fig.add_trace(go.Bar(x=grp.label, y=grp.reduction_pct, name=names.get(round(beta, 4), str(beta))))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="Fewer people infected (%)", gridcolor=SOFT)
    fig.update_xaxes(tickangle=-25)
    return _base(fig, 380, legend=dict(orientation="h", y=1.12, x=0), margin=dict(l=4, r=4, t=8, b=70))


def size_distribution(base_sizes, plan_sizes, n, bin_w=5):
    """Share of simulated outbreaks ending at each size: no plan vs plan."""
    edges = np.arange(0, n + bin_w + 1, bin_w)
    fig = go.Figure()
    for sizes, name, color in [(base_sizes, "No plan", INFECTED), (plan_sizes, "With plan", INK)]:
        hist, _ = np.histogram(sizes, bins=edges)
        fig.add_trace(go.Bar(x=[f"{int(a)}-{int(a + bin_w - 1)}" for a in edges[:-1]], y=100 * hist / len(sizes),
                             name=name, marker_color=color, opacity=0.8,
                             hovertemplate="%{x} people infected: %{y:.1f}% of outbreaks<extra>" + name + "</extra>"))
    fig.update_layout(barmode="group")
    fig.update_xaxes(title="People infected in one outbreak", tickangle=-45)
    fig.update_yaxes(title="Share of simulated outbreaks (%)", gridcolor=SOFT)
    return _base(fig, 340, legend=dict(orientation="h", y=1.12, x=0))