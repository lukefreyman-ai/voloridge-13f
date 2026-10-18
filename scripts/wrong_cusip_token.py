"""Diagnostic (read-only, 2026-10-11): rows whose resolved CUSIP is invalid/ambiguous/unconfirmed while the issuer or
class text carries a check-digit-valid 9-char CUSIP that is on the SEC 13(f) list for the quarter -> the parser took
the wrong 9-digit token (typically a 9-digit share count) as the CUSIP. Usage: python3 scripts/wrong_cusip_token.py <label> <list_year> <list_qtr>"""
import re, sys
sys.path.insert(0, ".")
import pandas as pd
from pipeline.cusip import is_valid9
from pipeline.seclist_names import load

label, ly, lq = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
sl = load(ly, lq); universe = set(sl["cusip"])
h = pd.read_parquet(f"cache/parsed/{label}_holdings.parquet", columns=["accession", "name_of_issuer", "title_of_class", "cusip_raw", "cusip", "cusip_status", "value", "shares"])
f = pd.read_parquet(f"cache/parsed/{label}_filings.parquet").set_index("accession")
bad = h[h["cusip_status"].isin(["invalid_9", "ambiguous", "unconfirmed_short"])].copy()
TOK = re.compile(r"(?<![0-9A-Z])([0-9A-Z]{6}[ -]?[0-9A-Z]{2}[ -]?[0-9A-Z])(?![0-9A-Z])")
def find(s):
    for m in TOK.finditer((s or "").upper()):
        t = m.group(1).replace(" ", "").replace("-", "")
        if re.search(r"\d", t) and is_valid9(t) and t in universe:
            return t
    return None
bad["cusip_in_text"] = (bad["name_of_issuer"].fillna("") + " | " + bad["title_of_class"].fillna("")).map(find)
hit = bad[bad["cusip_in_text"].notna()]
tot_rows = len(h)
# value comparison uses as-filed value (no scale normalization) -> order of magnitude only
per_f = hit.groupby("accession").agg(rows=("cusip", "size"), value=("value", "sum")).sort_values("rows", ascending=False)
per_f["manager"] = per_f.index.map(f["manager_name"]); per_f["method"] = per_f.index.map(f["parse_method"]); per_f["checksum"] = per_f.index.map(f["checksum_status"]); per_f["n_rows"] = per_f.index.map(f["n_rows"])
txt = (f"{label}: wrong-CUSIP-token rows (status invalid_9/ambiguous/unconfirmed_short but a valid 13(f)-list CUSIP sits in the text): "
       f"{len(hit):,} rows in {hit['accession'].nunique():,} filings ({len(hit) / tot_rows:.3%} of {tot_rows:,} rows); shares>0 on {int((hit['shares'] > 0).sum()):,} of them; "
       f"by parse method {hit['accession'].map(f['parse_method']).value_counts().to_dict()}\n"
       f"candidate rows checked {len(bad):,} by status {bad['cusip_status'].value_counts().to_dict()}\n"
       "filings with most such rows:\n" + per_f.head(10).to_string(max_colwidth=34) + "\nsample rows:\n" +
       hit.head(6)[["accession", "name_of_issuer", "title_of_class", "cusip_raw", "cusip_in_text", "value", "shares"]].to_string(index=False, max_colwidth=26))
open(f"output/problems/{label}/wrong_cusip_token.txt", "w").write(txt); print(txt.split("\n")[0])
