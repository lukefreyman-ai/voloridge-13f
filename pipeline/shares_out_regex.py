"""Regex cover-page fallback for shares outstanding (decision 4, 2026-10-11; 2026-10-12: 10-K only).
Only original 10-K / 10-KT filings are used: the 1,000-filing validation gave 96.6% precision on 10-K (n=264) vs
88.6% on 10-Q (n=70) within the deployable 45-day subset (output/problems/pilot_2013Q4/cover_regex_1000.txt).
Used ONLY for mapped operating companies with no XBRL dei:EntityCommonStockSharesOutstanding fact for the quarter,
and ONLY when the matched as-of date is within 45 days of the filing's own filing date (the deployable form of the
validated 45-day subset; see output/problems/pilot_2013Q4/cover_regex_1000.txt). Source is marked
'regex <form> <accession>' and the matched sentence is kept in the evidence column.
  python3 -m pipeline.shares_out_regex <label> <quarter_end YYYY-MM-DD>
Candidate filings: the company's original 10-K/10-Q/10-KT/10-QT in the EDGAR full index filed within [-100, +140]
days of the quarter end; filings after the quarter end are tried first (nearest first), then those before; the
first capture passing the 45-day gate is kept. gap_flag when |as-of - quarter end| > 100 days (same as the XBRL rule).
Output: cache/parsed/<label>_shares_out_regex.parquet (same columns as the XBRL table + evidence + asof_filed_gap),
cache/parsed/<label>_shares_out_regex_attempts.parquet (every CIK tried, with status), output/problems/<label>/shares_out_regex.txt"""
from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from . import config as cfgmod
from . import funds as fundsmod
from .cover_regex import cover_shares
from .edgar import Edgar

GATE_DAYS = 45
FORMS = ("10-K", "10-KT")          # 10-K only (Luke 2026-10-12)
WINDOW = (-100, 140)


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def parse_asof(s: str):
    return pd.to_datetime(str(s).replace(",", " ").strip(), errors="coerce")


def candidates(cik: int, tk: pd.DataFrame, qe: pd.Timestamp) -> list[tuple[str, str, pd.Timestamp]]:
    c = tk[tk["cik"] == cik]
    after = c[c["date_filed"] >= qe].sort_values("date_filed")
    before = c[c["date_filed"] < qe].sort_values("date_filed", ascending=False)
    return [(r.form_type, r.accession, r.date_filed) for r in pd.concat([after, before]).itertuples()]


def try_cik(edgar: Edgar, cik: int, cands: list, qe: pd.Timestamp) -> dict:
    if not cands:
        return {"cik": cik, "status": "no 10-K filed within the window"}
    last = "no match"
    for form, adsh, filed in cands:
        r = cover_shares(edgar, cik, adsh)
        if r.get("status") != "ok":
            last = r.get("status", "no match")
            continue
        asof = parse_asof(r["asof_text"])
        if pd.isna(asof):
            last = "as-of date unparseable"
            continue
        if abs((asof - filed).days) > GATE_DAYS:
            last = f"as-of more than {GATE_DAYS} days from filing date"
            continue
        gap = (asof - qe).days
        return {"cik": cik, "status": "ok", "form": form, "adsh": adsh, "filed": filed, "shares": float(r["shares"]),
                "shares_outstanding_date": asof.strftime("%Y-%m-%d"), "gap_days": gap, "gap_flag": abs(gap) > 100,
                "asof_filed_gap": (asof - filed).days, "evidence": r["evidence"], "url": r.get("url", "")}
    return {"cik": cik, "status": last}


def run(label: str, qend: str):
    cfg = cfgmod.load(); edgar = Edgar(cfg)
    qe = pd.Timestamp(qend)
    m = pd.read_csv(f"data/{label}_cusip_cik_map.csv", dtype={"cusip6": str, "cusip9": str})
    so = pd.read_parquet(f"cache/parsed/{label}_shares_out.parquet")
    h = pd.read_parquet(f"cache/parsed/{label}_holdings.parquet", columns=["cusip", "cusip_status", "put_call", "sh_prn"])
    h = h[(h["put_call"] == "") & (h["sh_prn"] != "PRN") & h["cusip_status"].isin(["ok", "repaired_check_digit", "repaired_pad_zeros"])]
    uni6 = set(h["cusip"].str[:6].unique())
    fund = set(fundsmod.load()["cik"])
    ciks = m[m["cusip6"].isin(uni6)].drop_duplicates("cusip6")
    names = ciks.drop_duplicates("company_cik").set_index("company_cik")["company_name"]
    ciks = set(ciks["company_cik"]) - fund
    missing = sorted(ciks - set(so["cik"]))
    idx = pd.read_parquet("cache/parsed/edgar_full_index_2010Q1_2015Q1.parquet")
    tk = idx[idx["form_type"].isin(FORMS)].copy()
    tk["date_filed"] = pd.to_datetime(tk["date_filed"])
    tk = tk[(tk["date_filed"] >= qe + pd.Timedelta(days=WINDOW[0])) & (tk["date_filed"] <= qe + pd.Timedelta(days=WINDOW[1]))]
    tk = tk[tk["cik"].isin(missing)]
    log(f"{label}: mapped operating companies {len(ciks):,}; with XBRL fact {len(ciks) - len(missing):,}; missing {len(missing):,}; "
        f"candidate 10-K filings in the window: {len(tk):,} on {tk['cik'].nunique():,} companies")
    rows = []
    with ThreadPoolExecutor(max_workers=cfg["edgar"]["workers"]) as ex:
        futs = {ex.submit(try_cik, edgar, c, candidates(c, tk, qe), qe): c for c in missing}
        for i, f in enumerate(as_completed(futs), 1):
            try:
                rows.append(f.result())
            except Exception as e:  # noqa
                rows.append({"cik": futs[f], "status": f"error {type(e).__name__}"})
            if i % 250 == 0:
                log(f"  {i}/{len(missing)}")
    att = pd.DataFrame(rows)
    att["name"] = att["cik"].map(names)
    ok = att[att["status"] == "ok"].copy()
    ok["class_axis"] = ""
    ok["shares_outstanding_source"] = "regex " + ok["form"] + " " + ok["adsh"]
    ok["source_set"] = "regex"
    cols = ["cik", "name", "class_axis", "shares", "shares_outstanding_source", "shares_outstanding_date", "form", "adsh", "filed", "gap_days", "gap_flag", "source_set", "evidence", "asof_filed_gap"]
    Path("cache/parsed").mkdir(exist_ok=True)
    ok[cols].to_parquet(f"cache/parsed/{label}_shares_out_regex.parquet", index=False)
    att.to_parquet(f"cache/parsed/{label}_shares_out_regex_attempts.parquet", index=False)
    out = [f"{label}: regex cover-page fallback, 10-K only, 45-day gate on |as-of - filing date|, quarter end {qend}",
           f"mapped operating companies {len(ciks):,}; missing an XBRL fact {len(missing):,}; regex captured {len(ok):,} = {len(ok) / max(len(missing), 1):.1%} of missing",
           "attempt status: " + att["status"].value_counts().to_dict().__str__(),
           "by form: " + ok["form"].value_counts().to_dict().__str__(),
           f"gap > 100 days flagged: {ok['gap_flag'].sum():,}; gap distribution (days): " + (ok["gap_days"].describe()[["min", "25%", "50%", "75%", "max"]].round(0).to_dict().__str__() if len(ok) else "{}"),
           "\nsample captures:\n" + ok.head(10)[["cik", "name", "form", "shares", "shares_outstanding_date", "evidence"]].to_string(index=False, max_colwidth=60)]
    txt = "\n".join(out); Path(f"output/problems/{label}").mkdir(parents=True, exist_ok=True)
    open(f"output/problems/{label}/shares_out_regex.txt", "w").write(txt); print(txt)


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
