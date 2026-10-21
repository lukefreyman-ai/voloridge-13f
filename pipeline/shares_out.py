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
# A thousands-tagging error shows up as a ratio near 1,000. A reverse split or a dilution shows up
# as 10-30x, and must NOT trigger a correction. No US listed company in 2010-2014 had more than
# about 2.9e10 shares (Citigroup pre-split), so 1e11 is a generous ceiling on a possible result.
SCALE_RATIO_LO, SCALE_RATIO_HI = 900.0, 1100.0
# Citigroup pre-split, about 2.9e10, is the largest real US share count in 2010-2014.
MAX_PLAUSIBLE_SHARES = 35_000_000_000
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

    # Scale cross-check. Some filers tag a share count in THOUSANDS and the SEC data set stores it
    # verbatim: Apple 2014Q1 carries CommonStockSharesOutstanding = 861,745 against a cover-page
    # 861,381,000, which published Apple at 11,687% institutional ownership.
    #
    # The first version of this rule took the LARGER of the two tags whenever they differed by 10x.
    # Verification on 2026-10-19 showed that was wrong twice over: it fired on genuine 10-30x
    # reverse splits and dilution (17 of 173 in 2012Q2), and when the OTHER fact was the broken one
    # it took the broken one, publishing Oracle 2012Q2 with 4.819e15 shares and leaving 313
    # impossible denominators across the 20 quarters.
    #
    # So a correction now requires BOTH:
    #   - a ratio consistent with a thousands-tagging error, not a corporate action, and
    #   - a result that is physically possible for a US listed company.
    # The replacement also carries the ALTERNATE fact's own accession, form, tag and as-of date, so
    # shares_outstanding_source and shares_outstanding_date describe the value actually published.
    near = f.sort_values(["abs_gap", "filed"], ascending=[True, False])
    key = pd.MultiIndex.from_arrays([pick["cik"], pick["class_axis"]])
    pick["scale_corrected"] = False
    for tag in TAGS:
        altf = near[near["tag"] == tag].drop_duplicates(["cik", "class_axis"]).set_index(["cik", "class_axis"])
        if altf.empty:
            continue
        cand = pd.Series(key.map(altf["shares"]), index=pick.index)
        ratio = cand / pick["shares"]
        # Both directions. The picked fact can be 1000x too SMALL (tagged in thousands, Apple) or
        # 1000x too LARGE (Pentair published 9.84e10 shares against a real ~1e8, reporting 0.078%
        # ownership instead of ~78%). The first version only looked for too-small, which left 41
        # published companies with a denominator above any real US share count.
        too_small = ratio.between(SCALE_RATIO_LO, SCALE_RATIO_HI)
        too_large = (1 / ratio).between(SCALE_RATIO_LO, SCALE_RATIO_HI)
        ok = ((pick["tag"] != tag) & cand.notna() & (too_small | too_large)
              & (cand <= MAX_PLAUSIBLE_SHARES))
        if not ok.any():
            continue
        for col in ("shares", "adsh", "form", "tag", "asof", "filed"):
            pick.loc[ok, col] = pd.Series(key.map(altf[col]), index=pick.index)[ok]
        pick.loc[ok, "scale_corrected"] = True
    # recompute the vintage AFTER any correction, so the published date is the published value's
    pick["gap_days"] = (pick["asof"] - qe).dt.days
    pick["abs_gap"] = pick["gap_days"].abs()
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
