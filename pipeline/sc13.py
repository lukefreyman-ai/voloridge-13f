"""Schedule 13G / 13D filings -> CUSIP -> subject-company CIK links (Phase 2a).
Every SC 13G/13D(/A) names the subject company in its SEC header (CENTRAL INDEX KEY under
SUBJECT COMPANY) and prints the security's CUSIP on the cover page. We keep every link with its
evidence (accession, filed date, form) and resolve by 6-char issuer prefix later.
  python3 -m pipeline.sc13 download <y> <q> [...]   list + download the filings of EDGAR index quarters
  python3 -m pipeline.sc13 parse <label> <y> <q> [...]   parse cached filings -> cache/parsed/<label>_sc13_links.parquet"""
from __future__ import annotations

import gzip
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from . import config as cfgmod
from .edgar import Edgar, submission_url
from .index import parse_form_idx, form_index_url

FORMS = ("SC 13G", "SC 13G/A", "SC 13D", "SC 13D/A")
CUSIP_NEAR = re.compile(r"(?i)cusip\s*(?:no\.?|number|#|:)?[^0-9A-Z]{0,40}([0-9A-Z]{6}[ -]?[0-9A-Z]{2}[ -]?[0-9A-Z])(?![0-9A-Z])")
CUSIP_ANY = re.compile(r"(?<![0-9A-Z])([0-9A-Z]{6}[ -]?[0-9A-Z]{2}[ -]?[0-9A-Z])(?![0-9A-Z])")
SUBJECT = re.compile(r"SUBJECT COMPANY:.*?COMPANY CONFORMED NAME:\s*(.+?)\n.*?CENTRAL INDEX KEY:\s*(\d+)", re.S)
FILER = re.compile(r"FILED BY:.*?COMPANY CONFORMED NAME:\s*(.+?)\n.*?CENTRAL INDEX KEY:\s*(\d+)", re.S)


def log(*a):
    import time
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def listing(edgar: Edgar, year: int, qtr: int) -> pd.DataFrame:
    df = parse_form_idx(edgar.get(form_index_url(year, qtr)), forms=FORMS)
    df = df.drop_duplicates("accession")        # one row per filing (the index lists filer and subject rows)
    df["index_quarter"] = f"{year}Q{qtr}"
    return df


def download(edgar: Edgar, df: pd.DataFrame, workers: int):
    urls = [submission_url(c, a) for c, a in zip(df["cik"], df["accession"])]
    todo = [u for u in urls if not edgar.is_cached(u)]
    log(f"SC 13G/13D: {len(urls)} filings, {len(todo)} to download")
    done = fails = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(edgar.get, u): u for u in todo}
        for f in as_completed(futs):
            try:
                f.result()
            except Exception as e:  # noqa
                fails += 1
            done += 1
            if done % 1000 == 0:
                log(f"  {done}/{len(todo)} (fail {fails})")
    log(f"download done, {fails} failures")


def parse_one(path: str) -> dict:
    try:
        t = gzip.open(path).read().decode("latin-1")
    except Exception as e:  # noqa
        return {"error": f"read: {e}"}
    hdr = t[:6000]
    m = SUBJECT.search(hdr)
    fm = FILER.search(hdr)
    body = re.sub(r"<[^>]+>", " ", t[:60000])
    body = re.sub(r"&#160;|&nbsp;", " ", body)
    near = [x.replace(" ", "").replace("-", "").upper() for x in CUSIP_NEAR.findall(body)]
    cusip = next((x for x in near if re.search(r"\d", x) and len(x) == 9), None)
    return {"subject_name": m.group(1).strip() if m else None, "subject_cik": int(m.group(2)) if m else None,
            "filer_name": fm.group(1).strip() if fm else None, "filer_cik": int(fm.group(2)) if fm else None,
            "cusip": cusip, "n_cusip_mentions": len(near), "cusip_near_all": "|".join(sorted(set(near))[:5])}


def parse_all(edgar: Edgar, df: pd.DataFrame, workers: int) -> pd.DataFrame:
    from multiprocessing import Pool
    paths = [str(edgar.cache_path(submission_url(c, a))) for c, a in zip(df["cik"], df["accession"])]
    recs = []
    with Pool(workers) as pool:
        for i, r in enumerate(pool.imap(parse_one, paths, chunksize=32), 1):
            recs.append(r)
            if i % 5000 == 0:
                log(f"  parsed {i}/{len(paths)}")
    out = pd.concat([df.reset_index(drop=True), pd.DataFrame(recs)], axis=1)
    return out


if __name__ == "__main__":
    cfg = cfgmod.load()
    edgar = Edgar(cfg)
    cmd = sys.argv[1]
    if cmd == "download":
        for y, q in zip(sys.argv[2::2], sys.argv[3::2]):
            df = listing(edgar, int(y), int(q))
            log(f"index {y}Q{q}: {len(df)} SC 13G/13D filings")
            download(edgar, df, cfg["edgar"]["workers"])
    elif cmd == "parse":
        label = sys.argv[2]
        dfs = [listing(edgar, int(y), int(q)) for y, q in zip(sys.argv[3::2], sys.argv[4::2])]
        df = pd.concat(dfs, ignore_index=True)
        out = parse_all(edgar, df, cfg["edgar"]["workers"])
        Path("cache/parsed").mkdir(exist_ok=True)
        out.to_parquet(f"cache/parsed/{label}_sc13_links.parquet", index=False)
        log(f"{label}: {len(out)} filings parsed; with subject CIK {out['subject_cik'].notna().sum()}, with CUSIP {out['cusip'].notna().sum()}")
