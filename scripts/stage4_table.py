"""Stage 4 cross-quarter table (Luke 2026-10-15): per quarter, % of 13F value matched to a company, % of value with
shares outstanding, median ownership, count over 100% (and the top-500 rate), each read from
output/problems/<label>/ownership_report.txt. Quarters out of line with the two pilots are flagged.
Usage: python3 scripts/stage4_table.py -> output/problems/stage4_table.csv, stage4_table.txt"""
import re
from pathlib import Path
import pandas as pd
ORDER = ["pilot_2010Q1", "2010Q2", "2010Q3", "2010Q4", "2011Q1", "2011Q2", "2011Q3", "2011Q4", "2012Q1", "2012Q2", "2012Q3", "2012Q4",
         "2013Q1", "2013Q2", "2013Q3", "pilot_2013Q4", "2014Q1", "2014Q2", "2014Q3", "2014Q4"]
PILOTS = ["pilot_2010Q1", "pilot_2013Q4"]
num = lambda x: float(x.replace(",", ""))
rows = []
for lab in ORDER:
    p = Path(f"output/problems/{lab}/ownership_report.txt")
    if not p.exists():
        rows.append({"quarter": lab, "status": "not run"}); continue
    t = p.read_text()
    m1 = re.search(r"coverage among OPERATING companies.*?: ([\d,]+) / ([\d,]+) = ([\d.]+)%; by value ([\d.]+)%", t)
    m2 = re.search(r"shares outstanding \(.*?\): companies with a figure ([\d,]+) / ([\d,]+) = ([\d.]+)%; by 13F value ([\d.]+)%", t)
    m3 = re.search(r"ownership pct distribution \(n=([\d,]+)\): \{.*?'50%': ([\d.]+)", t)
    m4 = re.search(r"companies over 100%: ([\d,]+) / ([\d,]+) = ([\d.]+)%", t)
    m5 = re.search(r"large companies \(top 500 by 13F value\) with a pct: ([\d,]+); over 100%: ([\d,]+) = ([\d.]+)%", t)
    rows.append({"quarter": lab, "status": "ok",
                 "issuers_matched_pct": num(m1[3]), "value_matched_pct": num(m1[4]),
                 "companies_with_shares_out": int(num(m2[1])), "mapped_companies": int(num(m2[2])), "value_with_shares_out_pct": num(m2[4]),
                 "companies_with_pct": int(num(m3[1])), "median_ownership_pct": num(m3[2]),
                 "over_100_count": int(num(m4[1])), "over_100_pct": num(m4[3]),
                 "top500_with_pct": int(num(m5[1])), "top500_over_100": int(num(m5[2])), "top500_over_100_pct": num(m5[3])})
tab = pd.DataFrame(rows).set_index("quarter")
ok = tab[tab["status"] == "ok"]
pil = ok.loc[[p for p in PILOTS if p in ok.index]]
def flags(r):
    f = []
    if r["value_matched_pct"] < pil["value_matched_pct"].min() - 3: f.append(f"value matched {r['value_matched_pct']}% < pilots' {pil['value_matched_pct'].min()}% - 3")
    if r["value_with_shares_out_pct"] < pil["value_with_shares_out_pct"].min() - 5: f.append(f"value with shares out {r['value_with_shares_out_pct']}% < pilots' {pil['value_with_shares_out_pct'].min()}% - 5")
    lo, hi = pil["median_ownership_pct"].min() - 10, pil["median_ownership_pct"].max() + 10
    if not lo <= r["median_ownership_pct"] <= hi: f.append(f"median {r['median_ownership_pct']}% outside pilots' {lo:.1f}-{hi:.1f}")
    if r["over_100_pct"] > pil["over_100_pct"].max() + 2: f.append(f"over-100% share {r['over_100_pct']}% > pilots' {pil['over_100_pct'].max()}% + 2")
    if r["top500_over_100_pct"] > pil["top500_over_100_pct"].max(): f.append(f"top-500 over-100% {r['top500_over_100_pct']}% > pilots' max {pil['top500_over_100_pct'].max()}%")
    elif r["top500_over_100_pct"] > 5: f.append(f"top-500 over-100% {r['top500_over_100_pct']}% above the 5% stop line (below the accepted 2013Q4 rate)")
    return "; ".join(f)
tab["flag"] = [flags(r) if r["status"] == "ok" and lab not in PILOTS else "" for lab, r in tab.iterrows()]
tab.to_csv("output/problems/stage4_table.csv")
view = tab[["value_matched_pct", "value_with_shares_out_pct", "median_ownership_pct", "over_100_count", "over_100_pct", "top500_over_100_pct", "flag"]]
txt = ("Stage 4 by quarter (from output/problems/<label>/ownership_report.txt); pilots are the reference rows\n" + view.to_string() +
       f"\n\nflagged quarters: {int((tab['flag'] != '').sum())}; not run: {int((tab['status'] != 'ok').sum())}")
Path("output/problems/stage4_table.txt").write_text(txt); print(txt)
