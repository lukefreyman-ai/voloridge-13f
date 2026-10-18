"""One place that turns a quarter label into every parameter the stages need, and says which cached inputs exist.
Labels: 'pilot_2013Q4' / 'pilot_2010Q1' (the two pilots) or a report-period label such as '2011Q2'.
  python3 -m pipeline.quarters [label ...]      prints the spec and the missing inputs for each label (default: all 20)
Conventions (as used for the pilots):
  index quarter   = the EDGAR full-index quarter after the report period (13F-HR is due 45 days after quarter end)
  13(f) list      = the SEC list for the report-period quarter (seclist_<y>q<q>.parquet from pipeline.seclist_names)
  13G/13D links   = SC 13G/13D filings of the period quarter and the index quarter (pilots: sc13_2010, sc13_2013)
  XBRL notes sets = the two SEC Financial Statement and Notes sets after the period (2013Q4 -> 2014q1 + 2014q2)
  SEC 13F data set = the index quarter's form13f zip (exists for 2013Q2 onward; cached for 2014q1 only)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

from . import config as cfgmod
from .edgar import Edgar, form_index_url
from .seclist import URL as LIST_URL
from .validate_secds import DS_URL

SC13_LABELS = {"pilot_2010Q1": "sc13_2010", "pilot_2013Q4": "sc13_2013"}
ALL_LABELS = ["pilot_2010Q1", "2010Q2", "2010Q3", "2010Q4", "2011Q1", "2011Q2", "2011Q3", "2011Q4", "2012Q1", "2012Q2",
              "2012Q3", "2012Q4", "2013Q1", "2013Q2", "2013Q3", "pilot_2013Q4", "2014Q1", "2014Q2", "2014Q3", "2014Q4"]
NOTES_URL = "https://www.sec.gov/files/dera/data/financial-statement-notes-data-sets/{y}q{q}_notes.zip"


def _shift(y: int, q: int, n: int) -> tuple[int, int]:
    p = pd.Period(f"{y}Q{q}", freq="Q") + n
    return p.year, p.quarter


def spec(label: str) -> dict:
    m = re.search(r"(\d{4})Q([1-4])$", label)
    if not m:
        raise ValueError(f"label {label!r} must end in YYYYQn")
    py, pq = int(m[1]), int(m[2])
    iy, iq = _shift(py, pq, 1)
    qend = pd.Period(f"{py}Q{pq}", freq="Q").end_time.normalize()
    n1, n2 = _shift(py, pq, 1), _shift(py, pq, 2)
    cfg = cfgmod.load(); edgar = Edgar(cfg)
    raw = edgar.cache / "raw"
    notes = [str(raw / "files" / "dera" / f"{y}q{q}_notes.zip") for y, q in (n1, n2)]
    return {
        "label": label, "period_year": py, "period_qtr": pq, "period": qend.strftime("%Y%m%d"),
        "quarter_end": qend.strftime("%Y-%m-%d"), "index_year": iy, "index_qtr": iq,
        "list_year": py, "list_qtr": pq, "sc13_label": SC13_LABELS.get(label, f"sc13_{py}Q{pq}"),
        "sc13_index_quarters": [(py, pq), (iy, iq)], "notes_zips": notes,
        "secds_available": (py, pq) >= (2013, 2),
        "inputs": {
            "form index": edgar.cache_path(form_index_url(iy, iq)),
            "13(f) list PDF": edgar.cache_path(LIST_URL.format(y=py, q=pq)),
            "13(f) list parquet": edgar.cache / "parsed" / f"seclist_{py}q{pq}.parquet",
            "13G/13D links": edgar.cache / "parsed" / f"{SC13_LABELS.get(label, f'sc13_{py}Q{pq}')}_sc13_links.parquet",
            "XBRL notes set 1": Path(notes[0]), "XBRL notes set 2": Path(notes[1]),
            "EDGAR full index 2010Q1-2015Q1": edgar.cache / "parsed" / "edgar_full_index_2010Q1_2015Q1.parquet",
            "fund CIKs": edgar.cache / "parsed" / "fund_ciks.parquet",
            "SEC 13F data set (validation only)": edgar.cache_path(DS_URL.format(y=iy, q=iq)),
        },
    }


def missing(s: dict) -> dict[str, str]:
    """Input name -> the command that creates it, for inputs not in the cache. The SEC data set is optional."""
    py, pq, iy, iq = s["period_year"], s["period_qtr"], s["index_year"], s["index_qtr"]
    how = {
        "form index": f"python3 -m pipeline.run download {iy} {iq}",
        "13(f) list PDF": f"python3 -m pipeline.seclist_names {py} {pq}",
        "13(f) list parquet": f"python3 -m pipeline.seclist_names {py} {pq}",
        "13G/13D links": f"python3 -m pipeline.sc13 download {py} {pq} {iy} {iq} && python3 -m pipeline.sc13 parse {s['sc13_label']} {py} {pq} {iy} {iq}",
        "XBRL notes set 1": "download " + NOTES_URL.format(y=_shift(py, pq, 1)[0], q=_shift(py, pq, 1)[1]) + " into cache/raw/files/dera/",
        "XBRL notes set 2": "download " + NOTES_URL.format(y=_shift(py, pq, 2)[0], q=_shift(py, pq, 2)[1]) + " into cache/raw/files/dera/",
        "EDGAR full index 2010Q1-2015Q1": "python3 -m pipeline.funds build",
        "fund CIKs": "python3 -m pipeline.funds build",
        "SEC 13F data set (validation only)": f"(optional) cache {DS_URL.format(y=iy, q=iq)}" if s["secds_available"] else "not published by the SEC for this quarter",
    }
    return {k: how[k] for k, p in s["inputs"].items() if not Path(p).exists()}


def shell_env(s: dict) -> str:
    """Shell assignments for the driver scripts: eval "$(python3 -m pipeline.quarters --env <label>)"."""
    return "\n".join([f"Q_LABEL={s['label']}", f"Q_PY={s['period_year']}", f"Q_PQ={s['period_qtr']}", f"Q_IY={s['index_year']}",
                      f"Q_IQ={s['index_qtr']}", f"Q_QEND={s['quarter_end']}", f"Q_PERIOD={s['period']}", f"Q_SC13={s['sc13_label']}",
                      f"Q_NOTES1={s['notes_zips'][0]}", f"Q_NOTES2={s['notes_zips'][1]}"])


if __name__ == "__main__":
    if sys.argv[1:2] == ["--env"]:
        print(shell_env(spec(sys.argv[2]))); sys.exit(0)
    for lab in sys.argv[1:] or ALL_LABELS:
        s = spec(lab); miss = missing(s)
        print(f"{lab}: index {s['index_year']}Q{s['index_qtr']}, quarter end {s['quarter_end']}, 13G/13D {s['sc13_label']}, "
              f"notes {[Path(z).stem for z in s['notes_zips']]}; missing inputs: {len(miss)}")
        for k, v in miss.items():
            print(f"    {k}: {v}")
