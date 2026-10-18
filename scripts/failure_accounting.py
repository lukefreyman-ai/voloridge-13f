"""Exact, mutually exclusive filing counts for one pilot, summing to the index total, and the
checksum pass rate two ways. Usage: python3 scripts/failure_accounting.py <label>"""
import sys
import pandas as pd

label = sys.argv[1]
f = pd.read_parquet(f"cache/parsed/{label}_filings.parquet")
n = len(f)
notice = f["report_type"].str.upper().eq("13F NOTICE")
hb = f[~notice]
out = [f"{label}: {n} filings in the EDGAR index (13F-HR and 13F-HR/A)\n",
       "Definitions: 'pass' = every summary total that is present on the filing matches the parsed holdings",
       "(entry count exactly; value total within 0.1%). A filing with only one total present can pass on that one.",
       "'usable summary page' = both totals present and > 0.\n"]
out.append(f"13F NOTICE (no holdings by design)            {notice.sum():5d}")
out.append(f"holdings-bearing                               {len(hb):5d}")
out.append(f"                                              -----\n  sum                                         {notice.sum() + len(hb):5d}  == {n}\n")
out.append("Holdings-bearing filings, one bucket each (checksum_cause from pipeline/checksum.py):")
vc = hb["checksum_cause"].replace("", "pass: all present totals match").value_counts()
for k, v in vc.items():
    out.append(f"  {v:5d}  {k}")
out.append(f"  -----\n  {vc.sum():5d}  == {len(hb)}\n")
e, v = hb["entry_total"].notna(), hb["value_total"].notna()
us = hb[e & v & (hb["entry_total"] > 0) & (hb["value_total"] > 0)]
out.append("Summary page presence (holdings-bearing):")
out.append(f"  both totals present and >0 (usable)   {len(us):5d}")
out.append(f"  both present, one or both == 0        {(e & v).sum() - len(us):5d}")
out.append(f"  entry total only                      {(e & ~v).sum():5d}")
out.append(f"  value total only                      {(~e & v).sum():5d}")
out.append(f"  neither                               {(~e & ~v).sum():5d}")
out.append(f"  -----\n  sum                                   {len(hb):5d}\n")
p_all = (hb["checksum_status"] == "pass").sum()
both = ((hb["checksum_entries_ok"] == True) & (hb["checksum_value_ok"] == True)).sum()  # noqa
p_us = (us["checksum_status"] == "pass").sum()
both_us = ((us["checksum_entries_ok"] == True) & (us["checksum_value_ok"] == True)).sum()  # noqa
out.append("Pass rate:")
out.append(f"  over ALL {n} index filings:                     pass {p_all:5d}  = {p_all / n:.1%}   (both totals match: {both:5d} = {both / n:.1%})")
out.append(f"  over {len(hb)} holdings-bearing filings:          pass {p_all:5d}  = {p_all / len(hb):.1%}   (both totals match: {both:5d} = {both / len(hb):.1%})")
out.append(f"  over {len(us)} usable-summary filings:            pass {p_us:5d}  = {p_us / len(us):.1%}   (both totals match: {both_us:5d} = {both_us / len(us):.1%})")
out.append(f"    entry total matches among usable:  {(us['checksum_entries_ok'] == True).sum():5d} = {(us['checksum_entries_ok'] == True).mean():.1%}")  # noqa
out.append(f"    value total matches among usable:  {(us['checksum_value_ok'] == True).sum():5d} = {(us['checksum_value_ok'] == True).mean():.1%}")  # noqa
txt = "\n".join(out)
open(f"output/problems/{label}/failure_accounting.txt", "w").write(txt)
print(txt)
