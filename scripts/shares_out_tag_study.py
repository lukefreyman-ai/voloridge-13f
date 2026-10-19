"""Measurement only, changes nothing: would a period-end-dated share count fix the over-100% cases?

pipeline/shares_out.py uses dei:EntityCommonStockSharesOutstanding, a COVER-PAGE fact whose
as-of date sits near the filing date, typically 31-59 days after quarter end. The same data sets
carry balance-sheet facts dated AT period end. This script compares what is available and how
many over-100% companies a period-end denominator would resolve.

  python3 scripts/shares_out_tag_study.py <label> <quarter_end YYYY-MM-DD> <notes zip> [...]
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pandas as pd

COVER = "EntityCommonStockSharesOutstanding"
BALANCE = ("CommonStockSharesOutstanding", "CommonStockSharesIssued")
FORMS = ("10-K", "10-Q", "10-K/A", "10-Q/A", "20-F", "40-F", "10-KT", "10-QT")


def facts(zips, qend):
    qe = pd.Timestamp(qend)
    parts = []
    for z in zips:
        zf = zipfile.ZipFile(z)
        sub = pd.read_csv(zf.open("sub.tsv"), sep="\t", dtype=str, usecols=["adsh", "cik", "form"])
        sub = sub[sub["form"].isin(FORMS)]
        keep = set(sub["adsh"])
        for chunk in pd.read_csv(zf.open("num.tsv"), sep="\t", dtype=str,
                                 usecols=["adsh", "tag", "ddate", "value", "coreg", "dimh"],
                                 chunksize=1_000_000):
            c = chunk[chunk["tag"].isin((COVER,) + BALANCE) & chunk["adsh"].isin(keep)
                      & chunk["coreg"].isna()]
            if len(c):
                parts.append(c.merge(sub, on="adsh"))
    f = pd.concat(parts, ignore_index=True)
    f["cik"] = f["cik"].astype(int)
    f["shares"] = pd.to_numeric(f["value"], errors="coerce")
    f["asof"] = pd.to_datetime(f["ddate"], format="%Y%m%d", errors="coerce")
    f = f[f["shares"].notna() & (f["shares"] > 0) & f["asof"].notna()].copy()
    f["gap_days"] = (f["asof"] - qe).dt.days
    return f


def main() -> int:
    label, qend, zips = sys.argv[1], sys.argv[2], sys.argv[3:]
    f = facts(zips, qend)
    out = [f"{label}: share-count tags available in {', '.join(Path(z).stem for z in zips)}", ""]
    for name, sel in (("cover (in use)", f["tag"] == COVER), ("balance sheet", f["tag"].isin(BALANCE))):
        d = f[sel]
        at_qend = (d["gap_days"] == 0).sum()
        out.append(f"{name:<16} facts {len(d):>8,}  CIKs {d['cik'].nunique():>6,}  "
                   f"dated exactly at quarter end {at_qend:>7,} ({100*at_qend/max(len(d),1):.1f}%)  "
                   f"median gap {d['gap_days'].median():.0f}d")

    # how many over-100% companies could get a quarter-end-dated denominator instead
    ov = Path(f"output/problems/{label}/over_100_companies.csv")
    if ov.exists():
        o = pd.read_csv(ov)
        cik_col = next((c for c in o.columns if c.lower() in ("company_cik", "cik")), None)
        pct_col = next((c for c in o.columns if "ownership_pct" in c.lower()), None)
        bal_qend = f[f["tag"].isin(BALANCE) & (f["gap_days"] == 0)]
        best = bal_qend.sort_values("shares", ascending=False).drop_duplicates("cik").set_index("cik")["shares"]
        o["cik_i"] = pd.to_numeric(o[cik_col], errors="coerce")
        o["qend_shares"] = o["cik_i"].map(best)
        have = o["qend_shares"].notna()
        out += ["", f"over-100% companies in {label}: {len(o):,}",
                f"  with a quarter-end-dated balance-sheet figure available: {have.sum():,} ({100*have.sum()/max(len(o),1):.1f}%)"]
        if pct_col and have.any():
            so_col = next((c for c in o.columns if c.lower() == "shares_outstanding"), None)
            if so_col:
                held = o.loc[have, so_col] * o.loc[have, pct_col] / 100
                newpct = 100 * held / o.loc[have, "qend_shares"]
                out += [f"  of those, recomputed with the quarter-end figure:",
                        f"    still over 100%: {(newpct > 100).sum():,}",
                        f"    would drop below 100%: {(newpct <= 100).sum():,}",
                        f"    median ownership {o.loc[have, pct_col].median():.1f}% -> {newpct.median():.1f}%"]
    txt = "\n".join(out)
    Path(f"output/problems/{label}").mkdir(parents=True, exist_ok=True)
    open(f"output/problems/{label}/shares_out_tag_study.txt", "w").write(txt + "\n")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.path.insert(0, ".")
    sys.exit(main())
