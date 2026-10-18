"""Crosstab of first-pass checksum causes (pipeline/run.py summarize) vs the
exhaustive classifier (pipeline/checksum.py) for one pilot. Shows exactly where
each failing filing moved, and reconstructs the early '37 unexplained entry /
~50 value' headline numbers from the first-pass rules."""
import sys
import numpy as np
import pandas as pd

label = sys.argv[1] if len(sys.argv) > 1 else "pilot_2013Q4"
f = pd.read_parquet(f"cache/parsed/{label}_filings.parquet")
hr = f[f["report_type"].fillna("").str.upper() != "13F NOTICE"].copy()
bad = hr[(hr["checksum_entries_ok"] == False) | (hr["checksum_value_ok"] == False)].copy()  # noqa

# --- first-pass rule, copied verbatim from run.py summarize() ---
bad["value_diff_pct"] = (bad["value_sum"] - bad["value_total"]) / bad["value_total"].replace(0, np.nan) * 100
def old_cause(r):
    if r["n_rows"] == 0:
        return "no rows parsed"
    if r["checksum_entries_ok"] == False and abs(r["entry_diff"]) <= 2:  # noqa
        return "entry count off by <=2"
    if r["checksum_entries_ok"] == False:  # noqa
        return "entry count off by >2 (parser miss or filer error)"
    vd = r["value_diff_pct"]
    if pd.isna(vd):
        return "value total unparseable"
    if abs(vd) < 1:
        return "value within 1% (rounding)"
    if 95 < abs(vd + 100) < 105 or abs(abs(vd) - 99900) < 200:
        return "value scale (x1000) mismatch"
    return "value off >1%"
bad["old_cause"] = bad.apply(old_cause, axis=1)

out = []
out.append(f"{label}: {len(bad)} checksum-failing filings (of {len(hr)} holdings-bearing)\n")
out.append("FIRST PASS (run.py) counts:\n" + bad["old_cause"].value_counts().to_string())
out.append("\nSECOND PASS (checksum.py) counts:\n" + bad["checksum_cause"].value_counts().to_string())
ct = pd.crosstab(bad["old_cause"], bad["checksum_cause"], margins=True)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
out.append("\nCROSSTAB rows = first pass, cols = second pass:\n" + ct.to_string())

# --- reconstruct the early headline numbers ---
e = bad[bad["checksum_entries_ok"] == False]  # noqa
more = e[e["entry_diff"] > 0]
less = e[e["entry_diff"] < 0]
out.append("\nENTRY failures: parsed MORE than declared = %d, parsed LESS = %d" % (len(more), len(less)))
explained_more = more[more["checksum_cause"].isin([
    "entry total counts distinct CUSIPs not rows", "summary fields swapped (entry total = value total)", "empty filing (single placeholder row, totals zero)", "summary totals zero but holdings present (filer omitted totals)"])]
out.append("  of the 'more' group, explained by distinct-CUSIP or swapped-summary: %d; unexplained: %d"
           % (len(explained_more), len(more) - len(explained_more)))
out.append("  second-pass 'entry count off by >2, unexplained' (both directions): %d; of which parsed MORE: %d, LESS: %d"
           % ((bad["checksum_cause"] == "entry count off by >2, unexplained").sum(),
              ((bad["checksum_cause"] == "entry count off by >2, unexplained") & (bad["entry_diff"] > 0)).sum(),
              ((bad["checksum_cause"] == "entry count off by >2, unexplained") & (bad["entry_diff"] < 0)).sum()))
v = bad[bad["old_cause"] == "value off >1%"]
out.append("\nVALUE: first pass 'value off >1%%' = %d. Where they went in the second pass:\n%s"
           % (len(v), v["checksum_cause"].value_counts().to_string()))
r = v["value_ratio"]
missed_scale = ((r > 900) & (r < 1100)) | ((r > 0.0009) & (r < 0.0011))
out.append("  first-pass scale heuristic missed %d true x1000 cases (ratio ~1000 or ~0.001); its rule keyed on"
           " value_diff_pct near -100 or near +99900, which fails when the sum side is the one scaled." % missed_scale.sum())

# per-filing movement list for anything that changed bucket meaningfully
moved = bad[bad["old_cause"] != bad["checksum_cause"]][
    ["accession", "manager_name", "n_rows", "n_distinct_cusip", "entry_total", "value_sum", "value_total", "value_ratio", "old_cause", "checksum_cause"]]
out.append(f"\nPER-FILING MOVES ({len(moved)} filings changed bucket):\n" + moved.sort_values(["old_cause", "checksum_cause"]).to_string(index=False, max_colwidth=40))
txt = "\n".join(out)
path = f"output/problems/{label}/checksum_reconciliation.txt"
open(path, "w").write(txt)
print(txt[:6000]); print("...\nwrote", path)
