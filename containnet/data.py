"""Download, clean and load the SocioPatterns hospital-ward contact network.

Source : https://networks.skewed.de/net/sp_hospital  (Vanhems et al., PLoS ONE 2013)
Output : data/hospital_contact_graph.graphml  -- undirected, weighted.
         edge weight = number of 20-second intervals the two people were face to face.
         node attrs  = status (NUR / PAT / MED / ADM), person_id (anonymous badge id)
"""
from __future__ import annotations

import io
import zipfile

import networkx as nx
import pandas as pd

from .config import GRAPH_PATH, RAW_DIR, ZIP_PATH, ZIP_URL


def download_zip() -> None:
    """Download the dataset unless a local copy already exists."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists():
        print(f"Using local archive {ZIP_PATH}")
        return
    import requests  # imported lazily: the app itself never needs it

    print(f"Downloading {ZIP_URL}")
    resp = requests.get(ZIP_URL, timeout=60)
    resp.raise_for_status()
    ZIP_PATH.write_bytes(resp.content)


def _read_member(z: zipfile.ZipFile, name_part: str) -> pd.DataFrame | None:
    for name in z.namelist():
        if name_part in name.lower() and name.lower().endswith(".csv"):
            with z.open(name) as fh:
                df = pd.read_csv(io.TextIOWrapper(fh, encoding="utf-8"))
            df.columns = [str(c).lstrip("#").strip() for c in df.columns]
            return df
    return None


def build_graph() -> nx.Graph:
    """Aggregate ~32k raw contact events into one weighted static graph."""
    with zipfile.ZipFile(ZIP_PATH) as z:
        edges = _read_member(z, "edges")
        nodes = _read_member(z, "nodes")
    if edges is None:
        raise RuntimeError("edges.csv not found inside the archive")

    pairs = (
        edges.assign(a=edges[["source", "target"]].min(axis=1), b=edges[["source", "target"]].max(axis=1))
        .query("a != b")
        .groupby(["a", "b"])
        .size()
        .reset_index(name="weight")
    )
    g = nx.Graph()
    for a, b, w in pairs.itertuples(index=False):
        g.add_edge(str(a), str(b), weight=int(w))

    status, pid = {}, {}
    if nodes is not None and {"index", "status"}.issubset(nodes.columns):
        for row in nodes.itertuples(index=False):
            status[str(row.index)] = str(row.status)
            if hasattr(row, "id"):
                pid[str(row.index)] = str(row.id)
    nx.set_node_attributes(g, {n: status.get(n, "UNKNOWN") for n in g}, "status")
    nx.set_node_attributes(g, {n: pid.get(n, n) for n in g}, "person_id")
    return g


def build_and_save() -> nx.Graph:
    download_zip()
    g = build_graph()
    GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(g, GRAPH_PATH)
    print(f"Built graph: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges -> {GRAPH_PATH}")
    return g


def load_graph() -> nx.Graph:
    """Load the cleaned graph, building it first if it does not exist yet."""
    if not GRAPH_PATH.exists():
        return build_and_save()
    return nx.read_graphml(GRAPH_PATH)


def backbone(g: nx.Graph, m: int) -> nx.Graph:
    """Keep each person's `m` strongest contacts (edge survives if either end keeps it).

    The raw ward graph is extremely dense (41% of all pairs linked), so clique
    percolation merges everyone into one giant community. The backbone strips the
    brief, incidental contacts and leaves the repeated ones, which is what actually
    carries transmission.
    """
    keep: set[frozenset] = set()
    for n in g:
        top = sorted(g[n].items(), key=lambda kv: -kv[1].get("weight", 1))[:m]
        keep.update(frozenset((n, v)) for v, _ in top)
    h = nx.Graph()
    h.add_nodes_from(g.nodes(data=True))
    for e in keep:
        u, v = tuple(e)
        h.add_edge(u, v, **g[u][v])
    return h


def node_order(g: nx.Graph) -> list[str]:
    """Stable node ordering (numeric where possible)."""
    return sorted(g.nodes(), key=lambda n: (0, int(n)) if str(n).isdigit() else (1, str(n)))
