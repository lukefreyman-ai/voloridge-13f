"""Quarters below the 85% text-era target: top failure causes by value. Usage: python3 scripts/below_target_causes.py"""
import pandas as pd
ta = pd.read_csv("output/problems/all_quarters_table.csv").set_index("quarter")
below = ta[(ta["pass+classA_plausible%"] < 85) & (ta["text%"] > 50)].index
out = []
for q in below:
    big = pd.read_parquet(f"cache/parsed/{q}_big_filers.parquet")
    f = pd.read_parquet(f"cache/parsed/{q}_filings.parquet")[["accession", "parse_method", "n_rows", "n_cusip_lines", "entry_total", "value_total", "value_sum", "checksum_cause", "value_ratio"]]
    b = big.merge(f, on="accession")
    implaus = ((b["value_w"] > 3 * b["value_total"].fillna(0) / b["value_ratio"].where((b["value_ratio"] >= 0.0005) & (b["value_ratio"] <= 0.002), 1).fillna(1)) & (b["value_total"].fillna(0) > 0)) | (b["value_w"] > 2e9)
    b = b[~implaus]
    tot = b["value_w"].sum()
    g = b.groupby("class")["value_w"].agg(filings="size", value_bn=lambda s: s.sum() / 1e6)
    g["share%"] = (100 * g["value_bn"] * 1e6 / tot).round(1)
    out.append(f"=== {q}: pass+classA (plausible) {ta.loc[q, 'pass+classA_plausible%']}%; plausible value ${tot / 1e6:,.0f}bn\n" + g.round(1).sort_values("value_bn", ascending=False).to_string())
    top = b[~b["class"].str.startswith(("pass", "(a)"))].sort_values("value_w", ascending=False).head(8)
    out.append("top failing filings (plausible weight):\n" + top.assign(value_bn=(top["value_w"] / 1e6).round(1))[["accession", "manager_name", "value_bn", "n_rows", "n_cusip_lines", "entry_total", "flag_share", "checksum_cause", "class"]].to_string(index=False, max_colwidth=30) + "\n")
txt = "\n".join(out); open("output/problems/below_target_causes.txt", "w").write(txt); print(txt)
