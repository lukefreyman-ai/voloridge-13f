"""SEC Official List of Section 13(f) Securities -> one row per (CUSIP, issuer name, issuer description, status).
The quarterly PDF prints each security as: CUSIP (6 2 1), optional '*' (option available), ISSUER NAME,
ISSUER DESCRIPTION, optional ADDED/DELETED. Names are CUSIP-standard abbreviations (HLDGS, INTL, ...).
  python3 -m pipeline.seclist_names <year> <qtr>      -> cache/parsed/seclist_<year>q<qtr>.parquet (from the cached PDF)"""
from __future__ import annotations

import gzip
import re
import sys
from pathlib import Path

import pandas as pd
import pymupdf

ROW = re.compile(r"^([0-9A-Z]{6}) ([0-9A-Z]{2}) ([0-9])$")
STATUS = {"ADDED", "DELETED"}


def parse_pdf(data: bytes) -> pd.DataFrame:
    doc = pymupdf.open(stream=data, filetype="pdf")
    rows = []
    for page in doc:
        lines = [l.strip() for l in page.get_text().splitlines()]
        i = 0
        while i < len(lines):
            m = ROW.match(lines[i])
            if not m:
                i += 1
                continue
            j = i + 1
            has_option = False
            if j < len(lines) and lines[j] in ("*", ""):
                has_option = lines[j] == "*"
                j += 1
            name = lines[j] if j < len(lines) else ""
            desc = lines[j + 1] if j + 1 < len(lines) else ""
            status = lines[j + 2] if j + 2 < len(lines) and lines[j + 2] in STATUS else ""
            rows.append((m.group(1) + m.group(2) + m.group(3), name, desc, status, has_option))
            i = j + 2
    return pd.DataFrame(rows, columns=["cusip", "issuer_name", "issuer_desc", "status", "has_option"])


def load(year: int, qtr: int) -> pd.DataFrame:
    p = Path(f"cache/raw/divisions/investment/13f/13flist{year}q{qtr}.pdf.gz")
    df = parse_pdf(gzip.open(p).read())
    df["cusip6"] = df["cusip"].str[:6]
    df["list_quarter"] = f"{year}q{qtr}"
    return df


if __name__ == "__main__":
    y, q = int(sys.argv[1]), int(sys.argv[2])
    df = load(y, q)
    df.to_parquet(f"cache/parsed/seclist_{y}q{q}.parquet", index=False)
    print(f"13(f) list {y}q{q}: {len(df):,} rows, {df['cusip'].nunique():,} distinct CUSIPs, "
          f"{df['cusip6'].nunique():,} issuers; status: {df['status'].value_counts().to_dict()}")
