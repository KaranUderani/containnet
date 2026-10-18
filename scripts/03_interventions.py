"""Step 3: compare intervention strategies, budget curve, disease sensitivity."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from containnet.data import load_graph
from containnet.pipeline import step_interventions
from containnet.strategies import build_context
from containnet.config import DEFAULTS

if __name__ == "__main__":
    ctx = build_context(load_graph(), DEFAULTS["backbone_m"], DEFAULTS["cpm_k"], DEFAULTS["louvain_runs"])
    step_interventions(ctx)
