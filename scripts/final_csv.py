"""One clean CSV in exactly the 12 columns of the project description.

Reads every finished output/<label>_institutional_ownership.csv, keeps the 12 spec
columns in spec order, concatenates all quarters in chronological order and writes
output/institutional_ownership_12col.csv plus a per-quarter row-count table.

Values are passed through as text so nothing is reformatted: CUSIP leading zeros,
CIK padding and the exact ownership decimals are preserved byte for byte.

  python3 scripts/final_csv.py
"""
from __future__ import annotations

import glob
import os
import re
import shutil
import sys

import pandas as pd

SPEC = ["quarter_end", "company_name", "company_cik", "cusip", "manager_cik",
        "manager_name", "shares_held", "shares_outstanding",
        "institutional_ownership_pct", "form_13f_accession_number",
        "shares_outstanding_source", "shares_outstanding_date"]

OUT = "output/institutional_ownership_12col.csv"
COUNTS = "output/problems/final_csv_rowcounts.csv"
CHUNK = 200_000
MIN_FREE_GB = 2


def quarter_key(label: str) -> tuple[int, int]:
    m = re.search(r"(\d{4})Q(\d)", label)
    return (int(m.group(1)), int(m.group(2))) if m else (9999, 9)


def main() -> int:
    free_gb = shutil.disk_usage(".").free / 1e9
    if free_gb < MIN_FREE_GB:
        print(f"ABORT: {free_gb:.1f} GB free, need {MIN_FREE_GB} GB headroom")
        return 1

    files = sorted(glob.glob("output/*_institutional_ownership.csv"),
                   key=lambda p: quarter_key(os.path.basename(p)))
    if not files:
        print("ABORT: no output/<label>_institutional_ownership.csv found")
        return 1

    # every file must carry the 12 spec columns, or the deliverable is not the spec
    for f in files:
        cols = pd.read_csv(f, nrows=0).columns.tolist()
        missing = [c for c in SPEC if c not in cols]
        if missing:
            print(f"ABORT: {f} is missing {missing}")
            return 1

    if os.path.exists(OUT):
        os.remove(OUT)
    rows, suspect, header_written = [], 0, False

    for f in files:
        label = os.path.basename(f).replace("_institutional_ownership.csv", "")
        n = 0
        for chunk in pd.read_csv(f, usecols=SPEC, dtype=str, chunksize=CHUNK):
            chunk = chunk[SPEC]
            # a summary or junk row would have no quarter_end, no cusip or no manager
            bad = chunk["quarter_end"].isna() | chunk["cusip"].isna() | chunk["manager_cik"].isna()
            if bad.any():
                suspect += int(bad.sum())
                chunk = chunk[~bad]
            chunk.to_csv(OUT, mode="a", index=False, header=not header_written)
            header_written = True
            n += len(chunk)
        qe = pd.read_csv(f, usecols=["quarter_end"], nrows=1)["quarter_end"].iloc[0]
        rows.append({"label": label, "quarter_end": qe, "rows": n})
        print(f"  {label:<14} {qe}  {n:>10,} rows")

    tab = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(COUNTS), exist_ok=True)
    tab.to_csv(COUNTS, index=False)
    size_mb = os.path.getsize(OUT) / 1e6

    print(f"\n{len(files)} quarters, {tab['rows'].sum():,} rows -> {OUT} ({size_mb:,.0f} MB)")
    print(f"row-count table -> {COUNTS}")
    print(f"junk/summary rows dropped: {suspect}")
    print(f"columns: {len(SPEC)} ({', '.join(SPEC)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
