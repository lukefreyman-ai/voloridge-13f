"""Evidence-based triage of every checksum failure in a pilot: parser miss vs filer error vs unknown.
Evidence per filing, recomputed from the raw text:
  n_rows          holdings the parser produced
  n_cusip_lines   lines carrying a CUSIP-looking token + >=2 numbers (parser's own count)
  n_shaped        lines that look like holdings (>=2 numbers + a discretion keyword), CUSIP or not
  entry_total     the filer's declared count
Usage: python3 scripts/triage_checksum.py pilot_2010Q1"""
import gzip, re, sys
sys.path.insert(0, ".")
import pandas as pd
from pipeline import config as c
from pipeline.edgar import Edgar, submission_url
from pipeline.parse13f import split_submission, html_to_lines

label = sys.argv[1]
ed = Edgar(c.load())
f = pd.read_parquet(f"cache/parsed/{label}_filings.parquet")
idx = pd.read_parquet(f"cache/parsed/{label}_index.parquet").set_index("accession")
SHAPED = re.compile(r"\b(SOLE|SHARED|DEFINED|DFND|OTHER)\b", re.I)
NUMS = re.compile(r"(?<![\w.])[\d,]{2,}(?![\w])")
SUMM = re.compile(r"entry\s+total|value\s+total", re.I)

def raw_lines(a):
    t = gzip.open(ed.cache_path(submission_url(idx.loc[a, "cik"], a))).read().decode("utf-8", "replace")
    h, docs = split_submission(t); main = [d for d in docs if d["type"].startswith("13F")] or docs
    ta = "\n".join(d["text"] for d in main)
    if re.search(r"<(html|tr|td)\b", ta, re.I):
        L = []; [L.extend(html_to_lines(d["text"])) for d in main]; return L, ta
    return re.sub(r"<[^>]+>", "", ta).splitlines(), ta

bad = f[(f["checksum_status"] != "pass") & (f["report_type"].str.upper() != "13F NOTICE")].copy()
rows = []
for r in bad.itertuples():
    L, ta = raw_lines(r.accession)
    shaped = sum(1 for l in L if SHAPED.search(l) and len(NUMS.findall(l)) >= 2)
    has_summ_words = bool(SUMM.search(re.sub(r"<[^>]+>", " ", ta)))
    rows.append({"accession": r.accession, "n_shaped": shaped, "summary_words_present": has_summ_words})
bad = bad.merge(pd.DataFrame(rows), on="accession")
ncl = bad["n_cusip_lines"].fillna(0)
et = bad["entry_total"]

def verdict(r):
    if r.checksum_status == "no_summary":
        return "info: summary page not found" + (" (words present, regex missed)" if r.summary_words_present else " (no entry/value total text)")
    if r.n_rows == 0:
        if r.n_cusip_lines == 0 and r.n_shaped == 0:
            return "parser: layout unrecognized (no CUSIP lines, no holding-shaped lines)"
        if r.n_cusip_lines == 0:
            return "parser: holding-shaped lines but no CUSIP token found"
        return "parser: CUSIP lines present, tails did not parse"
    if pd.notna(r.entry_total) and r.n_rows != r.entry_total:
        if r.n_cusip_lines > r.n_rows:
            return "parser: CUSIP lines unparsed (n_cusip_lines > n_rows)"
        if r.n_shaped > r.n_rows and r.n_cusip_lines <= r.n_rows:
            return "filer: holding lines without a CUSIP (n_shaped > n_rows)"
        if r.n_rows > r.entry_total:
            return "parser/filer: more rows than declared (dup or non-holding line captured)"
        return "filer: declared entry total disagrees with the lines present"
    if r.checksum_status == "fail_value":
        return "value: " + r.checksum_cause
    return "unknown"
bad["verdict"] = bad.apply(verdict, axis=1)
out = [f"{label}: {len(bad)} non-pass filings\n", bad["verdict"].value_counts().to_string(), ""]
for v, g in bad.groupby("verdict"):
    out.append(f"\n--- {v}  ({len(g)})")
    out.append(g[["accession", "manager_name", "parse_method", "n_rows", "n_cusip_lines", "n_shaped", "entry_total", "value_sum", "value_total", "checksum_cause"]]
               .head(6).to_string(index=False, max_colwidth=28))
txt = "\n".join(out)
open(f"output/problems/{label}/triage.txt", "w").write(txt)
bad.to_parquet(f"cache/parsed/{label}_triage.parquet", index=False)
print(txt[:7000])
