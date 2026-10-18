"""Shares outstanding from XBRL cover-page facts (dei:EntityCommonStockSharesOutstanding) in the SEC
"Financial Statement and Notes" data sets (num.tsv carries dei; sub.tsv has form/filed per adsh).
Per Luke (2026-10-09): record source filing (form + accession) and as-of date (ddate), pick the filing
whose as-of date is CLOSEST to the quarter end, flag gaps over 100 days.
  python3 -m pipeline.shares_out build <label> <quarter_end YYYY-MM-DD> <notes zip> [<notes zip> ...]
Output: cache/parsed/<label>_shares_out.parquet (one row per cik x class) and a summary text."""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pandas as pd

TAG = "EntityCommonStockSharesOutstanding"
FORMS = ("10-K", "10-Q", "10-K/A", "10-Q/A", "20-F", "40-F", "10-KT", "10-QT")


def load_facts(zips: list[str]) -> pd.DataFrame:
    parts = []
    for z in zips:
        zf = zipfile.ZipFile(z)
        sub = pd.read_csv(zf.open("sub.tsv"), sep="\t", dtype=str, usecols=["adsh", "cik", "name", "form", "period", "filed"])
        num = pd.read_csv(zf.open("num.tsv"), sep="\t", dtype=str, usecols=["adsh", "tag", "ddate", "value", "coreg", "dimh", "dimn"])
        so = num[num["tag"] == TAG].merge(sub, on="adsh")
        so = so[so["form"].isin(FORMS) & so["coreg"].isna()]
        dim = pd.read_csv(zf.open("dim.tsv"), sep="\t", dtype=str, usecols=["dimhash", "segments"]).rename(columns={"dimhash": "dimh"})
        so = so.merge(dim, on="dimh", how="left")
        so["source_set"] = Path(z).stem
        parts.append(so)
    f = pd.concat(parts, ignore_index=True)
    f["cik"] = f["cik"].astype(int)
    f["shares"] = pd.to_numeric(f["value"], errors="coerce")
    f["asof"] = pd.to_datetime(f["ddate"], format="%Y%m%d", errors="coerce")
    f["filed"] = pd.to_datetime(f["filed"], format="%Y%m%d", errors="coerce")
    f["class_axis"] = f["segments"].fillna("")          # '' = undimensioned (total / single class); else e.g. 'StatementClassOfStockAxis=CommonClassAMember'
    f = f[f["shares"].notna() & (f["shares"] > 0) & f["asof"].notna()]
    return f.drop(columns=["value", "coreg", "dimh", "dimn", "segments", "tag"])


def select(f: pd.DataFrame, qend: str, max_gap: int = 100) -> pd.DataFrame:
    qe = pd.Timestamp(qend)
    f = f.copy()
    f["gap_days"] = (f["asof"] - qe).dt.days
    f["abs_gap"] = f["gap_days"].abs()
    # one fact per (cik, class): closest as-of to quarter end; ties -> the later filing
    f = f.sort_values(["cik", "class_axis", "abs_gap", "filed"], ascending=[True, True, True, False])
    pick = f.drop_duplicates(["cik", "class_axis"]).copy()
    pick["gap_flag"] = pick["abs_gap"] > max_gap
    pick["shares_outstanding_source"] = pick["form"] + " " + pick["adsh"]
    pick["shares_outstanding_date"] = pick["asof"].dt.strftime("%Y-%m-%d")
    return pick[["cik", "name", "class_axis", "shares", "shares_outstanding_source", "shares_outstanding_date", "form", "adsh", "filed", "gap_days", "gap_flag", "source_set"]]


def build(label: str, qend: str, zips: list[str]) -> tuple[pd.DataFrame, str]:
    facts = load_facts(zips)
    pick = select(facts, qend)
    Path("cache/parsed").mkdir(exist_ok=True)
    pick.to_parquet(f"cache/parsed/{label}_shares_out.parquet", index=False)
    n_cik = pick["cik"].nunique()
    multi = pick.groupby("cik")["class_axis"].nunique()
    out = [f"{label} shares outstanding (quarter end {qend}) from {', '.join(Path(z).stem for z in zips)}",
           f"facts loaded {len(facts):,} on {facts['cik'].nunique():,} CIKs | selected {len(pick):,} rows on {n_cik:,} CIKs",
           f"CIKs with class-dimensioned facts (multi-class): {(multi > 1).sum():,}; undimensioned-only: {(multi == 1).sum():,}",
           f"gap > 100 days flagged: {pick['gap_flag'].sum():,} rows; gap distribution (days): " + pick["gap_days"].describe()[["min", "25%", "50%", "75%", "max"]].round(0).to_dict().__str__(),
           "by form: " + pick["form"].value_counts().to_dict().__str__()]
    txt = "\n".join(out); Path(f"output/problems/{label}").mkdir(parents=True, exist_ok=True)
    open(f"output/problems/{label}/shares_out.txt", "w").write(txt)
    return pick, txt


if __name__ == "__main__":
    cmd, label, qend = sys.argv[1], sys.argv[2], sys.argv[3]
    _, txt = build(label, qend, sys.argv[4:])
    print(txt)
