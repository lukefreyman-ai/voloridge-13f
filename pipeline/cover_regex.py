"""Cover-page regex fallback for shares outstanding, and its validation against XBRL facts.
For a 10-K/10-Q accession: fetch the filing index (index.json), take the primary document, strip tags,
and regex the cover-page sentence "... N shares of common stock ... outstanding as of <date>".
Every capture keeps the matched sentence as evidence.
  python3 -m pipeline.cover_regex test <label> <n>   sample n CIKs with an XBRL fact, compare; agreement must be >= 95%"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

from . import config as cfgmod
from .edgar import Edgar

NUM = r"(\d{1,3}(?:,\d{3})+|\d{6,})"
DATE = r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4})"
PATTERNS = [
    # "As of February 14, 2014, there were 891,989,000 shares of common stock outstanding"
    re.compile(rf"(?:as\s+of|at|on)\s+{DATE}[^.]{{0,120}}?{NUM}\s+(?:shares|common\s+shares)", re.I | re.S),
    # "891,989,000 shares of the registrant's common stock were outstanding as of February 14, 2014"
    re.compile(rf"{NUM}\s+shares[^.]{{0,160}}?outstanding[^.]{{0,60}}?(?:as\s+of|at|on)\s+{DATE}", re.I | re.S),
    # "Number of shares outstanding ... as of <date>: 891,989,000"
    re.compile(rf"outstanding[^.]{{0,80}}?(?:as\s+of|at|on)\s+{DATE}[^.]{{0,80}}?{NUM}", re.I | re.S),
]


def primary_doc_url(edgar: Edgar, cik: int, adsh: str) -> str | None:
    base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{adsh.replace('-', '')}"
    try:
        idx = json.loads(edgar.get(base + "/index.json"))
    except Exception:  # noqa
        return None
    items = idx.get("directory", {}).get("item", [])
    docs = [i["name"] for i in items if i["name"].lower().endswith((".htm", ".html", ".txt")) and "index" not in i["name"].lower()]
    # primary doc is usually the first .htm whose name carries the form (10k/10q) or just the first .htm
    pri = [d for d in docs if re.search(r"10-?[kq]", d.lower())] or [d for d in docs if d.lower().endswith((".htm", ".html"))] or docs
    return base + "/" + pri[0] if pri else None


COVER_END = re.compile(r"TABLE\s+OF\s+CONTENTS|\bPART\s+I\s*[-–—.]|\bITEM\s+1\s*[.:]\s*(?:BUSINESS|FINANCIAL)", re.I)
EXCLUDE_NEAR = re.compile(r"authoriz|treasury|preferred|held in|reserved|options|warrants|\bissued\b|par value", re.I)
THOUSANDS = re.compile(r"\(?\s*in\s+thousands\s*\)?", re.I)


def extract(text: str) -> dict | None:
    """Cover page only: the text before the table of contents / Part I. The sentence must mention
    'outstanding' and a date; sentences about authorized/treasury/preferred shares are skipped."""
    flat = re.sub(r"<[^>]+>", " ", text[:600000])
    flat = re.sub(r"&#160;|&nbsp;|&#xA0;|&#8217;|&#146;", " ", flat)
    flat = re.sub(r"\s+", " ", flat)
    m_end = COVER_END.search(flat, 2000)
    cover = flat[: m_end.start()] if m_end else flat[:80000]
    if len(cover) < 3000:
        cover = flat[:80000]
    for pat in PATTERNS:
        for m in pat.finditer(cover):
            g = m.groups()
            date, num = (g[0], g[1]) if re.search(r"\d{4}|/", g[0]) else (g[1], g[0])
            sent = cover[max(0, m.start() - 160): m.end() + 160]
            if EXCLUDE_NEAR.search(cover[max(0, m.start() - 60): m.end() + 60]):
                continue
            if not re.search(r"outstanding", sent, re.I):
                continue
            n = int(num.replace(",", ""))
            if THOUSANDS.search(cover[max(0, m.start() - 200): m.end() + 80]) and n < 50_000_000:
                n *= 1000
            if n < 100000:
                continue
            return {"shares": n, "asof_text": date, "evidence": sent[:320]}
    return None


def cover_shares(edgar: Edgar, cik: int, adsh: str) -> dict:
    url = primary_doc_url(edgar, cik, adsh)
    if not url:
        return {"cik": cik, "adsh": adsh, "status": "no primary doc"}
    try:
        text = edgar.get(url).decode("utf-8", "replace")
    except Exception as e:  # noqa
        return {"cik": cik, "adsh": adsh, "status": f"fetch error {type(e).__name__}"}
    r = extract(text)
    if not r:
        return {"cik": cik, "adsh": adsh, "status": "no match", "url": url}
    return {"cik": cik, "adsh": adsh, "status": "ok", "url": url, **r}


if __name__ == "__main__":
    cfg = cfgmod.load(); edgar = Edgar(cfg)
    cmd, label, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
    so = pd.read_parquet(f"cache/parsed/{label}_shares_out.parquet")
    so = so[(so["class_axis"] == "") & so["form"].isin(["10-K", "10-Q"])]
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 7
    sample = so.sample(n, random_state=seed)
    rows = []
    for i, r in enumerate(sample.itertuples(), 1):
        res = cover_shares(edgar, r.cik, r.adsh)
        res["xbrl_shares"] = r.shares; res["xbrl_asof"] = r.shares_outstanding_date; res["name"] = r.name
        rows.append(res)
        if i % 25 == 0:
            print(f"  {i}/{n}", flush=True)
    df = pd.DataFrame(rows)
    ok = df[df["status"] == "ok"].copy()
    ok["agree"] = (ok["shares"] - ok["xbrl_shares"]).abs() <= 0.005 * ok["xbrl_shares"]
    out = [f"{label}: cover-page regex vs XBRL dei:EntityCommonStockSharesOutstanding on {n} sampled 10-K/10-Q filings",
           "status: " + df["status"].value_counts().to_dict().__str__(),
           f"of matched: agree within 0.5% = {ok['agree'].sum()}/{len(ok)} = {ok['agree'].mean():.1%}" if len(ok) else "no matches",
           f"agreement over the whole sample (no match counts as disagree) = {ok['agree'].sum()}/{n} = {ok['agree'].sum() / n:.1%}"]
    bad = ok[~ok["agree"]]
    if len(bad):
        out.append("\ndisagreements:\n" + bad[["name", "adsh", "xbrl_shares", "shares", "asof_text", "evidence"]].head(15).to_string(index=False, max_colwidth=60))
    nm = df[df["status"] != "ok"]
    if len(nm):
        out.append("\nnon-matches:\n" + nm[["name", "adsh", "status"]].head(10).to_string(index=False, max_colwidth=40))
    txt = "\n".join(out)
    Path(f"output/problems/{label}").mkdir(parents=True, exist_ok=True)
    open(f"output/problems/{label}/cover_regex_test.txt", "w").write(txt)
    df.to_parquet(f"cache/parsed/{label}_cover_regex_test.parquet", index=False)
    print(txt)
