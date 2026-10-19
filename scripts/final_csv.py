"""CLI wrapper. The implementation lives in pipeline/final_csv.py so that
notebook.ipynb produces the final dataset itself, as the spec requires.

Run from the repo root:  python3 scripts/final_csv.py
"""
import sys

sys.path.insert(0, ".")

from pipeline.final_csv import build

if __name__ == "__main__":
    sys.exit(build())
