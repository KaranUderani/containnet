"""Run the whole pipeline in order and write results/ (tables, figures, REPORT.md).

    python scripts/run_all.py
    python scripts/run_all.py --skip-scalability     # faster
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from containnet.pipeline import run_all

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-scalability", action="store_true")
    run_all(skip_scalability=ap.parse_args().skip_scalability)
