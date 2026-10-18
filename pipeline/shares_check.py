"""Shares/value sanity check (decisions of 2026-10-08):
  - value is NEVER overwritten. A filing-level value_scale_flag ("", "x1000", "div1000") is written
    to the filings parquet; a rescaled value is used INTERNALLY here only.
  - implied_price = value*1000 / shares. Reference = per-CUSIP median across distinct filings
    (>= min_filings). Pass 1 on values as filed finds filings reporting in dollars (filing median
    ratio 500-2000) or in millions (0.0005-0.002); pass 2 recomputes medians with those filings
    normalized.
  - rounding-aware: value is rounded to the nearest $1000, so the true price lies in
    [(v-0.5)*1000/shares, (v+0.5)*1000/shares]. A row is flagged only when that whole interval
    is outside median*(1 -/+ tol).
  - flagged rows are assigned one cause, in order: scale (row-level ratio still ~1000 or ~0.001
    after filing normalization) -> wrong shares column (filing carries the value/shares swap note,
    or >50% of its testable rows are flagged) -> cusip repaired/short id (cusip_status not ok) ->
    cusip ambiguous (the CUSIP's own filing-level prices spread > tol: share class / ADR / unit mix)
    -> unexplained.
Usage: python3 -m pipeline.shares_check <label> [--min-filings 3] [--tol 0.25]"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCALE_UP = (500, 2000)        # filer reported dollars: implied/median ~ 1000
SCALE_DOWN = (0.0005, 0.002)  # filer reported millions


def _reference(e: pd.DataFrame, value_col: str, min_filings: int) -> pd.DataFrame:
    price = e[value_col] * 1000.0 / e["shares"]
    pf = e.assign(_p=price).groupby(["cusip", "accession"])["_p"].median().reset_index()
    g = pf.groupby("cusip")["_p"]
    ref = g.agg(median_price="median", n_filings="size", q25=lambda s: s.quantile(0.25), q75=lambda s: s.quantile(0.75)).reset_index()
    ref["cusip_spread"] = (ref["q75"] - ref["q25"]) / ref["median_price"]
    ref["testable"] = ref["n_filings"] >= min_filings
    return ref.drop(columns=["q25", "q75"])


def _flag(e: pd.DataFrame, value_col: str, tol: float) -> pd.Series:
    lo = (e[value_col] - 0.5) * 1000.0 / e["shares"]      # rounding interval of the true price
    hi = (e[value_col] + 0.5) * 1000.0 / e["shares"]
    above = lo > e["median_price"] * (1 + tol)
    below = hi < e["median_price"] * (1 - tol)
    return e["testable"] & (above | below)


def run(label: str, min_filings: int = 3, tol: float = 0.25) -> tuple[pd.DataFrame, str]:
    cache = Path("cache/parsed")
    h = pd.read_parquet(cache / f"{label}_holdings.parquet")
    f = pd.read_parquet(cache / f"{label}_filings.parquet")
    fcols = ["accession", "parse_method", "checksum_status", "checksum_cause", "report_type", "manager_name"]
    if "notes" in f:
        fcols.append("notes")
    h = h.merge(f[fcols], on="accession", how="left")
    h["notes"] = h["notes"].fillna("") if "notes" in h else ""
    h["swap_noted"] = h["notes"].str.contains("value/shares swap", regex=False)

    out = [f"{label}: shares/value check   (min distinct filings per CUSIP = {min_filings}, tolerance = {tol:.0%}, rounding-aware)\n"]
    prn = h["sh_prn"].eq("PRN")
    opt = h["put_call"].ne("")
    zero = ~(h["shares"].fillna(0) > 0) | ~(h["value"].fillna(0) > 0)
    eligible = ~(prn | opt | zero)
    out.append(f"rows total {len(h):,} | excluded: PRN {prn.sum():,}, put/call {(opt & ~prn).sum():,}, "
               f"zero/missing value or shares {(zero & ~prn & ~opt).sum():,} | eligible {eligible.sum():,}")
    e = h[eligible].copy()
    e["value"] = e["value"].astype(float)

    # ---- pass 1: values as filed -> filing-level scale flag
    ref1 = _reference(e, "value", min_filings)
    e = e.merge(ref1, on="cusip", how="left")
    e["ratio_raw"] = (e["value"] * 1000.0 / e["shares"]) / e["median_price"]
    e["flag_raw"] = _flag(e, "value", tol)
    fm = e[e["testable"]].groupby("accession")["ratio_raw"].median()
    scale = pd.Series("", index=fm.index)
    scale[(fm >= SCALE_UP[0]) & (fm <= SCALE_UP[1])] = "x1000"
    scale[(fm >= SCALE_DOWN[0]) & (fm <= SCALE_DOWN[1])] = "div1000"
    e["value_scale_flag"] = e["accession"].map(scale).fillna("")
    # persist the filing-level flag (reported values untouched)
    f["value_scale_flag"] = f["accession"].map(scale).fillna("")
    f.to_parquet(cache / f"{label}_filings.parquet", index=False)
    t1 = e[e["testable"]]
    out.append(f"testable rows (CUSIP in >= {min_filings} filings) {len(t1):,} of eligible {len(e):,}; not testable {(~e['testable']).sum():,}")
    out.append(f"\nPASS 1 (values as filed, rounding-aware): flagged {t1['flag_raw'].sum():,} / {len(t1):,} = {t1['flag_raw'].mean():.2%}")
    out.append(f"filings given value_scale_flag: x1000 {(scale == 'x1000').sum()}, div1000 {(scale == 'div1000').sum()} "
               f"(rows {(e['value_scale_flag'] == 'x1000').sum():,} / {(e['value_scale_flag'] == 'div1000').sum():,}); "
               f"of the x1000 filings, checksum already said 'scale': {f.loc[f['value_scale_flag'] == 'x1000', 'checksum_cause'].str.contains('scale').sum()}")

    # ---- pass 2: normalized internally. Scale detection is repeated once on the normalized medians: a dollar
    #      filer whose raw filing-median ratio fell just outside 500-2000 (reference medians were polluted by
    #      other dollar filers) is caught on the second pass (e.g. Crow Point: raw 498 -> normalized 993).
    for _pass in (1, 2):
        e["value_norm"] = np.where(e["value_scale_flag"] == "x1000", e["value"] / 1000.0,
                           np.where(e["value_scale_flag"] == "div1000", e["value"] * 1000.0, e["value"]))
        e = e.drop(columns=["median_price", "n_filings", "cusip_spread", "testable"])
        ref2 = _reference(e, "value_norm", min_filings)
        e = e.merge(ref2, on="cusip", how="left")
        e["implied_price"] = e["value_norm"] * 1000.0 / e["shares"]
        e["ratio"] = e["implied_price"] / e["median_price"]
        if _pass == 1:
            fm2 = e[e["testable"]].groupby("accession")["ratio"].median()
            up = fm2[(fm2 >= SCALE_UP[0]) & (fm2 <= SCALE_UP[1])].index
            dn = fm2[(fm2 >= SCALE_DOWN[0]) & (fm2 <= SCALE_DOWN[1])].index
            unflagged = e["value_scale_flag"] == ""
            e.loc[unflagged & e["accession"].isin(up), "value_scale_flag"] = "x1000"
            e.loc[unflagged & e["accession"].isin(dn), "value_scale_flag"] = "div1000"
            scale = e.groupby("accession")["value_scale_flag"].first()
            f["value_scale_flag"] = f["accession"].map(scale).fillna("")
            f.to_parquet(cache / f"{label}_filings.parquet", index=False)
    e["flag"] = _flag(e, "value_norm", tol)
    t = e[e["testable"]].copy()
    out.append(f"\nPASS 2 (scale-normalized internally): FLAG RATE {t['flag'].sum():,} / {len(t):,} = {t['flag'].mean():.2%}")

    # ---- causes
    r = t["ratio"]
    row_scale = ((r >= SCALE_UP[0]) & (r <= SCALE_UP[1])) | ((r >= SCALE_DOWN[0]) & (r <= SCALE_DOWN[1]))
    fshare = t.groupby("accession")["flag"].transform("mean")
    wrong_col = t["swap_noted"] | (fshare > 0.5)
    repaired = t["cusip_status"].ne("ok")
    ambiguous = t["cusip_spread"] > tol
    cause = np.select([~t["flag"], row_scale, wrong_col, repaired, ambiguous],
                      ["", "scale (row-level x1000 / ÷1000)", "wrong shares column (swap note or >50% of filing flagged)",
                       "cusip repaired / short id", "cusip ambiguous (filing prices spread >tol: class / ADR / unit mix)"],
                      default="unexplained")
    t["cause"] = cause
    e["cause"] = ""
    e.loc[t.index, "cause"] = cause
    vc = t.loc[t["flag"], "cause"].value_counts()
    out.append("\nflagged rows by cause (one per row, precedence as listed):\n" + vc.to_string() + f"\n  sum {vc.sum():,}")

    def by(col, title):
        g = t.groupby(col)["flag"].agg(rows="size", flagged="sum")
        g["rate"] = (g["flagged"] / g["rows"]).map("{:.2%}".format)
        out.append(f"\n{title}:\n" + g.to_string())
    by("parse_method", "by parse path")
    by("swap_noted", "by value/shares swap note")
    by("value_scale_flag", "by value_scale_flag")
    by("checksum_status", "by checksum status")
    buckets = pd.cut(t.loc[t["flag"], "ratio"], [0, 0.0015, 0.5, 0.75, 1.25, 2, 500, 2000, np.inf],
                     labels=["<0.0015", "0.0015–0.5", "0.5–0.75", "0.75–1.25", "1.25–2", "2–500", "500–2000", ">2000"])
    out.append("\nflagged rows by implied/median ratio (after normalization):\n" + buckets.value_counts().sort_index().to_string())
    fl = t.groupby("accession")["flag"].agg(rows="size", flagged="sum")
    fl["share"] = fl["flagged"] / fl["rows"]
    out.append(f"\nfilings with testable rows {len(fl):,}; >50% of rows flagged {(fl['share'] > 0.5).sum():,}; any flag {(fl['flagged'] > 0).sum():,}")
    top = fl[fl["rows"] >= 5].sort_values("share", ascending=False).head(10).reset_index()
    top = top.merge(f[["accession", "manager_name", "value_scale_flag", "checksum_cause"]], on="accession", how="left")
    top["share"] = top["share"].map("{:.0%}".format)
    out.append("\nfilings with >=5 testable rows, highest flagged share (after normalization):\n" + top.to_string(index=False, max_colwidth=32))
    sw = t[t["swap_noted"]]
    if len(sw):
        g = sw.groupby("accession")["flag"].agg(rows="size", flagged="sum").reset_index()
        g = g.merge(f[["accession", "manager_name", "value_scale_flag", "checksum_cause"]], on="accession", how="left")
        out.append("\nswap-noted filings, row-level result:\n" + g.to_string(index=False, max_colwidth=32))
    txt = "\n".join(out)
    outdir = Path("output/problems") / label
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "shares_check.txt").write_text(txt)
    e[["accession", "cusip", "cusip_status", "value", "value_scale_flag", "value_norm", "shares", "implied_price", "median_price",
       "n_filings", "cusip_spread", "testable", "ratio_raw", "flag_raw", "ratio", "flag", "cause"]] \
        .to_parquet(cache / f"{label}_shares_check.parquet", index=False)
    return e, txt


if __name__ == "__main__":
    label = sys.argv[1]
    kw = {}
    if "--min-filings" in sys.argv:
        kw["min_filings"] = int(sys.argv[sys.argv.index("--min-filings") + 1])
    if "--tol" in sys.argv:
        kw["tol"] = float(sys.argv[sys.argv.index("--tol") + 1])
    _, txt = run(label, **kw)
    print(txt)
