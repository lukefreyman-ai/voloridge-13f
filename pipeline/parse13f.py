"""Parse a full 13F submission (.txt) into header + summary + holdings.

Three holdings formats, one interface:
  xml  : 2013Q2 onward, <informationTable> XML document
  html : HTML tables (rows converted to text lines, then line parser)
  text : plain / fixed-width text (line parser)
"""
from __future__ import annotations

import collections
import re
from dataclasses import dataclass, field

import pandas as pd

from .cusip import is_valid9
from lxml import etree

HOLDING_COLS = [
    "name_of_issuer", "title_of_class", "cusip", "value", "shares", "sh_prn",
    "put_call", "investment_discretion", "other_managers",
    "voting_sole", "voting_shared", "voting_none",
    "inherited_cusip",   # 1 = continuation sub-row that took issuer/class/CUSIP from the row above (text filings)
]


@dataclass
class Parsed:
    accession: str = ""
    form_type: str = ""
    period_of_report: str = ""
    filed_date: str = ""
    manager_cik: int | None = None
    manager_name: str = ""
    filer_ciks: list = field(default_factory=list)
    report_type: str = ""
    amendment_type: str = ""
    amendment_no: str = ""
    entry_total: int | None = None
    value_total: int | None = None
    other_managers_count: int | None = None
    other_managers: list = field(default_factory=list)   # (seq, cik, name)
    parse_method: str = ""
    holdings: pd.DataFrame | None = None
    errors: list = field(default_factory=list)
    notes: list = field(default_factory=list)     # parser corrections with evidence (not errors)
    col_order: list | None = None                 # numeric column order read from the header (text filings)
    n_rows: int = 0
    n_cusip_lines: int | None = None   # text/html: lines carrying a 9-char CUSIP-looking token (evidence for checksum triage)
    value_sum: int | None = None
    checksum_entries_ok: bool | None = None
    checksum_value_ok: bool | None = None

    def filing_record(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k not in ("holdings", "other_managers", "filer_ciks", "errors", "notes", "col_order")}
        d["col_order"] = ",".join(self.col_order) if self.col_order else ""
        d["notes"] = " || ".join(self.notes)
        d["other_managers"] = ";".join(f"{s}|{c}|{n}" for s, c, n in self.other_managers)
        d["filer_ciks"] = ";".join(str(c) for c in self.filer_ciks)
        d["errors"] = " || ".join(self.errors)
        return d


# ---------------------------------------------------------------- submission

DOC_RE = re.compile(r"<DOCUMENT>(.*?)</DOCUMENT>", re.S)
TAG_RE = re.compile(r"^<(TYPE|SEQUENCE|FILENAME|DESCRIPTION)>(.*)$", re.M)


def split_submission(text: str):
    hdr_m = re.search(r"<SEC-HEADER>(.*?)</SEC-HEADER>", text, re.S)
    header = hdr_m.group(1) if hdr_m else text[:5000]
    docs = []
    for m in DOC_RE.finditer(text):
        body = m.group(1)
        meta = dict((k, v.strip()) for k, v in TAG_RE.findall(body.split("<TEXT>", 1)[0]))
        tm = re.search(r"<TEXT>(.*?)(?:</TEXT>|$)", body, re.S)
        docs.append({"type": meta.get("TYPE", ""), "filename": meta.get("FILENAME", ""), "text": tm.group(1) if tm else ""})
    return header, docs


def _hget(header: str, key: str) -> str:
    m = re.search(rf"^\s*{re.escape(key)}:\s*(.*)$", header, re.M)
    return m.group(1).strip() if m else ""


def parse_header(header: str, p: Parsed):
    p.accession = _hget(header, "ACCESSION NUMBER")
    p.form_type = _hget(header, "CONFORMED SUBMISSION TYPE")
    p.period_of_report = _hget(header, "CONFORMED PERIOD OF REPORT")
    p.filed_date = _hget(header, "FILED AS OF DATE")
    # first FILER block is the filing manager
    names = re.findall(r"COMPANY CONFORMED NAME:\s*(.*)", header)
    ciks = re.findall(r"CENTRAL INDEX KEY:\s*(\d+)", header)
    if names:
        p.manager_name = names[0].strip()
    if ciks:
        p.manager_cik = int(ciks[0])
        p.filer_ciks = [int(c) for c in ciks]


# ---------------------------------------------------------------- XML

def _xml_root(text: str):
    m = re.search(r"<XML>(.*?)</XML>", text, re.S)
    xml = (m.group(1) if m else text).strip()
    xml = re.sub(r"^<\?xml[^>]*\?>", "", xml).strip()
    parser = etree.XMLParser(recover=True, huge_tree=True)
    return etree.fromstring(xml.encode("utf-8", "replace"), parser)


def _ln(el, name: str) -> str:
    """text of first descendant with local-name == name"""
    r = el.xpath(f".//*[local-name()='{name}']")
    return (r[0].text or "").strip() if r else ""


def _to_int(s: str) -> int | None:
    s = (s or "").replace(",", "").replace("$", "").strip()
    if s in ("", "-", "--"):
        return None
    if len(s.split(".")[0]) > 15:      # no 13F value/share count has 16+ digits: a glued digit run (fixture text_digit_run_overflow_2010)
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


_CSV_DELIM = re.compile(r",(?!\d{3}(?!\d))")   # a comma that is NOT a thousands separator


def _split_csv_line(line: str) -> str:
    """Comma-DELIMITED holdings lines (fixture text_digit_run_overflow_2010: 'TIME WARNER INC,COM NEW,887317303,1533,49000, ,SH,,SOLE')
    become space-separated cells so commas are not read as thousands separators. Lines whose commas
    are only digit grouping are returned unchanged."""
    if line.count(",") < 5 or len(_CSV_DELIM.findall(line)) < 4:
        return line
    import csv
    try:
        cells = next(csv.reader([line]))
    except Exception:  # noqa
        return line
    return "   ".join(c.strip() for c in cells)


def parse_xml_primary(text: str, p: Parsed):
    root = _xml_root(text)
    p.report_type = _ln(root, "reportType")
    p.amendment_type = _ln(root, "amendmentType")
    p.amendment_no = _ln(root, "amendmentNo")
    p.entry_total = _to_int(_ln(root, "tableEntryTotal"))
    p.value_total = _to_int(_ln(root, "tableValueTotal"))
    p.other_managers_count = _to_int(_ln(root, "otherIncludedManagersCount"))
    for om in root.xpath(".//*[local-name()='otherManager2']"):
        p.other_managers.append((_ln(om, "sequenceNumber"), _ln(om, "cik"), _ln(om, "name")))
    nm = _ln(root, "name")
    if nm and not p.manager_name:
        p.manager_name = nm


def parse_xml_infotable(text: str) -> pd.DataFrame:
    root = _xml_root(text)
    rows = []
    for it in root.xpath(".//*[local-name()='infoTable']"):
        rows.append({
            "name_of_issuer": _ln(it, "nameOfIssuer"),
            "title_of_class": _ln(it, "titleOfClass"),
            "cusip": _ln(it, "cusip"),
            "value": _to_int(_ln(it, "value")),
            "shares": _to_int(_ln(it, "sshPrnamt")),
            "sh_prn": _ln(it, "sshPrnamtType").upper(),
            "put_call": _ln(it, "putCall").upper(),
            "investment_discretion": _ln(it, "investmentDiscretion").upper(),
            "other_managers": _ln(it, "otherManager"),
            "voting_sole": _to_int(_ln(it, "Sole")),
            "voting_shared": _to_int(_ln(it, "Shared")),
            "voting_none": _to_int(_ln(it, "None")),
        })
    df = pd.DataFrame(rows, columns=HOLDING_COLS)
    df["inherited_cusip"] = 0
    return df


# ---------------------------------------------------------------- text / html

# A CUSIP token must stand alone: whitespace / quote / apostrophe / pipe / line edge on both sides.
# Punctuation-embedded runs (uuencoded attachments in fixture html_tabs_quoted_2010) are not CUSIPs.
CUSIP_RE = re.compile(r"(?<![^\s\"'|(])([0-9A-Z]{6})[ -]?([0-9A-Z]{2})[ -]?([0-9A-Z])(?![^\s\"'|,;:)])")
CUSIP_GLUED_RE = re.compile(r"(?<=[A-Z$.&%/)])([0-9][0-9A-Z]{5})([0-9A-Z]{2})([0-9A-Z])(?=\s)")   # left-glued ("Common14149Y108"): starts with a digit
CUSIP8_RE = re.compile(r"(?<![^\s\"'|(])([0-9A-Z]{6,8})(?![^\s\"'|,;:)])")   # short ids: zeros dropped / SEDOL; standalone token
# A totals line: TOTAL-words, then straight into numbers (or nothing). "TOTAL SA" (the issuer) does not match.
TOTAL_LINE_RE = re.compile(r"^\s*(?:GRAND\s+|SUB-?\s*|PAGE\s+|PORTFOLIO\s+)?TOTALS?(?:\s+FOR\s+PAGE)?(?:\s+\d+)?(?:\s*\(.*?\))?\s*[:\-]*\s*(?:\$|\d|$)")
NUM = r"[\d,]+(?:\.\d+)?"
DISC = r"(?:SOLE|SHARED|DEFINED|DFND|DEFND|OTHER|OTR|NONE|SHRD|SOL|DEF)"
TAIL_RE = re.compile(
    rf"\s+(?P<value>{NUM})\s+(?P<shares>{NUM})"
    rf"(?:\s+(?P<shprn>SH|PRN|SHS|SHRS|SHARES))?"
    rf"(?:\s+(?P<pc>PUT|CALL))?"
    rf"(?:\s+(?P<disc>{DISC}))?"
    rf"(?P<rest>(?:\s+(?:{NUM}|-+))*)\s*$",
    re.I,
)
# Matched with .match(line, pos) at the end of the CUSIP token, so the CUSIP itself
# can never be swallowed as the value column. SH/PRN is optional because many
# 2010-era filings leave that column blank (blank == SH by 13F convention).


def html_to_lines(text: str) -> list[str]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(text, "lxml")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    lines = []
    tables = soup.find_all("table")
    if tables:
        for tb in tables:
            trs = tb.find_all("tr")
            if not trs:   # SGML <TABLE> around pre-formatted text, not an HTML table
                lines.extend(tb.get_text("\n").splitlines())
            for tr in trs:
                cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
                lines.append("   ".join(cells))
            lines.append("")
        # also keep non-table text for summary-page regexes
        for tb in tables:
            tb.decompose()
    lines.extend(soup.get_text("\n").splitlines())
    return lines


def _norm_cusip(a: str, b: str, c: str) -> str:
    return (a.replace(" ", "") + b + c).upper()


_NUM_TOK = re.compile(r"^\(?[\d,]+(?:\.\d+)?\)?$")
_SHPRN = {"SH": "SH", "SHS": "SH", "SHR": "SH", "SHRS": "SH", "SHARES": "SH", "S": "SH", "SHARE": "SH",
          "PRN": "PRN", "P": "PRN", "PRIN": "PRN", "PRINCIPAL": "PRN"}
_PUTCALL = {"PUT": "PUT", "CALL": "CALL", "CAL": "CALL"}   # CAL: Goldman Sachs heading "PUT/ CAL" (fixture text_put_cal_abbreviation_2011)
_DISC_PREFIX = ("SOLE", "SHARED", "SHRD", "SHARE-", "DEFINED", "DFND", "DEFND", "DEF", "OTHER", "OTR", "OTH", "ALL")
_FILLER = {"X", "-", "--", "NA", "N/A", "N.A.", "N.A", "NONE", "N", "Y", "YES", "NO", "*", "USD", "US", "0.0", "NIL"}
_REF = re.compile(r"^\(?[A-Z0-9]{1,2}\)?[,.;]?$")   # footnote refs like (a) (1) 01,


def parse_tail(tail: str, col_order: list[str] | None = None, head_nums: list | None = None) -> dict | None:
    """Token rules for what follows the CUSIP on a holdings line. Column order varies by
    filer (value SH shares / value shares SH / tab cells / quoted numbers / X marks ...), so:
    first two numeric tokens = value, shares; SH/PRN, PUT/CALL and discretion are keyword
    tokens wherever they sit (discretion matched by prefix: SOLE, SHARED-OTHER, DEF/OTH, ...);
    remaining numerics = [other managers...] + voting (last 3). Short filler tokens (X, N/A,
    Yes, USD, (a) ...) are ignored. Two or more real words after the numbers -> prose, None."""
    tail = re.sub(r"(\d)(SH|SHR|PRN|S|P)\b", r"\1 \2", tail.replace('"', " ").replace("$", " "), flags=re.I)
    # a 2-decimal number glued to the next number: 415105.00420600.00 / 1,475.0428,000 / 45.6012345 — but not 21.9100 or 2,790.000
    tail = re.sub(r"(\d\.\d{2})(?=(?:\d{1,3},\d{3}|[\d,]{3,}\.\d{2}(?!\d))(?![\d.]))", r"\1 ", tail)   # 2-decimal pairs first (a bare digit run is a long decimal: 950.6419606)
    tail = re.sub(r"(\d\.\d{3})(?=[\d,]{3,}\.\d{3}(?!\d))", r"\1 ", tail)                                      # then 3-decimal pairs (133761.058 style)
    toks = tail.split()
    nums, kw = [], {"shprn": "", "pc": "", "disc": ""}
    seen_num, stray, pre_words = False, 0, []
    for t in toks:
        u = t.upper().strip(",;:")
        bare = u.strip("()-/.,")
        if _NUM_TOK.match(u):
            nums.append(_to_int(u.strip("()")))
            seen_num = True
        elif bare in _SHPRN:
            kw["shprn"] = kw["shprn"] or _SHPRN[bare]
        elif bare in _PUTCALL:
            kw["pc"] = kw["pc"] or _PUTCALL[bare]
        elif bare.startswith(_DISC_PREFIX):
            kw["disc"] = kw["disc"] or bare
        elif u in _FILLER or bare in _FILLER or _REF.match(u):
            continue
        elif not seen_num:
            pre_words.append(t)   # words before the numbers: title/issuer text (fixture text_price_column_header_2010)
            continue
        else:
            stray += 1
            if stray >= 2 or len(u) > 15:
                return None       # free text after the numbers: not a holdings row
    if col_order and head_nums and len(nums) < len(col_order):
        nums = list(head_nums) + nums      # header puts a numeric column (e.g. QUANTITY) before the CUSIP
    if len(nums) < 2:
        return None
    if col_order and len(nums) >= len(col_order):
        value, shares = nums[col_order.index("value")], nums[col_order.index("shares")]
        rest = nums[len(col_order):]
    else:
        value, shares, rest = nums[0], nums[1], nums[2:]
    voting = rest[-3:] if len(rest) >= 3 else rest
    other = rest[:-3] if len(rest) > 3 else []
    vs = (voting + [None, None, None])[:3]
    return {"value": value, "shares": shares, "sh_prn": kw["shprn"], "put_call": kw["pc"],
            "investment_discretion": kw["disc"], "other_managers": " ".join(str(x) for x in other),
            "voting_sole": vs[0], "voting_shared": vs[1], "voting_none": vs[2], "_pre_words": " ".join(pre_words)}


# ---- header-driven column order (fixtures: text_value_shares_swapped_2010, text_three_value_columns_2010,
#      text_header_contradicts_data_2010). Numbers are right-aligned under headers of varying width, so
#      positions are unreliable; the left-to-right ORDER of numeric column headings matches the data.
_HDR_VALUE = re.compile(r"FAIR MARKET\.?\s?VALUE|MARKET\.?\s?VALUE|MKT\.?\s?VALUE|FAIR MARKET|\bMKT\b|\bMARKET\b|\(?X?\$?\s?1,?000\)?S?|\(\s*000'?S?\s*\)|\$000|\bVALUE\b")
_HDR_MARKET = re.compile(r"FAIR MARKET\.?\s?VALUE|MARKET\.?\s?VALUE|MKT\.?\s?VALUE|FAIR MARKET|\bMKT\b|\bMARKET\b")
_HDR_SHARES = re.compile(r"\bSHARES\b|\bSHRS\b|\bSHS\b|\bPRINCIPAL\b|\bPRN\s+AM(?:OU)?N?T\b|\bAMOUNT\b|\bNUMBER OF\b|\bQUANTITY\b")
_HDR_PRICE = re.compile(r"\bPRICE\b|\bUNIT PRICE\b|\bCOST\b")   # numeric column that is neither value nor shares
_HDR_ANY = re.compile(r"CUSIP|VALUE|SHARES|SHRS|PRINCIPAL|AMOUNT|DISCRETION|ISSUER|PRICE")
_PROSE_END = re.compile(r"[.,;]\s*$")   # Luke 2026-10-12: prose lines above the table are never column headings


def find_column_order(lines: list[str], first_data: int, lookback: int = 14) -> list[str] | None:
    """Return the order of numeric columns, e.g. ['shares','value'] or ['mv','value','shares'], read
    from the header lines above the first holdings line; None when the header is absent or ambiguous
    (then the default order value, shares applies). Numbers are right-aligned, so each heading is
    placed by its RIGHT edge; headings of one kind within 9 chars (multi-line headers) are one column."""
    hits = []   # [right_edge, kind, line_no, text, left_edge]
    cusip_pos = None
    for ln, l in enumerate(lines[max(0, first_data - lookback): first_data]):
        up = l.upper().expandtabs(8)       # fixture text_tab_header_2010: a tab is one char but many columns
        if not _HDR_ANY.search(up) or re.search(r"\bTOTAL\b", up):   # summary-page lines ("... Value Total") are not column headings
            continue
        if _PROSE_END.search(l) or len(re.findall(r"\b[a-z]{3,}\b", l)) >= 4:
            continue    # a sentence ("...to correct market value data.") is not a column heading (fixture text_prose_market_value_before_header_2012)
        mc = re.search(r"\bCUSIP\b", up)
        if mc:
            cusip_pos = mc.end()
        for m in _HDR_PRICE.finditer(up):
            hits.append([m.end(), "price", ln, m.group(0), m.start()])
        for m in _HDR_SHARES.finditer(up):
            hits.append([m.end(), "shares", ln, m.group(0), m.start()])
        for m in _HDR_VALUE.finditer(up):
            hits.append([m.end(), "mv" if _HDR_MARKET.fullmatch(m.group(0)) else "value", ln, m.group(0), m.start()])
    if not hits:
        return None
    # a bare VALUE stacked within 4 chars of a bare MARKET/MKT on another line reads "MARKET / VALUE": market value
    for h in hits:
        if h[1] == "value" and h[3] == "VALUE":   # stacked under/over by right OR left edge (fixture text_fair_market_value_left_aligned_header_2010)
            if any(g[1] == "mv" and g[2] != h[2] and g[3] in ("MARKET", "MKT", "FAIR MARKET") and (abs(g[0] - h[0]) <= 4 or abs(g[4] - h[4]) <= 4) for g in hits):
                h[1] = "mv"
    cols = []   # [right_edge, kind]
    for kind in ("shares", "value", "mv", "price"):
        for r, k, _, _, _ in sorted(h for h in hits if h[1] == kind):
            if cols and cols[-1][1] == kind and abs(cols[-1][0] - r) <= 9:
                cols[-1][0] = max(cols[-1][0], r)
            else:
                cols.append([r, kind])
    vals = [c for c in cols if c[1] == "value"]
    cols = [c for c in cols if not (c[1] == "mv" and any(abs(c[0] - v[0]) <= 3 for v in vals))]   # same column labelled both ways
    if not vals and sum(c[1] == "mv" for c in cols) == 1:
        for c in cols:
            if c[1] == "mv":
                c[1] = "value"                 # a lone "market value" IS the value column
    cols.sort()
    kinds = [k for _, k in cols]
    if kinds.count("value") != 1 or kinds.count("shares") != 1:
        return None
    for (r1, k1), (r2, k2) in zip(cols, cols[1:]):
        if r2 - r1 < 4:
            return None                        # two headings on top of each other: ambiguous
    n_before = sum(1 for r, _ in cols if cusip_pos is not None and r < cusip_pos)
    return kinds + ([f"<{n_before}"] if n_before else [])   # trailing "<n": n numeric columns are left of CUSIP


def _continuation(line, up, rows, col_order, keep_source) -> bool:
    """Continuation sub-row (guardrails, Luke 2026-10-09): starts with a number, has the full shape of a
    holding (value + shares + SH/PRN or discretion keyword), is not a totals/subtotal line, and directly
    follows a parsed row. It inherits issuer/class/CUSIP and is flagged inherited_cusip=1."""
    if not (rows and re.match(r"^\s*[\d,]+(?:\.\d+)?\s", line) and re.search(r"\b(SH|SHS|SHR|PRN|SOLE|SHARED|DEFINED|DFND|OTHER)\b", up)
            and not re.search(r"TOTAL|SUBTOTAL|SUB-TOTAL|GRAND", up) and not _is_cusip_only(line)):
        return False
    t = parse_tail(line, col_order)
    if not (t and t["value"] is not None and t["shares"] is not None):
        return False
    t.pop("_pre_words", None)
    prev = rows[-1]
    rec = {"name_of_issuer": prev["name_of_issuer"], "title_of_class": prev["title_of_class"], "cusip": prev["cusip"], **t, "inherited_cusip": 1}
    if keep_source:
        rec["_src"] = line
    rows.append(rec)
    return True


def find_cusip_column(lines: list[str], first_data: int, lookback: int = 14) -> int | None:
    """Left edge of the CUSIP heading above the first holdings line (fixed-width layouts), else None."""
    for l in lines[max(0, first_data - lookback): first_data]:
        m = re.search(r"\bCUSIP\b", l.upper().expandtabs(8))
        if m and not re.search(r"\bTOTAL\b", l.upper()):
            return m.start()
    return None


def parse_text_lines(lines: list[str], keep_source: bool = False) -> tuple[pd.DataFrame, int]:
    """Line parser. A holding is a line containing a 9-char CUSIP-looking token (6-2-1, with
    at least one digit) whose tail parses under parse_tail(). Returns (holdings, n_cusip_lines):
    n_cusip_lines counts every line that carried a CUSIP-looking token plus at least two
    numeric tokens, whether or not the tail parsed, so parser misses are measurable."""
    rows, cusip_lines = [], 0
    col_order, n_before, cusip_col = None, 0, None
    for i, raw in enumerate(lines):        # pre-pass: header above the first holdings line
        if _line_candidates(raw)[0]:
            col_order = find_column_order(lines, i)
            cusip_col = find_cusip_column(lines, i)
            if col_order and col_order[-1].startswith("<"):
                n_before = int(col_order[-1][1:])
                col_order = col_order[:-1]
            break
    data_col = _cusip_data_column(lines)   # fixed-width layouts: the column where standalone CUSIPs start on most lines
    for raw in lines:
        line = _split_csv_line(raw.rstrip())
        if not line.strip():
            continue
        up = line.upper()
        if TOTAL_LINE_RE.search(up):
            continue              # page / grand totals are never holdings
        cands, short_ids = _candidates(up)
        if cands and not short_ids and cusip_col is not None and not any(is_valid9(c) for _, c in cands) \
                and not any(abs(cm.start() - cusip_col) <= 6 for cm, _ in cands):
            # a 9-char token that fails the check digit and sits away from the CUSIP heading is class text
            # ("MIDCAP400"); if a short id sits under the heading, use the short-id candidates instead
            alt = [(cm, cm.group(1)) for cm in CUSIP8_RE.finditer(up) if re.search(r"\d", cm.group(1)) and abs(cm.start() - cusip_col) <= 6]
            if alt:
                cands, short_ids = alt, True
        if data_col is not None and (not cands or short_ids):
            # Luke 2026-10-12 (fixture text_cusip_glued_to_digit_under_heading_2011): fixed-width class text ending in a
            # digit glues to the CUSIP ("COM PAR $0.01345370860"), so no token regex can see it; the 9 characters at the
            # filing's CUSIP data column (where standalone CUSIPs start on most lines) are the CUSIP when they pass the
            # check digit and end at whitespace. Before the fix the 6-digit value was taken as a short id ("116035"
            # value=1187668 shares=1), which put $97bn on 13 rows. Anchored to the data column, not a window around the
            # heading: a window let a chance-valid slice of a 12-char "CUSIP+000" token win (Gilder Gagnon Howe 2010Q4).
            under = _cusip_under_heading(up, data_col, window=0)
            if under:
                cands, short_ids = [under], False
        if not cands:
            if _continuation(line, up, rows, col_order, keep_source):
                cusip_lines += 1
            continue
        if len(re.findall(r"(?<![\w.])[\d,]{2,}(?![\w])", up)) >= 2:
            cusip_lines += 1
        hit = None
        # 9-char CUSIPs: last candidate whose tail parses (skips tokens embedded in the name). Short ids:
        # FIRST candidate, because the id column precedes the numbers and voting numbers also look like ids
        # (fixture text_continuation_rows_glued_voting_2010: "6251448  478835 90988400 SH SOLE 89557400 1431000").
        if short_ids and cusip_col is not None:   # 8-char ids + digit tokens in the class text (fixture text_8char_ids_digit_class_text_2010)
            cands = sorted(cands, key=lambda c: abs(c[0].start() - cusip_col))
        order = list(cands if short_ids else reversed(cands))
        if not short_ids:
            # Luke 2026-10-12: a 9-char token is a CUSIP only if it passes the check digit. Candidates that pass are
            # tried before any that fail: a 9-digit SHARE COUNT ("594918104 7743339 264534730 SH") used
            # to win as the "last candidate whose tail parses" (fixture text_nine_digit_shares_vs_cusip_heading_2010).
            # Lines with no valid candidate keep the old behaviour (filers with broken check digits are repaired later).
            # Valid-check-digit candidates are tried first; the others only when no valid one yields a holding
            # (fixture text_price_column_header_2010 has a row whose true CUSIP fails the check digit).
            valid = [c for c in order if is_valid9(c[1])]
            if cusip_col is not None and len(valid) > 1:
                # two valid tokens (a share count can pass the check digit by chance): the one under the CUSIP heading
                # wins (fixture text_two_valid_cusip_tokens_heading_column_2011: "369604103  2117439  112271440 SH")
                valid = sorted(valid, key=lambda c: abs(c[0].start() - cusip_col))
            order = valid + [c for c in order if not is_valid9(c[1])]
        for cm, cusip in order:
            head_nums = None
            if n_before:   # header puts numeric column(s) left of CUSIP (fixture text_price_column_header_2010)
                head_nums = [_to_int(x) for x in re.findall(r"(?<![\w.])[\d,]+(?![\w.])", line[: cm.start()].replace("$", " "))][-n_before:]
            t = parse_tail(line[cm.end():], col_order, head_nums)
            if t:
                hit = (cm, cusip, t)
                break
        if not hit:
            if _continuation(line, up, rows, col_order, keep_source):   # the CUSIP-like tokens were voting numbers / short ids
                cusip_lines += 1
            continue
        cm, cusip, t = hit
        name_part = line[: cm.start()].replace('"', " ").strip()
        parts = re.split(r"\s{2,}|\t|\|", name_part)
        parts = [x.strip() for x in parts if x.strip()]
        issuer = parts[0] if parts else name_part
        klass = " ".join(parts[1:]) if len(parts) > 1 else ""
        pre = t.pop("_pre_words", "")
        if (not issuer or _NUM_TOK.match(issuer.replace("$", "").strip())) and pre:
            issuer = pre               # issuer text sits after the CUSIP in this layout
        rec = {"name_of_issuer": issuer, "title_of_class": klass, "cusip": cusip, **t, "inherited_cusip": 0}
        if keep_source:
            rec["_src"] = line
        rows.append(rec)
    cols = HOLDING_COLS + (["_src"] if keep_source else [])
    df = pd.DataFrame(rows, columns=cols)
    df.attrs["col_order"] = col_order
    return df, cusip_lines


_NINE = re.compile(r"[0-9A-Z]{9}")


def _cusip_data_column(lines: list[str], min_lines: int = 20, min_share: float = 0.5) -> int | None:
    """Start column of standalone, check-digit-valid 9-char CUSIP tokens when at least `min_lines` lines carry one and
    the modal column holds `min_share` of them (a fixed-width layout); None for ragged / tab / HTML-derived layouts."""
    cols = collections.Counter()
    for raw in lines:
        up = _split_csv_line(raw.rstrip()).upper()
        for rx in (CUSIP_RE, CUSIP_GLUED_RE):   # standalone, and letter-glued ("Common88579Y101": fixture text_cusip_glued_to_class_text_2010)
            for cm in rx.finditer(up):
                c = _norm_cusip(*cm.groups())
                if re.search(r"\d", c) and is_valid9(c):
                    cols[cm.start()] += 1
    if sum(cols.values()) < min_lines:
        return None
    col, n = cols.most_common(1)[0]
    return col if n >= min_share * sum(cols.values()) else None


def _cusip_under_heading(up: str, cusip_col: int, window: int = 6):
    """(match, cusip) for a check-digit-valid 9-char run that starts within `window` chars of the CUSIP heading's
    left edge and ends at whitespace / line end, whatever precedes it; None otherwise."""
    for p in range(max(0, cusip_col - window), cusip_col + window + 1):
        m = _NINE.match(up, p)
        if m and (m.end() == len(up) or up[m.end()].isspace()) and re.search(r"\d", m.group(0)) and is_valid9(m.group(0)):
            return m, m.group(0)
    return None


def _candidates(up: str):
    """CUSIP-like tokens on an upper-cased line: 9-char standalone, else glued to the class text, else 6-8 char
    short ids (zeros dropped / SEDOL / check digit dropped). Returns (list of (match, id), short_ids?)."""
    cands = []
    for cm in CUSIP_RE.finditer(up):
        cusip = _norm_cusip(*cm.groups())
        if re.search(r"\d", cusip):
            cands.append((cm, cusip))
    if not cands:   # CUSIP glued to the preceding class text (column overflow); right side must be whitespace
        for cm in CUSIP_GLUED_RE.finditer(up):
            cusip = _norm_cusip(*cm.groups())
            if re.search(r"\d", cusip) and re.search(r"[A-Z]{2}", up[: cm.start()]):
                cands.append((cm, cusip))
    if cands:
        return cands, False
    for cm in CUSIP8_RE.finditer(up):
        tok = cm.group(1)
        if re.search(r"\d", tok) and re.search(r"[A-Z]{2}", up[: cm.start()]):
            cands.append((cm, tok))
    return cands, True


def _line_candidates(raw: str):
    """(parses?, line) — does this line look like a holdings line under default column order."""
    line = _split_csv_line(raw.rstrip())
    up = line.upper()
    if not line.strip() or TOTAL_LINE_RE.search(up):
        return False, line
    cands, _ = _candidates(up)
    for cm, _c in cands:
        if parse_tail(line[cm.end():]):
            return True, line
    return False, line


# ---- stacked-cell layouts (fixtures: text_stacked_cells_2010 = column-major per page,
#      text_stacked_cells_named_2010 = one record top-to-bottom) ---------------------------------
_CUSIP_ONLY = re.compile(r"^\s*([0-9A-Z]{6,9})\s*$")


def _is_cusip_only(l: str, digits_ok: bool = False) -> bool:
    """A line that is just a 6-9 char id. Pure-digit ids (leading zeros lost, e.g. 8474108) count only
    when digits_ok, i.e. the document writes its numbers with commas so a bare digit run is an id."""
    m = _CUSIP_ONLY.match(l.upper())
    if not m or not re.search(r"\d", m.group(1)):
        return False
    return digits_ok or not _NUM_TOK.match(m.group(1))


def _digits_are_ids(L: list[str]) -> bool:
    comma = sum(1 for l in L if re.fullmatch(r"\s*\$?\d{1,3}(,\d{3})+(\.\d+)?\s*", l))
    plain = sum(1 for l in L if re.fullmatch(r"\s*\$?\d{4,}(\.\d+)?\s*", l))
    return comma > plain


def _is_numeric_line(l: str) -> bool:
    return bool(_NUM_TOK.match(l.replace("$", "").replace('"', "").strip()))


def parse_stacked(lines: list[str]) -> pd.DataFrame:
    """One cell per line. Two shapes:
    row-major: [name lines] CUSIP [value] [shares] [filler/keywords...] then the next name;
    column-major per page: a block of N CUSIP lines, then a block of N values, a block of N shares,
    with the N names (and N classes) in the blocks just before the CUSIPs."""
    L = [l.rstrip() for l in lines]
    dok = _digits_are_ids(L)
    cus = [i for i, l in enumerate(L) if _is_cusip_only(l, dok)]
    if len(cus) < 3:
        return pd.DataFrame(columns=HOLDING_COLS)
    rows = []
    # consecutive CUSIP lines => column-major
    runs = sum(1 for a, b in zip(cus, cus[1:]) if b == a + 1)
    if runs >= len(cus) * 0.6:
        blocks, cur = [], []
        for i, l in enumerate(L):
            if l.strip():
                cur.append(i)
            elif cur:
                blocks.append(cur); cur = []
        if cur:
            blocks.append(cur)
        for bi, b in enumerate(blocks):
            if sum(_is_cusip_only(L[i], dok) for i in b) < max(3, 0.8 * len(b)):
                continue
            n = len(b)
            nums = [blk for blk in blocks[bi + 1: bi + 8] if len(blk) == n and sum(_is_numeric_line(L[i]) and not _is_cusip_only(L[i], dok) for i in blk) >= 0.8 * n]
            if len(nums) < 2:
                continue
            names = [blk for blk in blocks[max(0, bi - 4): bi] if len(blk) == n and sum(not _is_numeric_line(L[i]) and not _is_cusip_only(L[i], dok) for i in blk) >= 0.8 * n]
            name_blk = names[0] if names else None
            class_blk = names[1] if len(names) > 1 else None
            for k in range(n):
                cl = L[b[k]].strip().upper()
                rows.append({"name_of_issuer": L[name_blk[k]].strip() if name_blk else "", "title_of_class": L[class_blk[k]].strip() if class_blk else "",
                             "cusip": cl, "value": _to_int(L[nums[0][k]].replace("$", "")), "shares": _to_int(L[nums[1][k]].replace("$", "")),
                             "sh_prn": "", "put_call": "", "investment_discretion": "", "other_managers": "",
                             "voting_sole": None, "voting_shared": None, "voting_none": None})
        df = pd.DataFrame(rows, columns=HOLDING_COLS); df["inherited_cusip"] = 0
        return df
    # row-major
    prev_end = 0
    for j, ci in enumerate(cus):
        tail = []
        k = ci + 1
        while k < len(L) and (k < (cus[j + 1] if j + 1 < len(cus) else len(L))):
            tok = L[k].strip()
            if not tok:
                k += 1; continue
            u = tok.upper().strip("()-/.,")
            if (_is_numeric_line(tok) and not _is_cusip_only(tok, dok)) or u in _SHPRN or u in _PUTCALL or u.startswith(_DISC_PREFIX) or tok.upper() in _FILLER or u in _FILLER or _REF.match(tok.upper()):
                tail.append(tok.replace("$", " ")); k += 1
            else:
                break
        name_lines = [L[i].strip() for i in range(prev_end, ci) if L[i].strip()][-2:]
        prev_end = k
        t = parse_tail(" ".join(tail))
        if not t:
            continue
        issuer = " ".join(name_lines[:-1]) if len(name_lines) > 1 else (name_lines[0] if name_lines else "")
        klass = name_lines[-1] if len(name_lines) > 1 else ""
        t.pop("_pre_words", None)
        rows.append({"name_of_issuer": issuer, "title_of_class": klass, "cusip": L[ci].strip().upper(), **t})
    df = pd.DataFrame(rows, columns=HOLDING_COLS); df["inherited_cusip"] = 0
    return df


SUMMARY_ENTRY_RE = re.compile(r"(?:information\s+)?table\s+entry\s+total[^0-9]{0,40}([\d,]+)(?![A-Za-z])", re.I)   # (?![A-Za-z]) rejects the 13 of "Form 13F"
SUMMARY_VALUE_RE = re.compile(r"(?:information\s+)?table\s+value(?:\s+total)?[^0-9]{0,40}([\d,]+)(?![A-Za-z])", re.I)
REPORT_TYPE_RE = re.compile(r"\[\s*[xX]\s*\]\s*(13F\s+(?:HOLDINGS|NOTICE|COMBINATION)\s*(?:REPORT)?)", re.I)
AMEND_TYPE_RE = re.compile(r"amendment\s+type[^A-Za-z]{0,20}(restatement|new\s+holdings)", re.I)
# "amendment type" is the XML tag name and never appears on a text-era cover page, which instead
# carries a checkbox. Without this the text era had NO amendment type at all, so ownership.py
# defaulted every amendment to RESTATEMENT and deleted the original filing's holdings
# (decision 12, 2026-10-18; ~131k rows deleted in 2010Q1 alone).
# Three real layouts, found by verification on 2026-10-19: brackets [X], parentheses (X) and pipes
# |X|; "adds new holding entries" (singular) as often as "holdings"; and "add" as well as "adds".
# The first version accepted only "[X] adds new holdings", which left 105 amendments across the 13
# text quarters still defaulting to RESTATEMENT. One of them, accession 0001390777-11-000128,
# replaced Bank of New York Mellon's entire 20,336-row 2011Q1 book with a single row.
AMEND_CHECKBOX_RE = re.compile(
    r"[\[\(\|]\s*[xX]\s*[\]\)\|]\s*(is\s+a\s+restatement|adds?\s+new\s+holding)", re.I)
OTHER_MGR_COUNT_RE = re.compile(r"number\s+of\s+other\s+included\s+managers[^0-9]{0,40}(\d+)", re.I)


def parse_text_summary(text: str, p: Parsed):
    flat = re.sub(r"<[^>]+>", " ", text)
    flat = re.sub(r"&nbsp;|&#160;", " ", flat)
    m = SUMMARY_ENTRY_RE.search(flat)
    if m:
        p.entry_total = _to_int(m.group(1))
    m = SUMMARY_VALUE_RE.search(flat)
    if m and not (_to_int(m.group(1)) == 1000 and re.search(r"[xX(]\s*\$?\s*$", flat[max(0, m.start(1) - 4): m.start(1)])):
        p.value_total = _to_int(m.group(1))
    elif m:   # "(x$1000)" unit marker right after the label; look for a real number after it
        m2 = re.compile(r"[\d,]{4,}(?![A-Za-z])").search(flat, m.end())
        if m2 and m2.start() - m.end() < 60:
            p.value_total = _to_int(m2.group(0))
    m = REPORT_TYPE_RE.search(flat)
    if m:
        p.report_type = re.sub(r"\s+", " ", m.group(1).upper())
    m = AMEND_TYPE_RE.search(flat)
    if m:
        p.amendment_type = re.sub(r"\s+", " ", m.group(1).upper())
    else:
        m = AMEND_CHECKBOX_RE.search(flat)          # text-era cover page
        if m:
            p.amendment_type = "RESTATEMENT" if "restatement" in m.group(1).lower() else "NEW HOLDINGS"
    m = OTHER_MGR_COUNT_RE.search(flat)
    if m:
        p.other_managers_count = _to_int(m.group(1))


# ---------------------------------------------------------------- driver

def parse_submission(text: str) -> Parsed:
    p = Parsed()
    header, docs = split_submission(text)
    parse_header(header, p)
    try:
        xml_primary = [d for d in docs if d["type"].startswith("13F") and "<XML>" in d["text"][:2000].upper()]
        xml_table = [d for d in docs if d["type"].upper().startswith("INFORMATION TABLE") and "<XML>" in d["text"][:2000].upper()]
        if xml_table or xml_primary:
            p.parse_method = "xml"
            if xml_primary:
                parse_xml_primary(xml_primary[0]["text"], p)
            if xml_table:
                p.holdings = parse_xml_infotable(xml_table[0]["text"])
            else:
                p.holdings = pd.DataFrame(columns=HOLDING_COLS)
                if p.report_type.upper() != "13F NOTICE":
                    p.errors.append("no INFORMATION TABLE document")
        else:
            main = [d for d in docs if d["type"].startswith("13F")] or docs
            if not main:
                p.errors.append("no documents")
                p.holdings = pd.DataFrame(columns=HOLDING_COLS)
                return p
            for d in main:
                if re.search(r"Content-Transfer-Encoding:\s*quoted-printable", d["text"][:3000], re.I):
                    import quopri
                    d["text"] = quopri.decodestring(d["text"].encode("latin-1", "replace")).decode("latin-1")
            text_all = "\n".join(d["text"] for d in main)
            is_html = bool(re.search(r"<(html|tr|td)\b", text_all, re.I))   # bare <TABLE> is SGML text, not HTML
            if is_html:
                p.parse_method = "html"
                lines = []
                for d in main:
                    lines.extend(html_to_lines(d["text"]))
            else:
                p.parse_method = "text"
                lines = []
                for d in main:
                    t = re.sub(r"<[^>]+>", "", d["text"])  # strip <PAGE>, <S>, <C> markers
                    lines.extend(t.splitlines())
            parse_text_summary(text_all, p)
            p.holdings, n_cusip = parse_text_lines(lines)
            p.n_cusip_lines = n_cusip
            p.col_order = p.holdings.attrs.get("col_order")
            if p.col_order:
                p.notes.append(f"column order from header: {','.join(p.col_order)}")
            _dok = _digits_are_ids(lines)
            n_only = sum(_is_cusip_only(l, _dok) for l in lines)
            if n_only >= 3 and len(p.holdings) < 0.1 * n_only:
                st = parse_stacked(lines)
                if len(st) > len(p.holdings):
                    p.holdings = st
                    p.n_cusip_lines = n_only
                    p.notes.append(f"stacked-cell layout: {len(st)} rows from {n_only} one-per-line CUSIPs")
            if len(p.holdings) and p.value_total:
                vsum = p.holdings["value"].fillna(0).sum()
                ssum = p.holdings["shares"].fillna(0).sum()
                tol = max(1, 0.01 * p.value_total)
                if abs(vsum - p.value_total) > tol and abs(ssum - p.value_total) <= tol:
                    # Flag only. Applying a swap was wrong for 3-column layouts (market value $, value $000,
                    # shares): see tests/fixtures/text_three_value_columns_2010 and output/problems/*/shares_check.txt
                    p.notes.append("possible value/shares swap: shares column sums to the declared value total (not applied)")
            if p.holdings.empty:
                p.errors.append(f"no holdings parsed ({p.parse_method}, cusip-lines={n_cusip})")
    except Exception as ex:  # noqa
        p.errors.append(f"exception: {type(ex).__name__}: {str(ex)[:200]}")
        if p.holdings is None:
            p.holdings = pd.DataFrame(columns=HOLDING_COLS)

    h = p.holdings
    p.n_rows = len(h)
    if p.parse_method == "xml":
        p.n_cusip_lines = p.n_rows
    p.value_sum = int(h["value"].fillna(0).sum()) if len(h) else 0
    if p.entry_total is not None:
        p.checksum_entries_ok = (p.entry_total == p.n_rows)
    if p.value_total is not None:
        p.checksum_value_ok = (abs(p.value_total - p.value_sum) <= max(1, 0.001 * max(p.value_total, 1)))
    return p
