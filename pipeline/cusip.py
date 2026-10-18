"""CUSIP normalization, option-code flagging, SEDOL detection, universe-confirmed repair.

cusip_status values (every holdings row gets exactly one):
  ok                      valid 9-char CUSIP
  option_code             9-char, fails check digit, '9' in position 7 (13F option convention). FLAG only;
                          exclusion from ownership uses the put/call field.
  invalid_9               9-char, fails check digit, not an option code (foreign ids etc.). Unrepaired.
  sedol                   7-char string passing the SEDOL check digit. Unrepaired, kept as identifier.
  repaired_pad_zeros      short -> left-padded with zeros; check digit valid AND in reference universe
  repaired_check_digit    short -> check digit computed; result in reference universe
  ambiguous               both readings confirmed by the universe. Unrepaired.
  unconfirmed_short       neither reading confirmed by the universe. Unrepaired.
  empty / too_long        as named

Reference universe = valid 9-char CUSIPs seen in the quarter's filings
                   ∪ SEC Official List of Section 13(f) Securities for the quarter (if loaded).
"""
from __future__ import annotations

import re

import pandas as pd

_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ*@#"
_SEDOL_W = (1, 3, 1, 7, 3, 9)


def _cval(ch: str) -> int:
    return _CHARS.index(ch)


def check_digit(base8: str) -> str:
    total = 0
    for i, ch in enumerate(base8):
        v = _cval(ch)
        if i % 2 == 1:
            v *= 2
        total += v // 10 + v % 10
    return str((10 - total % 10) % 10)


def is_valid9(c: str) -> bool:
    return bool(re.fullmatch(r"[0-9A-Z*@#]{9}", c)) and check_digit(c[:8]) == c[8]


def is_option_code(c: str) -> bool:
    return len(c) == 9 and c[6] == "9" and not is_valid9(c)


def is_sedol(s: str) -> bool:
    if not re.fullmatch(r"[0-9B-DF-HJ-NP-TV-Z]{6}\d", s):
        return False
    t = sum(w * (int(ch) if ch.isdigit() else ord(ch) - 55) for w, ch in zip(_SEDOL_W, s[:6]))
    return (10 - t % 10) % 10 == int(s[6])


def clean(raw: str) -> str:
    return re.sub(r"[^0-9A-Z*@#]", "", (raw or "").upper())


def candidates(c: str) -> tuple[str, str]:
    a = c.rjust(9, "0")
    b = c.rjust(8, "0")
    return a, b + check_digit(b)


def resolve(raw: str, universe: set[str]) -> tuple[str, str]:
    c = clean(raw)
    if not c:
        return "", "empty"
    if len(c) > 9:
        return c, "too_long"
    if len(c) == 9:
        if is_valid9(c):
            return c, "ok"
        return c, "option_code" if is_option_code(c) else "invalid_9"
    if len(c) == 7 and is_sedol(c):
        return c, "sedol"
    a, b = candidates(c)
    a_ok = is_valid9(a) and a in universe
    b_ok = b in universe
    if a_ok and b_ok:
        return c, "ambiguous"
    if a_ok:
        return a, "repaired_pad_zeros"
    if b_ok:
        return b, "repaired_check_digit"
    return c, "unconfirmed_short"


def build_universe(raw_cusips: pd.Series, sec_list: set[str] | None = None) -> set[str]:
    u = {c for c in raw_cusips.fillna("").map(clean).unique() if is_valid9(c)}
    if sec_list:
        u |= {c for c in sec_list if is_valid9(c)}
    return u


def resolve_series(s: pd.Series, universe: set[str]) -> pd.DataFrame:
    cache = {}
    out_c, out_s = [], []
    for raw in s.fillna("").astype(str):
        if raw not in cache:
            cache[raw] = resolve(raw, universe)
        c, st = cache[raw]
        out_c.append(c)
        out_s.append(st)
    return pd.DataFrame({"cusip_raw": s.values, "cusip": out_c, "cusip_status": out_s}, index=s.index)
