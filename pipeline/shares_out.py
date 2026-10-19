"""Shares outstanding from XBRL facts in the SEC "Financial Statement and Notes" data sets
(num.tsv carries the facts; sub.tsv has form/filed per adsh).

Two kinds of share count exist and they have different vintages:
  - us-gaap:CommonStockSharesOutstanding  balance sheet, dated AT the period end (median gap 0 days)
  - dei:EntityCommonStockSharesOutstanding  cover page, dated near the FILING date (median gap 90 days)

Decision 11 (Luke, 2026-10-18): prefer a figure dated exactly at the quarter end, and among those
prefer the balance-sheet fact; otherwise fall back to the closest available, balance sheet first.
The cover-page fact alone left the denominator a median 90 days stale, which inflated ownership for
companies that bought back stock in the gap. Motivating measurement, on real data:
output/problems/pilot_2013Q4/shares_out_tag_study.txt (scripts/shares_out_tag_study.py).
CommonStockSharesIssued is deliberately NOT used: issued includes treasury shares, so it is not
outstanding and would understate ownership.

Per Luke (2026-10-09): record source filing (form + accession) and as-of date (ddate), pick the filing
whose as-of date is CLOSEST to the quarter end, flag gaps over 100 days.
  python3 -m pipeline.shares_out build <label> <quarter_end YYYY-MM-DD> <notes zip> [<notes zip> ...]
Output: cache/parsed/<label>_shares_out.parquet (one row per cik x class) and a summary text."""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pandas as pd

COVER_TAG = "EntityCommonStockSharesOutstanding"      # dei, cover page, dated near the filing date
BALANCE_TAG = "CommonStockSharesOutstanding"          # us-gaap, balance sheet, dated at period end
TAGS = (BALANCE_TAG, COVER_TAG)
TAG_PRIORITY = {BALANCE_TAG: 0, COVER_TAG: 1}         # lower wins when the as-of date ties
FORMS = ("10-K", "10-Q", "10-K/A", "10-Q/A", "20-F", "40-F", "10-KT", "10-QT")


def load_facts(zips: list[str]) -> pd.DataFrame:
    parts = []
    for z in zips:
        zf = zipfile.ZipFile(z)
        sub = pd.read_csv(zf.open("sub.tsv"), sep="\t", dtype=str, usecols=["adsh", "cik", "name", "form", "period", "filed"])
        num = pd.read_csv(zf.open("num.tsv"), sep="\t", dtype=str, usecols=["adsh", "tag", "ddate", "value", "coreg", "dimh", "dimn"])
        so = num[num["tag"].isin(TAGS)].merge(sub, on="adsh")
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
    return f.drop(columns=["value", "coreg", "dimh", "dimn", "segments"])


def select(f: pd.DataFrame, qend: str, max_gap: int = 100) -> pd.DataFrame:
    qe = pd.Timestamp(qend)
    f = f.copy()
    f["gap_days"] = (f["asof"] - qe).dt.days
    f["abs_gap"] = f["gap_days"].abs()
    # one fact per (cik, class). Order: nearest as-of date to the quarter end wins (so gap 0, the
    # period-end figure, wins outright); the balance-sheet tag breaks ties at the same distance;
    # then the later filing. Distance comes FIRST: a stale balance-sheet figure is worse than a
    # near cover-page one (tests/test_shares_out_select.py pins this).
    f["tag_priority"] = f["tag"].map(TAG_PRIORITY).fillna(9).astype(int)
    f = f.sort_values(["cik", "class_axis", "abs_gap", "tag_priority", "filed"],
                      ascending=[True, True, True, True, False])
    pick = f.drop_duplicates(["cik", "class_axis"]).copy()

    # Scale cross-check (2026-10-18, found reviewing decision 11). Some filers tag the balance-sheet
    # share count in THOUSANDS and the SEC data set stores it verbatim: Apple 2014Q1 carries
    # CommonStockSharesOutstanding = 861,745 against a cover-page 861,381,000. Preferring the
    # balance-sheet fact therefore made the denominator 1000x too small for those companies and
    # published Apple at 11,687% institutional ownership. Measured on 2014Q1: 42 of 6,216
    # (cik, class) pairs are affected, 97.2% agree within 2x.
    # A listed company's share count cannot genuinely move by more than 10x in a quarter, so a gap
    # that large is a units error and the LARGER value is the one in shares.
    near = f.sort_values("abs_gap")
    alt = {t: near[near["tag"] == t].drop_duplicates(["cik", "class_axis"])
                .set_index(["cik", "class_axis"])["shares"] for t in TAGS}
    key = pd.MultiIndex.from_arrays([pick["cik"], pick["class_axis"]])
    other = pd.concat([pd.Series(key.map(a), index=pick.index) for a in alt.values()], axis=1).max(axis=1)
    rescale = other.notna() & (pick["shares"] * 10 < other)
    pick["scale_corrected"] = rescale
    pick.loc[rescale, "shares"] = other[rescale]
    pick["gap_flag"] = pick["abs_gap"] > max_gap
    # the tag goes into the source string: the spec requires shares_outstanding_source, and which
    # XBRL fact was used is the single most important thing about a denominator
    pick["shares_outstanding_source"] = (pick["form"] + " " + pick["adsh"] + " " + pick["tag"]
                                         + pick["scale_corrected"].map({True: " (scale-corrected)", False: ""}))
    pick["shares_outstanding_date"] = pick["asof"].dt.strftime("%Y-%m-%d")
    return pick[["cik", "name", "class_axis", "shares", "shares_outstanding_source", "shares_outstanding_date", "form", "adsh", "tag", "filed", "gap_days", "gap_flag", "scale_corrected", "source_set"]]


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
           "by form: " + pick["form"].value_counts().to_dict().__str__(),
           "by XBRL tag (decision 11): " + pick["tag"].value_counts().to_dict().__str__(),
           f"dated exactly at quarter end: {(pick['gap_days'] == 0).sum():,} of {len(pick):,} "
           f"({100 * (pick['gap_days'] == 0).mean():.1f}%)",
           f"scale-corrected (fact tagged in thousands, cross-checked against the other tag): "
           f"{int(pick['scale_corrected'].sum()):,}"]
    txt = "\n".join(out); Path(f"output/problems/{label}").mkdir(parents=True, exist_ok=True)
    open(f"output/problems/{label}/shares_out.txt", "w").write(txt)
    return pick, txt


if __name__ == "__main__":
    cmd, label, qend = sys.argv[1], sys.argv[2], sys.argv[3]
    _, txt = build(label, qend, sys.argv[4:])
    print(txt)
