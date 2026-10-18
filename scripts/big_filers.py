"""Stage 1: classify the largest failing filings of a pilot by value:
 (a) parse right, summary page wrong   rows parsed == CUSIP-bearing lines (+-2), shares-check flag share < 10%
 (b) rows missing                       parsed < declared-2 and raw evidence shows more lines than rows
 (c) rows wrong                         shares-check flag share >= 25%, or value far off with rows == declared
Also: value share of the pilot in filings that pass or are class (a). Usage: python3 scripts/big_filers.py <label> [N]"""
import sys
import numpy as np
import pandas as pd

label = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 20
f = pd.read_parquet(f"cache/parsed/{label}_filings.parquet")
tri = pd.read_parquet(f"cache/parsed/{label}_triage.parquet")[["accession", "n_shaped", "verdict"]]
sc = pd.read_parquet(f"cache/parsed/{label}_shares_check.parquet")
hb = f[f["report_type"].str.upper() != "13F NOTICE"].merge(tri, on="accession", how="left")
w = sc[sc["value_norm"] <= 2e8].groupby("accession")["value_norm"].sum()
fl = sc[sc["testable"]].groupby("accession")["flag"].agg(testable="size", flagged="sum")
hb["value_w"] = hb["accession"].map(w).fillna(0.0)
hb["value_scale_flag"] = hb["accession"].map(sc.groupby("accession")["value_scale_flag"].first()).fillna("")   # from the shares check (re-parses drop the column)
hb = hb.merge(fl, left_on="accession", right_index=True, how="left")
hb["flag_share"] = (hb["flagged"] / hb["testable"]).fillna(0.0)
hb["pass"] = hb["checksum_status"] == "pass"
ncl = hb["n_cusip_lines"].fillna(0); nsh = hb["n_shaped"].fillna(0)
rows_ok = (hb["n_rows"] - ncl).abs() <= 2
scale_like = hb["checksum_cause"].str.contains("scale|rounding|summary page missing|summary totals zero", regex=True)
def klass(r):
    if r["pass"]:
        return "pass"
    if r["flag_share"] >= 0.25:
        return "(c) rows wrong"
    missing = pd.notna(r["entry_total"]) and r["n_rows"] < r["entry_total"] - max(2, 0.005 * r["n_rows"])
    extra_lines = max(r["n_cusip_lines"] or 0, r["n_shaped"] or 0) > r["n_rows"] + 2
    if missing and extra_lines:
        return "(b) rows missing (parser)"
    if missing:
        return "(b) rows missing (filer: no CUSIP / declared total)"
    tol = max(2, 0.005 * r["n_rows"])     # a handful of odd lines in a 20k-row filing is not "rows wrong"
    if (abs(r["n_rows"] - (r["n_cusip_lines"] or 0)) <= tol or r["n_rows"] == r["entry_total"]) and r["flag_share"] < 0.10:   # 2026-10-12: rows == declared is itself the documented class (a) reason (n_cusip_lines undercounts "0  2 SH" lines)
        # class (a) check (Luke 2026-10-09): implied price cannot see missing rows, so the row count must
        # match the declared count, or there must be a documented reason; otherwise it is (b).
        et = r["entry_total"]
        if pd.isna(et) or et <= 0:
            return "(a) parse right, summary wrong [no declared count]"
        if r["n_rows"] == et:
            return "(a) parse right, summary wrong [rows == declared]"
        if r["n_rows"] > et:
            return "(a) parse right, summary wrong [rows > declared, nothing missing]"
        if abs(r["n_distinct_cusip"] - et) <= 2:
            return "(a) parse right, summary wrong [declared count = distinct CUSIPs]"
        if r["n_rows"] >= et - tol:
            return "(a) parse right, summary wrong [within 0.5% of declared]"
        return "(b) rows missing (unexplained: fewer rows than declared, all lines parsed)"
    return "(c) rows wrong"
hb["class"] = hb.apply(klass, axis=1)
tot = hb["value_w"].sum()
good = hb.loc[hb["class"].str.startswith(("pass", "(a)")), "value_w"].sum()
out = [f"{label}: value in filings that pass or are class (a): ${good/1e6:,.0f}bn / ${tot/1e6:,.0f}bn = {good/tot:.1%}",
       "by class (value share):"]
g = hb.groupby("class")["value_w"].agg(filings="size", value_bn=lambda s: s.sum()/1e6); g["share"] = (g["value_bn"]*1e6/tot).map("{:.1%}".format); g["value_bn"] = g["value_bn"].map("{:,.0f}".format)
out.append(g.to_string())
top = hb[~hb["pass"]].sort_values("value_w", ascending=False).head(N)
cols = ["accession", "manager_name", "n_rows", "n_cusip_lines", "n_shaped", "entry_total", "value_sum", "value_total", "value_scale_flag", "flag_share", "checksum_cause", "class"]
t = top[cols].copy(); t["value_sum"] = t["value_sum"].map("{:,.0f}".format); t["value_total"] = t["value_total"].map(lambda x: "" if pd.isna(x) else f"{x:,.0f}"); t["flag_share"] = t["flag_share"].map("{:.0%}".format)
t.insert(2, "value_bn", (top["value_w"]/1e6).map("{:,.1f}".format))
out.append(f"\n{N} largest non-pass filings by value:\n" + t.to_string(index=False, max_colwidth=26))
txt = "\n".join(out); open(f"output/problems/{label}/big_filers.txt", "w").write(txt); print(txt)
hb[["accession", "manager_name", "value_w", "class", "flag_share"]].to_parquet(f"cache/parsed/{label}_big_filers.parquet", index=False)
