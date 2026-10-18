"""Vectorised Independent Cascade (IC) Monte Carlo.

Your Colab version ran one Python loop per trial. This one simulates *all trials at once*
with NumPy, which is what makes thousands of runs per strategy cheap enough for a live app.

Two ideas make comparisons fair:

1. Live-edge formulation of IC. In IC every directed contact (u->v) gets exactly one
   transmission attempt, so we can pre-draw "did this attempt succeed?" for every contact in
   every trial, then outbreak size = what is reachable from patient zero over successful contacts.

2. Common random numbers. Every strategy is evaluated on the SAME random draws, so
   differences between strategies are not Monte Carlo noise, and we can report paired CIs.

Transmission probability per contact:
   weighted : p = 1 - exp(-beta * w)   w = number of 20 s intervals in contact (longer contact = riskier)
   uniform  : p = beta                 (the classic constant-probability IC, as in your first version)
"""
from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np

from .data import node_order


@dataclass
class Net:
    """Array view of a contact graph (directed arcs sorted by destination for fast reduceat)."""

    nodes: list
    index: dict
    src: np.ndarray
    dst: np.ndarray
    w: np.ndarray
    seg_starts: np.ndarray
    seg_nodes: np.ndarray

    @property
    def n(self) -> int:
        return len(self.nodes)

    @property
    def n_arcs(self) -> int:
        return len(self.src)


def build_net(g: nx.Graph) -> Net:
    nodes = node_order(g)
    index = {v: i for i, v in enumerate(nodes)}
    s, d, w = [], [], []
    for u, v, data in g.edges(data=True):
        wt = data.get("weight", 1)
        s += [index[u], index[v]]
        d += [index[v], index[u]]
        w += [wt, wt]
    s, d, w = np.array(s), np.array(d), np.array(w, dtype=float)
    order = np.argsort(d, kind="stable")
    s, d, w = s[order], d[order], w[order]
    seg_nodes, seg_starts = np.unique(d, return_index=True)
    return Net(nodes, index, s, d, w, seg_starts, seg_nodes)


def arc_probability(net: Net, beta: float, mode: str = "weighted") -> np.ndarray:
    if mode == "uniform":
        return np.full(net.n_arcs, float(beta))
    return 1.0 - np.exp(-beta * net.w)


@dataclass
class Draws:
    """Pre-drawn randomness shared by every strategy (common random numbers)."""

    u_arc: np.ndarray   # trials x arcs
    u_seed: np.ndarray  # trials x nodes

    @classmethod
    def make(cls, net: Net, trials: int, seed: int) -> "Draws":
        rng = np.random.default_rng(seed)
        return cls(
            rng.random((trials, net.n_arcs), dtype=np.float32),
            rng.random((trials, net.n), dtype=np.float32),
        )

    @property
    def trials(self) -> int:
        return self.u_arc.shape[0]


def blocked_mask(net: Net, blocked) -> np.ndarray:
    m = np.zeros(net.n, dtype=bool)
    for b in blocked:
        m[net.index[b]] = True
    return m


def run_ic(
    net: Net,
    p_arc: np.ndarray,
    draws: Draws,
    blocked=(),
    n_seeds: int = 1,
    seeds=None,
    max_rounds: int = 80,
    return_rounds: bool = False,
):
    """Run `draws.trials` outbreaks in parallel.

    blocked : people who are vaccinated/isolated: they cannot be infected or pass infection on.
    seeds   : optional explicit patient-zero node ids (same for every trial). If omitted, each
              trial picks `n_seeds` random people who are NOT blocked (a vaccinated person
              cannot be patient zero).
    Returns outbreak sizes (trials,), and optionally the round each person was infected (-1 = never).
    """
    T, n = draws.trials, net.n
    bm = blocked_mask(net, blocked)

    live = draws.u_arc < p_arc[None, :]
    if bm.any():
        live &= ~(bm[net.src] | bm[net.dst])[None, :]

    infected = np.zeros((T, n), dtype=bool)
    if seeds is not None:
        idx = [net.index[s] for s in seeds if not bm[net.index[s]]]
        if idx:
            infected[:, idx] = True
    else:
        pri = draws.u_seed.copy()
        pri[:, bm] = np.inf
        k = min(n_seeds, int((~bm).sum()))
        pick = np.argpartition(pri, k - 1, axis=1)[:, :k]
        infected[np.arange(T)[:, None], pick] = True

    rounds = None
    if return_rounds:
        rounds = np.full((T, n), -1, dtype=np.int16)
        rounds[infected] = 0

    frontier = infected.copy()
    for r in range(1, max_rounds + 1):
        if not frontier.any():
            break
        act = frontier[:, net.src] & live
        reach = np.zeros((T, n), dtype=bool)
        reach[:, net.seg_nodes] = np.logical_or.reduceat(act, net.seg_starts, axis=1)
        new = reach & ~infected
        if not new.any():
            break
        infected |= new
        if return_rounds:
            rounds[new] = r
        frontier = new

    sizes = infected.sum(axis=1)
    return (sizes, rounds) if return_rounds else sizes


def summarize(sizes: np.ndarray, base_sizes: np.ndarray | None = None) -> dict:
    """Mean outbreak size with a 95% CI; if baseline given, paired % reduction with CI."""
    T = len(sizes)
    mean = float(sizes.mean())
    ci = 1.96 * float(sizes.std(ddof=1)) / np.sqrt(T) if T > 1 else 0.0
    out = {"mean": mean, "ci95": ci}
    if base_sizes is not None:
        b = float(base_sizes.mean())
        diff = base_sizes.astype(float) - sizes.astype(float)
        dci = 1.96 * float(diff.std(ddof=1)) / np.sqrt(T) if T > 1 else 0.0
        out.update(
            reduction_pct=100.0 * float(diff.mean()) / b if b else 0.0,
            reduction_ci=100.0 * dci / b if b else 0.0,
            people_spared=float(diff.mean()),
        )
    return out


def final_size_distribution(sizes: np.ndarray, n: int, bins: int = 15):
    hist, edges = np.histogram(sizes, bins=bins, range=(0, n))
    return hist, edges


def patient_zero_potential(net: Net, p_arc: np.ndarray, trials: int = 400, seed: int = 11):
    """Expected outbreak size if each person in turn is patient zero (their 'true' spreading power)."""
    import pandas as pd

    draws = Draws.make(net, trials, seed)
    rows = []
    for node in net.nodes:
        sizes = run_ic(net, p_arc, draws, seeds=[node])
        rows.append({"node": node, "outbreak_if_patient_zero": float(sizes.mean())})
    return pd.DataFrame(rows)
