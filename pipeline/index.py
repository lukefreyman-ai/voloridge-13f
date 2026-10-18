"""EDGAR full-index -> list of 13F filings."""
import io
import re
from datetime import date

import pandas as pd

from .edgar import Edgar, form_index_url

FORMS_13F = ("13F-HR", "13F-HR/A")


ROW_RE = re.compile(r"^(?P<form>\S+(?: \S+)*?)\s{2,}(?P<name>.*?)\s+(?P<cik>\d+)\s+(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<file>edgar/\S+)\s*$")


def parse_form_idx(raw: bytes, forms: tuple | None = None) -> pd.DataFrame:
    """form.idx is nominally fixed-width but long names overflow the columns,
    so parse each row from the right: file name, date, CIK are unambiguous."""
    text = raw.decode("latin-1")
    rows = []
    for l in text.splitlines():
        if forms and not l.startswith(forms):
            continue
        m = ROW_RE.match(l)
        if not m:
            continue
        rows.append((m["form"], m["name"].strip(), m["cik"], m["date"], m["file"]))
    df = pd.DataFrame(rows, columns=["form_type", "company_name", "cik", "date_filed", "file_name"])
    df["accession"] = df["file_name"].str.extract(r"(\d{10}-\d{2}-\d{6})\.txt$")
    return df


def filings_13f(edgar: Edgar, year: int, qtr: int) -> pd.DataFrame:
    df = parse_form_idx(edgar.get(form_index_url(year, qtr)), forms=FORMS_13F)
    df = df[df["form_type"].isin(FORMS_13F)].copy()
    df["cik"] = df["cik"].astype(int)
    df["date_filed"] = pd.to_datetime(df["date_filed"])
    df["index_year"] = year
    df["index_qtr"] = qtr
    return df.reset_index(drop=True)


def quarters_between(start: date, end: date):
    """(year, qtr) index quarters from start to end inclusive."""
    y, q = start.year, (start.month - 1) // 3 + 1
    while (y, q) <= (end.year, (end.month - 1) // 3 + 1):
        yield y, q
        q += 1
        if q == 5:
            y, q = y + 1, 1
