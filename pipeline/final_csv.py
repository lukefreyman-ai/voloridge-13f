"""One clean CSV in exactly the 12 columns of the project description.

Imported by notebook.ipynb so the notebook itself produces the final dataset,
as the project description requires. scripts/final_csv.py is a thin CLI wrapper.

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


def build(verbose: bool = True) -> int:
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
        if verbose:
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


# ---------------------------------------------------------------------------
# Decision 12 (2026-10-18). Review found that institutional_ownership_pct is a
# COMPANY-level figure repeated on every manager row, and that the 12-column cut
# dropped every quality flag the pipeline produces. Both are fixed by shipping a
# company-quarter file alongside the row-level one: it is the natural grain of the
# variable, it is small enough to open in Excel, and it carries the flags.

COMPANY_OUT = "output/company_ownership_by_quarter.csv"
MANIFEST = "output/deliverable_manifest.json"

COMPANY_COLS = ["quarter_end", "company_cik", "company_name", "n_managers", "n_cusips",
                "shares_held_total", "shares_outstanding", "institutional_ownership_pct",
                "denominator_basis", "shares_outstanding_source", "shares_outstanding_date",
                "over_100_flag", "over_100_cause", "pct_suppressed_cause",
                "multi_class_flag", "map_conflict", "rows_excluded_from_figure"]


def build_company(verbose: bool = True) -> int:
    """One row per company x quarter: the grain institutional_ownership_pct actually has."""
    import glob
    import os

    files = sorted(glob.glob("output/*_institutional_ownership.csv"),
                   key=lambda p: quarter_key(os.path.basename(p)))
    frames = []
    for f in files:
        d = pd.read_csv(f, dtype={"company_cik": str, "cusip": str}, low_memory=False)
        d = d[d["company_cik"].notna() & (d["company_cik"] != "")]
        incl = d[d["excluded_from_ownership"].fillna("") == ""]
        g = incl.groupby(["quarter_end", "company_cik"], as_index=False).agg(
            company_name=("company_name", "first"),
            n_managers=("manager_cik", "nunique"),
            n_cusips=("cusip", "nunique"),
            shares_held_total=("shares_held", "sum"),
            shares_outstanding=("company_shares_outstanding", "first"),
            denominator_basis=("denominator_basis", "first"),
            institutional_ownership_pct=("institutional_ownership_pct", "first"),
            shares_outstanding_source=("shares_outstanding_source", "first"),
            shares_outstanding_date=("shares_outstanding_date", "first"),
            over_100_flag=("over_100_flag", "first"),
            over_100_cause=("over_100_cause", "first"),
            pct_suppressed_cause=("pct_suppressed_cause", "first"),
            multi_class_flag=("multi_class_flag", "first"),
            map_conflict=("map_conflict", "first"))
        exc = d[d["excluded_from_ownership"].fillna("") != ""].groupby(
            ["quarter_end", "company_cik"]).size().rename("rows_excluded_from_figure")
        g = g.merge(exc, on=["quarter_end", "company_cik"], how="left")
        g["rows_excluded_from_figure"] = g["rows_excluded_from_figure"].fillna(0).astype(int)
        frames.append(g[COMPANY_COLS])
        if verbose:
            print(f"  {os.path.basename(f).replace('_institutional_ownership.csv',''):<14} "
                  f"{len(g):>7,} companies")
    allc = pd.concat(frames, ignore_index=True)
    allc.to_csv(COMPANY_OUT, index=False)
    print(f"\n{len(allc):,} company-quarters -> {COMPANY_OUT} "
          f"({os.path.getsize(COMPANY_OUT) / 1e6:,.1f} MB)")
    return 0


def write_manifest() -> int:
    """Provenance, so no published figure is ever ambiguous about which build produced it."""
    import glob
    import hashlib
    import json
    import os
    import subprocess
    from datetime import datetime, timezone

    def sha_head():
        try:
            return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                  text=True, check=True).stdout.strip()
        except Exception:
            return "unknown"

    quarters = []
    for f in sorted(glob.glob("output/*_institutional_ownership.csv"),
                    key=lambda p: quarter_key(os.path.basename(p))):
        st = os.stat(f)
        with open(f, "rb") as fh:
            fh.seek(0)
            head = hashlib.sha256(fh.read(1_000_000)).hexdigest()[:16]
        quarters.append({"label": os.path.basename(f).replace("_institutional_ownership.csv", ""),
                         "file": f, "bytes": st.st_size,
                         "modified": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                         "sha256_first_1mb": head})
    mtimes = {q["modified"][:10] for q in quarters}
    man = {"built": datetime.now(timezone.utc).isoformat(), "code_commit": sha_head(),
           "quarters": quarters, "quarter_count": len(quarters),
           "single_build_date": len(mtimes) == 1,
           "warning": None if len(mtimes) == 1 else
                      f"per-quarter files span {len(mtimes)} dates: {sorted(mtimes)} - mixed vintages"}
    with open(MANIFEST, "w") as fh:
        json.dump(man, fh, indent=2)
    print(f"manifest -> {MANIFEST} (commit {man['code_commit'][:9]}, "
          f"{'single vintage' if man['single_build_date'] else 'MIXED VINTAGES'})")
    return 0
