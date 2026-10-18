"""SEC Official List of Section 13(f) Securities (quarterly PDF) -> set of CUSIPs."""
from __future__ import annotations

import re

import pymupdf  # already in anaconda

from .edgar import Edgar

URL = "https://www.sec.gov/divisions/investment/13f/13flist{y}q{q}.pdf"
ROW_RE = re.compile(r"\b([0-9A-Z]{6}) ([0-9A-Z]{2}) ([0-9])\b")


def load_13f_list(edgar: Edgar, year: int, qtr: int) -> tuple[set[str], dict]:
    """Return (set of 9-char CUSIPs, info). Rows marked with '*' have an option
    listed too; '+' means added this quarter. We only need the CUSIP."""
    data = edgar.get(URL.format(y=year, q=qtr))
    doc = pymupdf.open(stream=data, filetype="pdf")
    cusips = set()
    npages = len(doc)
    for page in doc:
        for a, b, c in ROW_RE.findall(page.get_text()):
            cusips.add(a + b + c)
    return cusips, {"pages": npages, "n_cusips": len(cusips), "bytes": len(data)}
