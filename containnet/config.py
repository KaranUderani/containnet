"""Single place for paths, constants and human-readable labels."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
GRAPH_PATH = DATA_DIR / "hospital_contact_graph.graphml"
RESULTS_DIR = ROOT / "results"
FIG_DIR = RESULTS_DIR / "figures"

ZIP_URL = "https://networks.skewed.de/net/sp_hospital/files/sp_hospital.csv.zip"
ZIP_PATH = RAW_DIR / "sp_hospital.csv.zip"

ROLE_NAMES = {
    "NUR": "Nurse / aide",
    "PAT": "Patient",
    "MED": "Doctor",
    "ADM": "Admin staff",
    "UNKNOWN": "Unknown",
}

# Defaults used by the scripts AND the app, so numbers in the report match the dashboard.
DEFAULTS = dict(
    backbone_m=4,        # each person keeps their m strongest contacts for CPM
    cpm_k=3,             # clique size for Clique Percolation
    louvain_runs=30,     # Louvain is stochastic: keep the best of N runs
    budget=8,            # people we can vaccinate / isolate
    trials=1000,         # Monte Carlo runs per strategy
    n_seeds=1,           # patient zero count
    random_sets=40,      # random strategy is averaged over this many random draws
    beta=0.004,          # transmission hazard per 20-second contact interval
    rng_seed=2026,
)

# Named disease presets -> beta (per 20-second contact interval hazard).
DISEASE_PRESETS = {
    "Slow spreader": 0.0015,
    "Seasonal flu-like": 0.004,
    "Fast spreader": 0.010,
}

STRATEGY_COLORS = {
    "none": "#8A97A0",
    "random": "#C9A227",
    "degree": "#5B7C99",
    "betweenness": "#2F5D8A",
    "eigenvector": "#7A6C9D",
    "community_degree": "#0F7B8A",
    "bridge_score": "#D2691E",
    "cpm_bridge": "#C2185B",
    "greedy": "#1B1F23",
}
