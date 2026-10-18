"""Checksum pass rate three ways: by filing count, by holdings rows, by reported value.
Value weight = parsed value_sum per filing, divided by 1000 when value_scale_flag == x1000
(filer reported dollars) or multiplied by 1000 for div1000, so dollar-filers do not dominate.
Also lists the 20 largest non-pass filings by that value with their bucket.
Usage: python3 scripts/weighted_pass.py <label>"""
import sys
import numpy as np
import pandas as pd

label = sys.argv[1]
f = pd.read_parquet(f"cache/parsed/{label}_filings.parquet")
hb = f[f["report_type"].str.upper() != "13F NOTICE"].copy()
# weight = sum of the filing's row values after the shares check's scale normalization
# (value_norm from <label>_shares_check.parquet: /1000 for filings whose implied prices say dollars),
# excluding rows above $200bn (glued digit runs in failing text filings). Declared totals are shown
# but not used: in 2010Q1 many are in dollars with no way to tell except through implied prices.
sc = pd.read_parquet(f"cache/parsed/{label}_shares_check.parquet", columns=["accession", "value_norm"])
sc = sc[sc["value_norm"] <= 2e8]
w = sc.groupby("accession")["value_norm"].sum()
hb["value_w"] = hb["accession"].map(w).fillna(0.0)
hb["weight_src"] = "rows, scale-normalized"
out0 = f"rows excluded from weights as glued digit runs (> $200bn): {(pd.read_parquet(f'cache/parsed/{label}_shares_check.parquet', columns=['value_norm'])['value_norm'] > 2e8).sum()}"
implaus = pd.Series(False, index=hb.index)
hb["pass"] = hb["checksum_status"] == "pass"
e, v = hb["entry_total"].notna(), hb["value_total"].notna()
usable = e & v & (hb["entry_total"] > 0) & (hb["value_total"] > 0)
out = [f"{label}: checksum pass rate weighted three ways (holdings-bearing filings = {len(hb)})",
       "value weight = filing's row values after shares-check scale normalization ($000), rows > $200bn excluded", out0, ""]
def block(d, title):
    out.append(f"{title}: filings {d['pass'].sum()}/{len(d)} = {d['pass'].mean():.1%} | "
               f"rows {d.loc[d['pass'], 'n_rows'].sum():,}/{d['n_rows'].sum():,} = {d.loc[d['pass'], 'n_rows'].sum() / d['n_rows'].sum():.1%} | "
               f"value ${d.loc[d['pass'], 'value_w'].sum() / 1e6:,.0f}bn/${d['value_w'].sum() / 1e6:,.0f}bn = {d.loc[d['pass'], 'value_w'].sum() / d['value_w'].sum():.1%}")
block(hb, "all holdings-bearing")
block(hb[usable], "usable summary page  ")
out.append("\nnon-pass buckets weighted:")
g = hb[~hb["pass"]].groupby("checksum_cause").agg(filings=("accession", "size"), rows=("n_rows", "sum"), value_bn=("value_w", lambda s: s.sum() / 1e6)).sort_values("value_bn", ascending=False)
g["rows_share"] = (g["rows"] / hb["n_rows"].sum()).map("{:.1%}".format)
g["value_share"] = (g["value_bn"] / (hb["value_w"].sum() / 1e6)).map("{:.1%}".format)
g["value_bn"] = g["value_bn"].map("{:,.1f}".format)
out.append(g.to_string())
top = hb[~hb["pass"]].sort_values("value_w", ascending=False).head(20)[
    ["accession", "manager_name", "parse_method", "n_rows", "entry_total", "value_sum", "value_total", "weight_src", "checksum_cause"]]
top["value_sum"] = top["value_sum"].map("{:,.0f}".format); top["value_total"] = top["value_total"].map(lambda x: "" if pd.isna(x) else f"{x:,.0f}")
out.append(f"\n20 largest non-pass filings by normalized value:\n" + top.to_string(index=False, max_colwidth=30))
if implaus.any():
    ip = hb[implaus][["accession", "manager_name", "n_rows", "entry_total", "value_sum", "value_total", "checksum_cause"]]
    ip["value_sum"] = ip["value_sum"].map("{:,.0f}".format)
    out.append("\nimplausible-weight filings (parsed sums with glued digit runs; parser work paused):\n" + ip.to_string(index=False, max_colwidth=30))
txt = "\n".join(out)
open(f"output/problems/{label}/weighted_pass.txt", "w").write(txt)
print(txt)
