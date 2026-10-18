"""Step 0: download the dataset and build data/hospital_contact_graph.graphml."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from containnet.pipeline import step_graph

if __name__ == "__main__":
    step_graph()
