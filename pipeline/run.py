"""Download + parse all 13F-HR(/A) filings in an EDGAR index quarter."""
from __future__ import annotations

import gzip
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

from . import config as cfgmod
from .edgar import Edgar, submission_url
from .index import filings_13f
from .parse13f import parse_submission
from .problems import Problems
from . import checksum as checksummod
from . import cusip as cusipmod
from .seclist import load_13f_list


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def download_all(edgar: Edgar, idx: pd.DataFrame, workers: int) -> pd.DataFrame:
    urls = [submission_url(c, a) for c, a in zip(idx["cik"], idx["accession"])]
    todo = [u for u in urls if not edgar.is_cached(u)]
    log(f"download: {len(urls)} filings, {len(todo)} not cached")
    fails = {}
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(edgar.get, u): u for u in todo}
        for f in as_completed(futs):
            u = futs[f]
            try:
                f.result()
            except Exception as e:  # noqa
                fails[u] = str(e)[:200]
            done += 1
            if done % 250 == 0:
                log(f"  downloaded {done}/{len(todo)} (fail {len(fails)})")
    idx = idx.copy()
    idx["url"] = urls
    idx["download_error"] = idx["url"].map(fails).fillna("")
    log(f"download done, {len(fails)} failures")
    return idx


def _parse_one(args):
    path, accession = args
    try:
        with gzip.open(path, "rb") as f:
            text = f.read().decode("utf-8", "replace")
        p = parse_submission(text)
        if not p.accession:
            p.accession = accession
        rec = p.filing_record()
        h = p.holdings.copy()
        h.insert(0, "accession", p.accession)
        return rec, h
    except Exception as e:  # noqa
        return {"accession": accession, "errors": f"fatal: {type(e).__name__}: {str(e)[:200]}", "parse_method": "none", "n_rows": 0}, None


def parse_all(edgar: Edgar, idx: pd.DataFrame, workers: int):
    jobs = [(str(edgar.cache_path(u)), a) for u, a, err in zip(idx["url"], idx["accession"], idx["download_error"]) if not err]
    log(f"parse: {len(jobs)} filings on {workers} processes")
    recs, hs = [], []
    with Pool(workers) as pool:
        for i, (rec, h) in enumerate(pool.imap_unordered(_parse_one, jobs, chunksize=8), 1):
            recs.append(rec)
            if h is not None and len(h):
                hs.append(h)
            if i % 500 == 0:
                log(f"  parsed {i}/{len(jobs)}")
    filings = pd.DataFrame(recs)
    holdings = pd.concat(hs, ignore_index=True) if hs else pd.DataFrame()
    log(f"parse done: {len(filings)} filings, {len(holdings)} holdings rows")
    return filings, holdings


def period_quarter(year: int, qtr: int) -> tuple[int, int]:
    """EDGAR index quarter -> the report-period quarter it mostly covers (one earlier)."""
    return (year - 1, 4) if qtr == 1 else (year, qtr - 1)


def enrich(edgar: Edgar, label: str, year: int, qtr: int, filings: pd.DataFrame, holdings: pd.DataFrame):
    """Filing-level checksum status/cause + row-level CUSIP resolution. Rewrites both parquets.
    Holdings gain cusip_raw (as filed), cusip (resolved), cusip_status (see pipeline/cusip.py)."""
    out = edgar.cache / "parsed"
    filings = checksummod.assign(filings, holdings)
    filings.to_parquet(out / f"{label}_filings.parquet", index=False)
    log("checksum: " + ", ".join(f"{k}={v}" for k, v in filings["checksum_status"].value_counts().items()))
    if not len(holdings):
        return filings, holdings
    py, pq = period_quarter(year, qtr)
    try:
        sec_list, info = load_13f_list(edgar, py, pq)
        log(f"SEC 13(f) list {py}Q{pq}: {info['n_cusips']} CUSIPs")
    except Exception as e:  # noqa
        sec_list = None
        log(f"SEC 13(f) list {py}Q{pq}: unavailable ({type(e).__name__}: {str(e)[:80]}); universe = data only")
    raw = holdings["cusip_raw"] if "cusip_raw" in holdings else holdings["cusip"]
    universe = cusipmod.build_universe(raw, sec_list)
    res = cusipmod.resolve_series(raw, universe)
    holdings = holdings.drop(columns=[c for c in ("cusip_raw", "cusip", "cusip_status") if c in holdings])
    holdings.insert(3, "cusip_raw", res["cusip_raw"].values)
    holdings.insert(4, "cusip", res["cusip"].values)
    holdings.insert(5, "cusip_status", res["cusip_status"].values)
    holdings.to_parquet(out / f"{label}_holdings.parquet", index=False)
    log("cusip_status rows: " + ", ".join(f"{k}={v}" for k, v in holdings["cusip_status"].value_counts().items()))
    return filings, holdings


def summarize(filings: pd.DataFrame, idx: pd.DataFrame, problems: Problems) -> str:
    out = []
    f = filings.merge(idx[["accession", "form_type", "company_name", "date_filed"]], on="accession", how="left", suffixes=("", "_idx"))
    out.append(f"filings in index: {len(idx)}   downloaded: {(idx['download_error']=='').sum()}   parsed: {len(f)}")
    out.append("\nby form type:\n" + f["form_type_idx"].value_counts().to_string())
    out.append("\nby parse method:\n" + f["parse_method"].value_counts(dropna=False).to_string())
    out.append("\nby report type:\n" + f["report_type"].fillna("").value_counts().to_string())
    out.append("\nby period of report:\n" + f["period_of_report"].fillna("").value_counts().head(8).to_string())
    hr = f[f["report_type"].fillna("").str.upper() != "13F NOTICE"]
    out.append(f"\nholdings-bearing filings (not NOTICE): {len(hr)}")
    for col, nm in (("checksum_entries_ok", "entry-count checksum"), ("checksum_value_ok", "value-total checksum")):
        s = hr[col]
        known = s.notna().sum()
        ok = (s == True).sum()  # noqa
        out.append(f"{nm}: summary present {known}/{len(hr)}; pass {ok}/{known} = {ok/known*100 if known else 0:.1f}%")
    both = hr[(hr["checksum_entries_ok"] == True) & (hr["checksum_value_ok"] == True)]  # noqa
    out.append(f"both checksums pass: {len(both)}/{len(hr)} = {len(both)/len(hr)*100 if len(hr) else 0:.1f}%")
    out.append(f"zero holdings parsed (non-NOTICE): {(hr['n_rows']==0).sum()}")
    if "checksum_cause" in hr:
        out.append("\nchecksum status (pipeline/checksum.py):\n" + hr["checksum_status"].value_counts().to_string())
        out.append("\nchecksum cause, non-pass:\n" + hr.loc[hr["checksum_cause"] != "", "checksum_cause"].value_counts().to_string())
    errs = f["errors"].fillna("")
    errs = errs[errs != ""]
    out.append(f"\nfilings with parser errors: {len(errs)}")
    if len(errs):
        out.append("top error strings:\n" + errs.str.replace(r"\d+", "N", regex=True).value_counts().head(15).to_string())
    # checksum failure causes
    bad = hr[(hr["checksum_entries_ok"] == False) | (hr["checksum_value_ok"] == False)].copy()  # noqa
    if len(bad):
        bad["entry_diff"] = bad["n_rows"] - bad["entry_total"]
        bad["value_diff_pct"] = (bad["value_sum"] - bad["value_total"]) / bad["value_total"].replace(0, pd.NA) * 100
        def cause(r):
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
        if "checksum_cause" in bad:   # exhaustive classifier (pipeline/checksum.py) wins when present
            bad["cause"] = bad["checksum_cause"]
        else:                         # first-pass heuristic, kept for runs before enrich()
            bad["cause"] = bad.apply(cause, axis=1)
            out.append("\ncheck-sum failure causes (first-pass heuristic):\n" + bad["cause"].value_counts().to_string())
        for _, r in bad.iterrows():
            problems.add("checksum", r["accession"], r["cause"], f"rows={r['n_rows']} entry_total={r['entry_total']} value_sum={r['value_sum']} value_total={r['value_total']} method={r['parse_method']}")
    for _, r in f[f["errors"].fillna("") != ""].iterrows():
        problems.add("parse", r["accession"], r["errors"][:80], r.get("parse_method", ""))
    for _, r in idx[idx["download_error"] != ""].iterrows():
        problems.add("download", r["accession"], "download failed", r["download_error"])
    return "\n".join(out)


def run_quarter(year: int, qtr: int, label: str | None = None):
    cfg = cfgmod.load()
    edgar = Edgar(cfg)
    label = label or f"idx{year}Q{qtr}"
    out = Path(cfg["edgar"]["cache_dir"]) / "parsed"
    out.mkdir(parents=True, exist_ok=True)
    idx = filings_13f(edgar, year, qtr)
    log(f"index {year}Q{qtr}: {len(idx)} 13F-HR(/A) filings")
    idx = download_all(edgar, idx, cfg["edgar"]["workers"])
    filings, holdings = parse_all(edgar, idx, cfg["edgar"]["workers"])
    filings.to_parquet(out / f"{label}_filings.parquet", index=False)
    if len(holdings):
        holdings.to_parquet(out / f"{label}_holdings.parquet", index=False)
    idx.to_parquet(out / f"{label}_index.parquet", index=False)
    filings, holdings = enrich(edgar, label, year, qtr, filings, holdings)
    problems = Problems()
    summary = summarize(filings, idx, problems)
    problems.write(cfg["output_dir"] / "problems" / label, f"index {year}Q{qtr}")
    (out / f"{label}_summary.txt").write_text(summary)
    print("\n" + summary)
    return filings, holdings


def resummarize(label: str):
    cfg = cfgmod.load()
    out = Path(cfg["edgar"]["cache_dir"]) / "parsed"
    filings = pd.read_parquet(out / f"{label}_filings.parquet")
    idx = pd.read_parquet(out / f"{label}_index.parquet")
    problems = Problems()
    summary = summarize(filings, idx, problems)
    problems.write(cfg["output_dir"] / "problems" / label, label)
    (out / f"{label}_summary.txt").write_text(summary)
    print(summary)


def quarters_from_config():
    """EDGAR index quarters covering the configured report periods (index quarter = period quarter + 1)."""
    cfg = cfgmod.load()
    first = pd.Timestamp(cfg["sample"]["first_quarter_end"]); last = pd.Timestamp(cfg["sample"]["last_quarter_end"])
    out = []
    for q in pd.period_range(first, last, freq="Q"):
        nxt = q + 1
        out.append((nxt.year, nxt.quarter, f"{q.year}Q{q.quarter}"))
    return out


def run_all():
    """One quarter per child process: parse/enrich memory is released when the child exits,
    parquets and reports are on disk before the next quarter starts. Re-runs skip nothing but
    download from cache, so an interrupted run is simply re-run."""
    import subprocess
    for y, q, label in quarters_from_config():
        log(f"=== quarter {label} (index {y}Q{q}) ===")
        r = subprocess.run([sys.executable, "-m", "pipeline.run", str(y), str(q), label])
        if r.returncode != 0:
            log(f"quarter {label} FAILED (exit {r.returncode}); stopping")
            sys.exit(r.returncode)


def download_only(year: int, qtr: int):
    """Index + download into cache, no parsing. Used for the background pre-fetch of all quarters."""
    cfg = cfgmod.load()
    edgar = Edgar(cfg)
    idx = filings_13f(edgar, year, qtr)
    log(f"index {year}Q{qtr}: {len(idx)} 13F-HR(/A) filings")
    idx = download_all(edgar, idx, cfg["edgar"]["workers"])
    log(f"download {year}Q{qtr} done: failures {(idx['download_error'] != '').sum()}")


if __name__ == "__main__":
    if sys.argv[1] == "all":
        run_all()
    elif sys.argv[1] == "download":
        download_only(int(sys.argv[2]), int(sys.argv[3]))
    elif sys.argv[1] == "summary":
        resummarize(sys.argv[2])
    elif sys.argv[1] == "enrich":
        _label, _y, _q = sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
        _cfg = cfgmod.load(); _edgar = Edgar(_cfg)
        _out = Path(_cfg["edgar"]["cache_dir"]) / "parsed"
        enrich(_edgar, _label, _y, _q, pd.read_parquet(_out / f"{_label}_filings.parquet"),
               pd.read_parquet(_out / f"{_label}_holdings.parquet"))
        resummarize(_label)
    else:
        y, q = int(sys.argv[1]), int(sys.argv[2])
        run_quarter(y, q, sys.argv[3] if len(sys.argv) > 3 else None)
