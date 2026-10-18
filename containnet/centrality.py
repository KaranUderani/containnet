"""Per-person importance scores: degree, strength, betweenness, eigenvector, bridge score."""
from __future__ import annotations

import networkx as nx
import pandas as pd

from .communities import labels_from_partition, membership_counts, participation


def centrality_table(g: nx.Graph, louvain: list, cpm_comms: list) -> pd.DataFrame:
    n = g.number_of_nodes()
    # Betweenness needs *distances*, but contact weight is a *closeness*: strong contact = short distance.
    dist_g = nx.Graph()
    for u, v, d in g.edges(data=True):
        dist_g.add_edge(u, v, dist=1.0 / d.get("weight", 1))
    btw = nx.betweenness_centrality(dist_g, weight="dist", normalized=True)
    try:
        eig = nx.eigenvector_centrality(g, weight="weight", max_iter=2000)
    except nx.PowerIterationFailedConvergence:
        eig = {v: 0.0 for v in g}

    lv_lab = labels_from_partition(louvain)
    part = participation(g, lv_lab)
    strength = dict(g.degree(weight="weight"))
    core = nx.core_number(g)
    cpm_mem = membership_counts(cpm_comms)

    df = pd.DataFrame(
        {
            "node": list(g.nodes()),
            "person_id": [g.nodes[v].get("person_id", v) for v in g.nodes()],
            "role": [g.nodes[v].get("status", "UNKNOWN") for v in g.nodes()],
            "contacts": [g.degree(v) for v in g.nodes()],
            "strength": [strength[v] for v in g.nodes()],
            "betweenness": [btw[v] for v in g.nodes()],
            "eigenvector": [eig[v] for v in g.nodes()],
            "k_core": [core[v] for v in g.nodes()],
            "louvain_group": [lv_lab[v] + 1 for v in g.nodes()],
            "participation": [part[v] for v in g.nodes()],
            "cpm_groups": [cpm_mem.get(v, 0) for v in g.nodes()],
        }
    )
    # Bridge score: spreads contact across several groups AND has lots of contact to spread.
    df["bridge_score"] = df["participation"] * (df["strength"] / df["strength"].max())
    df["degree_rank"] = df["contacts"].rank(ascending=False, method="first").astype(int)
    return df.sort_values("betweenness", ascending=False).reset_index(drop=True)


def top_per_community(df: pd.DataFrame, by: str = "contacts", top: int = 3) -> pd.DataFrame:
    """The 'super-spreader candidates' inside each Louvain group."""
    return (
        df.sort_values(by, ascending=False)
        .groupby("louvain_group", sort=True)
        .head(top)
        .sort_values(["louvain_group", by], ascending=[True, False])
        .reset_index(drop=True)
    )
