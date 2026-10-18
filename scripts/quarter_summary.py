"""Task B cross-quarter summary (2026-10-11): pass rates by count / rows / value per quarter, shares-check flag
rate, parse-method mix, and failure layouts not seen in the two pilots (with example filings).
Usage: python3 scripts/quarter_summary.py  -> output/problems/all_quarters_summary.txt, all_quarters_table.csv"""
import re
import numpy as np
import pandas as pd

ORDER = ["pilot_2010Q1", "2010Q2", "2010Q3", "2010Q4", "2011Q1", "2011Q2", "2011Q3", "2011Q4", "2012Q1", "2012Q2", "2012Q3", "2012Q4",
         "2013Q1", "2013Q2", "2013Q3", "pilot_2013Q4", "2014Q1", "2014Q2", "2014Q3", "2014Q4"]
PILOTS = {"pilot_2010Q1", "pilot_2013Q4"}
rows, causes, verdicts, errors, examples, bigs = [], {}, {}, {}, {}, {}
for label in ORDER:
    f = pd.read_parquet(f"cache/parsed/{label}_filings.parquet")
    hb = f[f["report_type"].str.upper() != "13F NOTICE"].copy()
    sc = pd.read_parquet(f"cache/parsed/{label}_shares_check.parquet", columns=["accession", "value_norm", "testable", "flag", "value_scale_flag"])
    w = sc[sc["value_norm"] <= 2e8].groupby("accession")["value_norm"].sum()
    hb["value_w"] = hb["accession"].map(w).fillna(0.0)
    hb["pass"] = hb["checksum_status"] == "pass"
    e, v = hb["entry_total"].notna(), hb["value_total"].notna()
    usable = e & v & (hb["entry_total"] > 0) & (hb["value_total"] > 0)
    t = sc[sc["testable"]]
    # second weight, immune to parser corruption: the filer's DECLARED value total, scale-normalized with the filing's
    # parsed/declared ratio (500-2000 -> declared is in thousands; 0.0005-0.002 -> declared is in dollars).
    vr = hb["value_ratio"]; dec = hb["value_total"].where(usable_mask := (hb["value_total"].fillna(0) > 0))
    dec = pd.Series(np.where((vr >= 0.0005) & (vr <= 0.002), dec / 1000.0, dec), index=hb.index)
    hb["value_dec"] = dec.fillna(0.0)
    implaus = ((hb["value_w"] > 3 * hb["value_dec"]) & (hb["value_dec"] > 0)) | (hb["value_w"] > 2e9)
    tri = pd.read_parquet(f"cache/parsed/{label}_triage.parquet", columns=["accession", "verdict"])
    big = pd.read_parquet(f"cache/parsed/{label}_big_filers.parquet")
    pm = hb["parse_method"].value_counts(normalize=True)
    err = f["errors"].fillna(""); err = err[err != ""].str.replace(r"\d+", "N", regex=True)
    rows.append({"quarter": label, "filings": len(f), "holdings_bearing": len(hb), "xml%": round(100 * pm.get("xml", 0), 1), "html%": round(100 * pm.get("html", 0), 1), "text%": round(100 * pm.get("text", 0), 1),
                 "pass_filings%": round(100 * hb["pass"].mean(), 1), "pass_usable%": round(100 * hb.loc[usable, "pass"].mean(), 1), "usable_n": int(usable.sum()),
                 "pass_rows%": round(100 * hb.loc[hb["pass"], "n_rows"].sum() / hb["n_rows"].sum(), 1), "pass_value%": round(100 * hb.loc[hb["pass"], "value_w"].sum() / hb["value_w"].sum(), 1),
                 "pass+classA_value%": round(100 * big.loc[big["class"].str.startswith(("pass", "(a)")), "value_w"].sum() / big["value_w"].sum(), 1),
                 "pass_value_plausible%": round(100 * hb.loc[hb["pass"] & ~implaus, "value_w"].sum() / hb.loc[~implaus, "value_w"].sum(), 1),
                 "pass+classA_plausible%": round(100 * hb.loc[hb["accession"].isin(big.loc[big["class"].str.startswith(("pass", "(a)")), "accession"]) & ~implaus, "value_w"].sum() / hb.loc[~implaus, "value_w"].sum(), 1),
                 "implausible_filings": int(implaus.sum()), "implausible_pass": int((implaus & hb["pass"]).sum()), "implausible_value_bn": round(hb.loc[implaus, "value_w"].sum() / 1e6, 0), "plausible_value_bn": round(hb.loc[~implaus, "value_w"].sum() / 1e6, 0),
                 "shares_flag%": round(100 * t["flag"].mean(), 2), "x1000_filings": int((sc.groupby("accession")["value_scale_flag"].first() == "x1000").sum()),
                 "no_rows": int((hb["n_rows"] == 0).sum()), "parse_errors": int(len(err)), "rows_total": int(hb["n_rows"].sum())})
    causes[label] = hb["checksum_cause"].replace("", "pass").value_counts()
    verdicts[label] = tri["verdict"].value_counts()
    errors[label] = err.value_counts()
    ex = hb.merge(tri, on="accession", how="left")
    examples[label] = ex
    bigs[label] = big.merge(hb[["accession", "parse_method", "n_rows", "entry_total", "checksum_cause"]], on="accession").sort_values("value_w", ascending=False)
tab = pd.DataFrame(rows).set_index("quarter")
tab.to_csv("output/problems/all_quarters_table.csv")
out = ["All 20 quarters, current parser (Task B 2026-10-11; pilots included for reference).",
       "pass_value% weights each filing by its PARSED row values (shares-check scale normalization, rows > $200bn excluded); corrupted filings inflate their own weight.",
       "implausible filings = parsed value > 3x the filer's declared total (scale-normalized) or > $2tn: their parsed values are corrupt and would inflate their own weight.",
       "pass_value_plausible% = the same pass rate with implausible filings removed from numerator and denominator (they are reported separately; declared totals are not usable as weights: many are in dollars or garbage).\n",
       tab[["filings", "holdings_bearing", "xml%", "text%", "pass_filings%", "pass_usable%", "pass_rows%", "pass_value%", "pass+classA_value%", "pass_value_plausible%", "pass+classA_plausible%", "shares_flag%"]].to_string(),
       "\n" + tab[["usable_n", "x1000_filings", "no_rows", "parse_errors", "rows_total", "implausible_filings", "implausible_pass", "implausible_value_bn", "plausible_value_bn"]].to_string()]
pil = lambda d: set().union(*(set(d[p].index) for p in PILOTS))
for name, d, key in (("checksum causes", causes, "checksum_cause"), ("triage verdicts", verdicts, "verdict"), ("parser error strings", errors, None)):
    known = pil(d)
    out.append(f"\n=== {name} NOT seen in either pilot ===")
    found = False
    for label in ORDER:
        if label in PILOTS:
            continue
        new = d[label][~d[label].index.isin(known)]
        for k, n in new.items():
            found = True
            if key:
                exs = examples[label][examples[label][key] == k].head(3)
            else:
                f = pd.read_parquet(f"cache/parsed/{label}_filings.parquet"); f["e"] = f["errors"].fillna("").str.replace(r"\d+", "N", regex=True); exs = f[f["e"] == k].head(3)
            out.append(f"{label}: {k!r} x{n}  examples: " + "; ".join(f"{a} ({m[:28]}, {pm})" for a, m, pm in zip(exs["accession"], exs["manager_name"], exs["parse_method"])))
    if not found:
        out.append("none")
out.append("\n=== per-quarter non-pass buckets (count) ===")
cause_tab = pd.DataFrame(causes).fillna(0).astype(int)
out.append(cause_tab.to_string())
out.append("\n=== per-quarter triage verdicts (count) ===")
out.append(pd.DataFrame(verdicts).fillna(0).astype(int).to_string())
out.append("\n=== three largest non-pass filings per quarter (by normalized value, $bn) with big_filers class ===")
for label in ORDER:
    b = bigs[label][bigs[label]["class"] != "pass"].head(3)
    for r in b.itertuples():
        out.append(f"{label:13} {r.accession} {r.manager_name[:30]:30} {r.value_w / 1e6:7.1f}  {r.parse_method:5} rows {r.n_rows:6} declared {'' if pd.isna(r.entry_total) else int(r.entry_total):>6}  {r.class_[:52] if hasattr(r, 'class_') else getattr(r, '_4')}")
txt = "\n".join(out); open("output/problems/all_quarters_summary.txt", "w").write(txt); print(txt[:9000])
