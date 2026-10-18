"""Fast sanity tests: run with `pytest -q` (or `python tests/test_core.py`)."""
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from containnet.data import backbone, load_graph
from containnet.simulation import Draws, arc_probability, build_net, run_ic
from containnet.strategies import build_context, compare_strategies


def test_graph_shape():
    g = load_graph()
    assert g.number_of_nodes() == 75
    assert g.number_of_edges() == 1139
    assert all(d["weight"] >= 1 for _, _, d in g.edges(data=True))


def test_backbone_is_sparser_and_keeps_everyone():
    g = load_graph()
    h = backbone(g, 4)
    assert h.number_of_nodes() == g.number_of_nodes()
    assert h.number_of_edges() < g.number_of_edges() / 3


def _naive_ic(g, seed, p, blocked=()):
    infected, active = {seed}, {seed}
    while active:
        new = set()
        for u in active:
            for v in g[u]:
                if v not in infected and v not in blocked and random.random() < p[(u, v)]:
                    new.add(v)
        infected |= new
        active = new
    return len(infected)


def test_vectorised_ic_matches_naive_loop():
    g = load_graph()
    net = build_net(g)
    beta = 0.003
    p_arc = arc_probability(net, beta)
    pm = {}
    for u, v, d in g.edges(data=True):
        q = 1 - np.exp(-beta * d["weight"])
        pm[(u, v)] = pm[(v, u)] = q
    random.seed(1)
    naive = np.mean([_naive_ic(g, "5", pm) for _ in range(2500)])
    fast = run_ic(net, p_arc, Draws.make(net, 2500, 9), seeds=["5"]).mean()
    assert abs(naive - fast) < 2.0


def test_protecting_people_never_increases_outbreak_with_same_randomness():
    g = load_graph()
    net = build_net(g)
    p_arc = arc_probability(net, 0.004)
    d = Draws.make(net, 500, 3)
    base = run_ic(net, p_arc, d, seeds=["5"])
    prot = run_ic(net, p_arc, d, seeds=["5"], blocked=["6", "28", "26"])
    assert (prot <= base).all()


def test_targeted_beats_random():
    ctx = build_context(load_graph(), 4, 3, louvain_runs=5)
    comp = compare_strategies(ctx, arc_probability(ctx.net, 0.004), 8, trials=600, random_sets=10).set_index("strategy")
    assert comp.loc["degree", "mean_infected"] < comp.loc["random", "mean_infected"] < comp.loc["none", "mean_infected"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
