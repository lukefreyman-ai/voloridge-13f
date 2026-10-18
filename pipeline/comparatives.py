"""Second fallback investigation (Luke 2026-10-09, item 3): prior-period share counts reported as
comparatives in LATER XBRL filings. For a target quarter end (2010-03-31) we look in later notes data
sets for: (a) us-gaap:CommonStockSharesOutstanding (balance-sheet instant) and dei facts dated near the
target; (b) us-gaap:WeightedAverageNumberOfSharesOutstandingBasic for the 3 months ended at the target
(a period average, not a point-in-time count). Reports coverage of the 13F companies missing a 2010
cover-page fact and validates on companies that have both. NOT used for ownership until approved.
  python3 -m pipeline.comparatives <label> <quarter_end> <map csv> <notes zip> [...]"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

TAGS_INSTANT = ("CommonStockSharesOutstanding", "EntityCommonStockSharesOutstanding")
TAG_WAVG = "WeightedAverageNumberOfSharesOutstandingBasic"


def load(zips):
    parts = []
    for z in zips:
        zf = zipfile.ZipFile(z)
        sub = pd.read_csv(zf.open("sub.tsv"), sep="\t", dtype=str, usecols=["adsh", "cik", "name", "form", "filed"])
        num = pd.read_csv(zf.open("num.tsv"), sep="\t", dtype=str, usecols=["adsh", "tag", "ddate", "qtrs", "value", "coreg", "dimh"])
        num = num[num["tag"].isin(TAGS_INSTANT + (TAG_WAVG,)) & num["coreg"].isna() & (num["dimh"] == "0x00000000")]
        d = num.merge(sub, on="adsh"); d["source_set"] = Path(z).stem
        parts.append(d)
    f = pd.concat(parts, ignore_index=True)
    f["cik"] = f["cik"].astype(int); f["shares"] = pd.to_numeric(f["value"], errors="coerce")
    f["asof"] = pd.to_datetime(f["ddate"], format="%Y%m%d", errors="coerce"); f["filed"] = pd.to_datetime(f["filed"], format="%Y%m%d", errors="coerce")
    return f[f["shares"].notna() & (f["shares"] > 0)]


if __name__ == "__main__":
    label, qend, mapcsv = sys.argv[1], pd.Timestamp(sys.argv[2]), sys.argv[3]
    zips = sys.argv[4:]
    f = load(zips)
    m = pd.read_csv(mapcsv); ciks13f = set(m["company_cik"].astype(int))
    have = pd.read_parquet(f"cache/parsed/{label}_shares_out.parquet"); have_ciks = set(have["cik"])
    missing = ciks13f - have_ciks
    out = [f"{label}: comparatives from {', '.join(Path(z).stem for z in zips)} for quarter end {qend.date()}",
           f"13F companies mapped to a CIK: {len(ciks13f):,}; with a 2010 cover-page XBRL fact: {len(ciks13f & have_ciks):,}; missing: {len(missing):,}"]
    inst = f[f["tag"].isin(TAGS_INSTANT)].copy(); inst["gap"] = (inst["asof"] - qend).dt.days
    # (a) instants within +-100 days of the target (year-end 2009-12-31 = -90 days, 2010-06-30 = +91)
    near = inst[inst["gap"].abs() <= 100].copy(); near["abs_gap"] = near["gap"].abs()
    near = near.sort_values(["cik", "abs_gap", "filed"], ascending=[True, True, False]).drop_duplicates("cik")
    exact = inst[inst["asof"] == qend].sort_values(["cik", "filed"], ascending=[True, False]).drop_duplicates("cik")
    wavg = f[(f["tag"] == TAG_WAVG) & (f["asof"] == qend) & (f["qtrs"] == "1")].sort_values(["cik", "filed"], ascending=[True, False]).drop_duplicates("cik")
    for name, d in [("instant exactly at quarter end (balance-sheet comparative)", exact), ("instant within 100 days of quarter end", near), ("weighted-average basic shares, the 3 months ended at quarter end", wavg)]:
        cov = set(d["cik"]) & missing
        out.append(f"  {name}: covers {len(cov):,} of {len(missing):,} missing companies ({len(cov) / max(len(missing), 1):.1%}); facts on {d['cik'].nunique():,} CIKs overall")
    # value-weighted coverage of the missing companies
    sc = pd.read_parquet(f"cache/parsed/{label}_shares_check.parquet", columns=["cusip", "value_norm"]); sc = sc[sc["value_norm"] <= 2e8]
    v6 = sc.groupby(sc["cusip"].str[:6])["value_norm"].sum()
    m6 = m.drop_duplicates("cusip6").set_index("cusip6")["company_cik"]
    vcik = v6.groupby(m6.reindex(v6.index)).sum()
    vmiss = vcik.reindex(list(missing)).fillna(0).sum(); vall = vcik.sum()
    out.append(f"missing companies carry {vmiss / vall:.1%} of mapped 13F value; of that, covered by exact instant: "
               f"{vcik.reindex(list(set(exact['cik']) & missing)).fillna(0).sum() / max(vmiss, 1):.1%}, by instant within 100d: "
               f"{vcik.reindex(list(set(near['cik']) & missing)).fillna(0).sum() / max(vmiss, 1):.1%}, by weighted-average: "
               f"{vcik.reindex(list(set(wavg['cik']) & missing)).fillna(0).sum() / max(vmiss, 1):.1%}")
    # validation on companies that have both the 2010 cover fact and a comparative
    hv = have[have["class_axis"] == ""].set_index("cik")["shares"]
    for name, d in [("exact instant", exact), ("instant within 100d", near), ("weighted-average", wavg)]:
        both = d[d["cik"].isin(hv.index)].copy(); both["cover"] = both["cik"].map(hv); both["ratio"] = both["shares"] / both["cover"]
        if len(both):
            out.append(f"validation {name}: n={len(both):,}; within 1% of the cover-page fact {((both['ratio'] - 1).abs() <= 0.01).mean():.1%}; within 5% {((both['ratio'] - 1).abs() <= 0.05).mean():.1%}; "
                       f"median |diff| {((both['ratio'] - 1).abs()).median():.2%}")
    txt = "\n".join(out); open(f"output/problems/{label}/comparatives.txt", "w").write(txt); print(txt)
    pd.concat([exact.assign(kind="exact"), near.assign(kind="near"), wavg.assign(kind="wavg")]).to_parquet(f"cache/parsed/{label}_comparatives.parquet", index=False)
