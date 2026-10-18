"""Compare our parse of raw filings with the SEC standardized 13F data set (2013Q2 onward).
  python3 -m pipeline.validate_secds <label> <index_year> <index_qtr>
Reads the cached data-set zip (cache/raw/files/structureddata/...), the label's filings/holdings parquets; writes
output/problems/<label>/secds_compare.txt and cache/parsed/<label>_secds_compare.parquet."""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as cfgmod
from .edgar import Edgar

DS_URL = "https://www.sec.gov/files/structureddata/data/form-13f-data-sets/{y}q{q}_form13f.zip"


def load_secds(edgar: Edgar, year: int, qtr: int) -> dict[str, pd.DataFrame]:
    z = zipfile.ZipFile(io.BytesIO(edgar.get(DS_URL.format(y=year, q=qtr))))
    out = {}
    for name in ("SUBMISSION", "SUMMARYPAGE", "INFOTABLE", "COVERPAGE"):
        with z.open(f"{name}.tsv") as fh:
            out[name] = pd.read_csv(fh, sep="\t", dtype=str, keep_default_na=False, low_memory=False)
    return out


def compare(ours_f: pd.DataFrame, ours_h: pd.DataFrame, ds: dict) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    it = ds["INFOTABLE"].copy()
    it["shares"] = pd.to_numeric(it["SSHPRNAMT"], errors="coerce")
    it["value"] = pd.to_numeric(it["VALUE"], errors="coerce")
    it = it.rename(columns={"ACCESSION_NUMBER": "accession", "CUSIP": "cusip"})
    it["cusip"] = it["cusip"].str.upper().str.strip()

    agg_ds = it.groupby("accession").agg(ds_rows=("cusip", "size"), ds_shares=("shares", "sum"), ds_value=("value", "sum"))
    oh = ours_h.copy()
    oh["cusip"] = oh["cusip"].str.upper().str.strip()
    agg_us = oh.groupby("accession").agg(our_rows=("cusip", "size"), our_shares=("shares", "sum"), our_value=("value", "sum"))

    f = ours_f[["accession", "manager_name", "form_type", "report_type", "n_rows", "entry_total", "value_total",
                "checksum_status", "checksum_cause"]].copy()
    f = f.merge(agg_us, on="accession", how="left").merge(agg_ds, on="accession", how="left")
    f["in_secds"] = f["ds_rows"].notna()
    for c in ("our_rows", "our_shares", "our_value"):
        f[c] = f[c].fillna(0)
    f["rows_match"] = f["in_secds"] & (f["our_rows"] == f["ds_rows"])
    f["shares_match"] = f["in_secds"] & (f["our_shares"] == f["ds_shares"])
    f["value_match"] = f["in_secds"] & (f["our_value"] == f["ds_value"])

    # row-level multiset match on (cusip, shares, value)
    key = ["accession", "cusip", "shares", "value"]
    a = oh.groupby(key).size().rename("n_us")
    b = it.groupby(key).size().rename("n_ds")
    m = pd.concat([a, b], axis=1).fillna(0)
    m["matched"] = np.minimum(m["n_us"], m["n_ds"])
    rl = m.groupby(level="accession").agg(rows_matched=("matched", "sum"))
    f = f.merge(rl, on="accession", how="left")
    f["rows_matched"] = f["rows_matched"].fillna(0)
    f["row_match_rate"] = np.where(f["our_rows"] > 0, f["rows_matched"] / f["our_rows"], np.nan)

    sec_only = set(agg_ds.index) - set(f["accession"])
    # report
    L = []
    both = f[f["in_secds"]]
    L.append(f"our filings: {len(f)}   in SEC data set: {len(both)}   ours not in SEC DS: {(~f['in_secds']).sum()}   SEC DS not in ours: {len(sec_only)}")
    tot_us = int(both["our_rows"].sum()); tot_m = int(both["rows_matched"].sum())
    L.append(f"filing-level exact match — rows: {both['rows_match'].mean()*100:.2f}%   shares: {both['shares_match'].mean()*100:.2f}%   value: {both['value_match'].mean()*100:.2f}%")
    L.append(f"row-level exact match on (cusip, shares, value): {tot_m}/{tot_us} = {tot_m/tot_us*100:.3f}%")
    allm = both[both["rows_match"] & both["shares_match"] & both["value_match"]]
    L.append(f"filings matching on all three: {len(allm)}/{len(both)} = {len(allm)/len(both)*100:.2f}%")
    L.append("\nmatch by our checksum status:")
    g = both.groupby("checksum_status").agg(n=("accession", "size"), rows=("rows_match", "mean"), shares=("shares_match", "mean"), value=("value_match", "mean"))
    L.append((g.assign(rows=g.rows*100, shares=g.shares*100, value=g.value*100).round(2)).to_string())
    L.append("\nmatch by our checksum cause (failing only):")
    g = both[both.checksum_status != "pass"].groupby("checksum_cause").agg(n=("accession", "size"), rows=("rows_match", "mean"), shares=("shares_match", "mean"), value=("value_match", "mean"))
    L.append((g.assign(rows=g.rows*100, shares=g.shares*100, value=g.value*100).round(2)).to_string())
    mism = both[~(both["rows_match"] & both["shares_match"] & both["value_match"])].copy()
    L.append(f"\nfilings with ANY mismatch vs SEC DS: {len(mism)}")
    if len(mism):
        mism["row_diff"] = mism["our_rows"] - mism["ds_rows"]
        mism["share_diff"] = mism["our_shares"] - mism["ds_shares"]
        mism["value_diff"] = mism["our_value"] - mism["ds_value"]
        L.append(mism[["accession", "manager_name", "our_rows", "ds_rows", "share_diff", "value_diff", "row_match_rate", "checksum_cause"]].head(40).to_string())
    return f, mism, "\n".join(L)


def run(label: str, year: int, qtr: int) -> str:
    cfg = cfgmod.load(); edgar = Edgar(cfg)
    ds = load_secds(edgar, year, qtr)
    cache = Path("cache/parsed")
    f = pd.read_parquet(cache / f"{label}_filings.parquet")
    h = pd.read_parquet(cache / f"{label}_holdings.parquet")
    if "cusip_raw" in h:            # compare what was PARSED (as filed) with the SEC's as-filed CUSIP, not our resolved one
        h = h.drop(columns=["cusip"]).rename(columns={"cusip_raw": "cusip"})
    h = h[["accession", "cusip", "shares", "value"]]
    per_filing, mism, txt = compare(f, h, ds)
    per_filing.to_parquet(cache / f"{label}_secds_compare.parquet", index=False)
    outdir = Path("output/problems") / label; outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "secds_compare.txt").write_text(txt)
    return txt


if __name__ == "__main__":
    print(run(sys.argv[1], int(sys.argv[2]), int(sys.argv[3])))
