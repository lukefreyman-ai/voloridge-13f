"""Evidence dump for one filing: header lines above the table, unparsed CUSIP/holding-shaped lines,
parsed rows with their source lines, and shares-check flagged rows. Usage: python3 scripts/show_filing.py <label> <accession> [n]"""
import gzip, re, sys
sys.path.insert(0, ".")
import pandas as pd
from pipeline import config as c
from pipeline.edgar import Edgar, submission_url
from pipeline.parse13f import split_submission, html_to_lines, parse_text_lines, parse_submission, CUSIP_RE, _norm_cusip, parse_tail, _split_csv_line, _line_candidates

label, acc = sys.argv[1], sys.argv[2]; n = int(sys.argv[3]) if len(sys.argv) > 3 else 6
ed = Edgar(c.load()); idx = pd.read_parquet(f"cache/parsed/{label}_index.parquet").set_index("accession")
t = gzip.open(ed.cache_path(submission_url(idx.loc[acc, "cik"], acc))).read().decode("utf-8", "replace")
p = parse_submission(t)
print(f"== {acc} {p.manager_name} | {p.parse_method} | rows {p.n_rows} cusip_lines {p.n_cusip_lines} entry {p.entry_total} val_sum {p.value_sum:,} val_tot {p.value_total} col_order={p.col_order} notes={p.notes}")
h, docs = split_submission(t); main = [d for d in docs if d["type"].startswith("13F")] or docs
ta = "\n".join(d["text"] for d in main)
if re.search(r"<(html|tr|td)\b", ta, re.I):
    L = []; [L.extend(html_to_lines(d["text"])) for d in main]
else:
    L = re.sub(r"<[^>]+>", "", ta).splitlines()
first = next((i for i, l in enumerate(L) if _line_candidates(l)[0]), None)
print("-- header block:")
if first is not None:
    for i in range(max(0, first - 8), first + 1): print(f"  {i:5d} |{L[i].rstrip()[:150]}")
SHAPED = re.compile(r"\b(SOLE|SHARED|DEFINED|DFND|OTHER)\b", re.I); NUMS = re.compile(r"(?<![\w.])[\d,]{2,}(?![\w])")
un = []
for l in L:
    ll = _split_csv_line(l.rstrip()); up = ll.upper()
    cands = [m for m in CUSIP_RE.finditer(up) if re.search(r"\d", _norm_cusip(*m.groups()))]
    shaped = SHAPED.search(ll) and len(NUMS.findall(ll)) >= 2
    if (cands or shaped) and not any(parse_tail(ll[m.end():]) for m in cands):
        un.append(ll)
print(f"-- unparsed CUSIP-bearing / holding-shaped lines: {len(un)}")
for l in un[:n]: print("  U |" + l.strip()[:150])
df, _ = parse_text_lines(L, keep_source=True)
print("-- parsed rows (source -> row):")
for _, r in df.head(3).iterrows():
    print("  S |" + r["_src"].strip()[:150]); print(f"  R | cusip={r['cusip']} value={r['value']} shares={r['shares']} {r['sh_prn']} {r['investment_discretion']}")
sc = pd.read_parquet(f"cache/parsed/{label}_shares_check.parquet"); x = sc[(sc.accession == acc) & sc.testable]
print(f"-- shares check: testable {len(x)} flagged {int(x.flag.sum())}; ratio median {x.ratio.median():.3f}; flagged ratio sample {list(x[x.flag].ratio.round(3).head(5))}")
