"""Step 1: Louvain vs Girvan-Newman vs CPM, centrality scores, overlap people, community maps."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from containnet.pipeline import step_communities

if __name__ == "__main__":
    step_communities()
