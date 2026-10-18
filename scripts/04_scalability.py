"""Step 4: time Louvain / centrality / Independent Cascade on synthetic networks up to 5,000 people."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from containnet.pipeline import step_scalability

if __name__ == "__main__":
    step_scalability()
