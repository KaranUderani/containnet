"""Community detection: Louvain, Girvan-Newman, Clique Percolation, plus overlap/bridge scores."""
from __future__ import annotations

import time
from collections import Counter

import networkx as nx
import numpy as np
from networkx.algorithms.community import (
    girvan_newman,
    k_clique_communities,
    louvain_communities,
    modularity,
)

Partition = list[set]


def sort_partition(comms) -> Partition:
    return [set(c) for c in sorted(comms, key=lambda c: (-len(c), sorted(c)[0]))]


def louvain_best(g: nx.Graph, runs: int = 30, seed: int = 0, resolution: float = 1.0):
    """Louvain is stochastic, so run it `runs` times and keep the highest-modularity result."""
    t0 = time.perf_counter()
    best, best_q = None, -1.0
    for i in range(runs):
        comms = louvain_communities(g, weight="weight", seed=seed + i, resolution=resolution)
        q = modularity(g, comms, weight="weight")
        if q > best_q:
            best, best_q = comms, q
    return sort_partition(best), best_q, time.perf_counter() - t0


def girvan_newman_best(g: nx.Graph, max_levels: int = 25):
    """Run Girvan-Newman and keep the split with the highest modularity.

    Girvan-Newman recomputes edge betweenness after every removal, so it is O(m^2 n).
    That is why it is only run on the sparsified backbone, never on a large graph.
    """
    t0 = time.perf_counter()
    best, best_q = [set(g.nodes())], -1.0
    for level, comms in enumerate(girvan_newman(g)):
        q = modularity(g, comms, weight="weight")
        if q > best_q:
            best, best_q = [set(c) for c in comms], q
        if level >= max_levels:
            break
    return sort_partition(best), best_q, time.perf_counter() - t0


def cpm(g: nx.Graph, k: int = 3):
    t0 = time.perf_counter()
    comms = list(k_clique_communities(g, k))
    return sort_partition(comms), time.perf_counter() - t0


def membership_counts(comms: Partition) -> dict:
    cnt: Counter = Counter()
    for c in comms:
        cnt.update(c)
    return dict(cnt)


def overlap_nodes(comms: Partition) -> list:
    return [n for n, c in membership_counts(comms).items() if c > 1]


def labels_from_partition(comms: Partition) -> dict:
    """node -> community index (first community wins if overlapping)."""
    lab = {}
    for i, c in enumerate(comms):
        for n in c:
            lab.setdefault(n, i)
    return lab


def community_shares(g: nx.Graph, labels: dict) -> dict:
    """For every node: share of its contact time spent with each community."""
    out = {}
    for n in g:
        tot: Counter = Counter()
        for m, d in g[n].items():
            tot[labels[m]] += d.get("weight", 1)
        s = sum(tot.values()) or 1
        out[n] = {c: v / s for c, v in tot.items()}
    return out


def participation(g: nx.Graph, labels: dict) -> dict:
    """Participation coefficient: 0 = all contact inside one community, ->1 = spread evenly across many."""
    return {n: 1.0 - sum(v * v for v in sh.values()) for n, sh in community_shares(g, labels).items()}


def nmi(a: list, b: list) -> float:
    """Normalised mutual information between two labelings (no sklearn needed)."""
    a, b = np.asarray(a), np.asarray(b)
    n = len(a)
    ua, ub = np.unique(a), np.unique(b)
    pa = np.array([(a == x).mean() for x in ua])
    pb = np.array([(b == y).mean() for y in ub])
    mi = 0.0
    for i, x in enumerate(ua):
        for j, y in enumerate(ub):
            pxy = ((a == x) & (b == y)).sum() / n
            if pxy > 0:
                mi += pxy * np.log(pxy / (pa[i] * pb[j]))
    ha = -(pa * np.log(pa)).sum()
    hb = -(pb * np.log(pb)).sum()
    return float(mi / np.sqrt(ha * hb)) if ha > 0 and hb > 0 else 0.0


def within_fraction(g: nx.Graph, comms: Partition) -> float:
    """Fraction of total contact time that stays inside a community (higher = tighter groups)."""
    lab = labels_from_partition(comms)
    inside = total = 0
    for u, v, d in g.edges(data=True):
        w = d.get("weight", 1)
        total += w
        if lab.get(u) is not None and lab.get(u) == lab.get(v):
            inside += w
    return inside / total if total else 0.0


def compare_methods(g: nx.Graph, h: nx.Graph, louvain_runs: int = 30, k: int = 3) -> tuple:
    """Louvain vs Girvan-Newman vs CPM (raw graph) vs CPM (backbone).

    Returns (table DataFrame, dict of partitions) so callers can reuse the partitions.
    """
    import pandas as pd

    roles = [g.nodes[n].get("status", "UNKNOWN") for n in g.nodes()]
    order = list(g.nodes())

    lv, lv_q, lv_t = louvain_best(g, runs=louvain_runs)
    gn, gn_q, gn_t = girvan_newman_best(h)
    cp_raw, cp_raw_t = cpm(g, k)
    cp_bb, cp_bb_t = cpm(h, k)

    def row(name, graph, comms, q, t, overlapping):
        mem = membership_counts(comms)
        lab = labels_from_partition(comms)
        sizes = [len(c) for c in comms]
        r = {
            "method": name,
            "communities": len(comms),
            "largest": max(sizes) if sizes else 0,
            "avg_size": round(float(np.mean(sizes)), 1) if sizes else 0.0,
            "people_covered": len(mem),
            "people_in_2plus": sum(1 for v in mem.values() if v > 1),
            "modularity": round(q, 3) if q is not None else None,
            "within_group_contact": round(within_fraction(g, comms), 3),
            "nmi_vs_roles": None if overlapping else round(nmi([lab.get(n, -1) for n in order], roles), 3),
            "runtime_s": round(t, 4),
        }
        return r

    rows = [
        row("Louvain (full graph)", g, lv, lv_q, lv_t, False),
        row("Girvan-Newman (backbone)", h, gn, gn_q, gn_t, False),
        row(f"CPM k={k} (full graph)", g, cp_raw, None, cp_raw_t, True),
        row(f"CPM k={k} (backbone)", h, cp_bb, None, cp_bb_t, True),
    ]
    parts = {"louvain": lv, "girvan_newman": gn, "cpm_raw": cp_raw, "cpm_backbone": cp_bb}
    return pd.DataFrame(rows), parts


def cpm_sweep(g: nx.Graph, ms=(3, 4, 5, 6, 8), ks=(3, 4, 5)):
    """How CPM behaves as the backbone gets denser / the clique size k changes."""
    import pandas as pd

    from .data import backbone

    rows = []
    for m in ms:
        h = backbone(g, m)
        for k in ks:
            comms, _ = cpm(h, k)
            mem = membership_counts(comms)
            sizes = sorted((len(c) for c in comms), reverse=True)
            rows.append(
                dict(
                    backbone_m=m,
                    k=k,
                    edges=h.number_of_edges(),
                    communities=len(comms),
                    largest=sizes[0] if sizes else 0,
                    people_covered=len(mem),
                    people_in_2plus=sum(1 for v in mem.values() if v > 1),
                )
            )
    return pd.DataFrame(rows)


def community_layout(h: nx.Graph, louvain: Partition, seed: int = 7, pull: float = 6.0):
    """Spring layout where same-group edges are pulled tighter, so groups show up as visible clusters."""
    lab = labels_from_partition(louvain)
    lg = nx.Graph()
    lg.add_nodes_from(h.nodes())
    for u, v in h.edges():
        lg.add_edge(u, v, w=pull if lab.get(u) == lab.get(v) else 1.0)
    # connect each group's members weakly so isolated backbone fragments stay with their group
    for c in louvain:
        members = sorted(c)
        for a, b in zip(members, members[1:]):
            if not lg.has_edge(a, b):
                lg.add_edge(a, b, w=0.4)
    return nx.spring_layout(lg, seed=seed, weight="w", k=0.9 / np.sqrt(max(len(lg), 1)) * 2.2, iterations=300)
