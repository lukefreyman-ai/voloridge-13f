"""Decision 12 (2026-10-18): amendment handling.

Two defects found by review on 2026-10-18 and fixed here:

1. `AMEND_TYPE_RE` searched for "amendment type", which is the XML tag name. A text-era cover page
   instead carries a checkbox, so amendment_type was EMPTY for all 13 text quarters. ownership.py
   then treated every amendment as a RESTATEMENT and deleted the original filing's holdings:
   131,915 rows in 2010Q1, 134,542 in 2012Q4, including Susquehanna's entire book (7,927 rows
   replaced by 3) on a filing whose cover page says it ADDS holdings.

2. When a manager's original was a 13F NOTICE (filtered out, so no original survived), every
   amendment was appended, double counting holdings: 9,886 duplicate (quarter, cusip, manager)
   rows and 3.32bn shares across 10 of 20 quarters.

Run: python3 -m pytest tests -q
"""
import glob
import gzip
from pathlib import Path

import pandas as pd

from pipeline.ownership import select_filings
from pipeline.parse13f import parse_submission

FIX = Path(__file__).parent / "fixtures"
PERIOD = "20100331"


def test_real_text_cover_page_checkbox_is_read():
    """The filing says '[ X] adds new holdings entries.' and never says 'amendment type'."""
    (path,) = glob.glob(str(FIX / "text_amendment_checkbox_new_holdings_2010__*.txt.gz"))
    raw = gzip.open(path).read().decode("utf-8", "replace")
    assert "amendment type" not in raw.lower(), "if this appears, the old regex would have worked"
    assert "adds new holdings" in raw.lower()
    p = parse_submission(raw)
    assert p.amendment_type == "NEW HOLDINGS", f"got {p.amendment_type!r}"


def filings(*rows):
    """rows: (accession, form_type, amendment_type, report_type, filed_date)"""
    return pd.DataFrame(
        [{"accession": a, "form_type": ft, "amendment_type": at, "report_type": rt,
          "filed_date": fd, "manager_cik": 1, "period_of_report": PERIOD} for a, ft, at, rt, fd in rows])


def chosen(df):
    sel, _ = select_filings(df, PERIOD)
    return list(sel["accession"])


def test_original_only():
    assert chosen(filings(("orig", "13F-HR", "", "13F HOLDINGS REPORT", "2010-04-10"))) == ["orig"]


def test_restatement_replaces_the_original():
    assert chosen(filings(
        ("orig", "13F-HR", "", "13F HOLDINGS REPORT", "2010-04-10"),
        ("am", "13F-HR/A", "RESTATEMENT", "13F HOLDINGS REPORT", "2010-05-10"))) == ["am"]


def test_new_holdings_is_added_to_the_original():
    assert chosen(filings(
        ("orig", "13F-HR", "", "13F HOLDINGS REPORT", "2010-04-10"),
        ("am", "13F-HR/A", "NEW HOLDINGS", "13F HOLDINGS REPORT", "2010-05-10"))) == ["orig", "am"]


def test_two_blank_amendments_with_no_original_keep_only_the_latest():
    """The double-counting case: the original was a NOTICE, so no original survives."""
    got = chosen(filings(
        ("notice", "13F-HR", "", "13F NOTICE", "2010-04-10"),
        ("am1", "13F-HR/A", "", "13F HOLDINGS REPORT", "2010-05-10"),
        ("am2", "13F-HR/A", "", "13F HOLDINGS REPORT", "2010-05-20")))
    assert got == ["am2"], f"both amendments kept = holdings counted twice; got {got}"


def test_explicit_new_holdings_with_no_original_still_stack():
    """Genuinely additive amendments must not be collapsed."""
    got = chosen(filings(
        ("notice", "13F-HR", "", "13F NOTICE", "2010-04-10"),
        ("am1", "13F-HR/A", "NEW HOLDINGS", "13F HOLDINGS REPORT", "2010-05-10"),
        ("am2", "13F-HR/A", "NEW HOLDINGS", "13F HOLDINGS REPORT", "2010-05-20")))
    assert got == ["am1", "am2"]


def test_two_originals_keeps_the_later_one():
    assert chosen(filings(
        ("o1", "13F-HR", "", "13F HOLDINGS REPORT", "2010-04-10"),
        ("o2", "13F-HR", "", "13F HOLDINGS REPORT", "2010-04-20"))) == ["o2"]


def test_notice_alone_selects_nothing():
    assert chosen(filings(("notice", "13F-HR", "", "13F NOTICE", "2010-04-10"))) == []


# ---- decision 12 grain and plausibility guards

def test_write_output_refuses_a_double_counted_grain(tmp_path, monkeypatch):
    """The stated grain is one row per manager x security. Publishing a duplicate would double
    count holdings, which is what 9,886 rows across 10 quarters did before 2026-10-18."""
    import numpy as np
    import pytest

    from pipeline import ownership

    monkeypatch.chdir(tmp_path)
    row = {c: "" for c in ownership.OUTPUT_COLUMNS}
    row.update({"cusip": "002824100", "manager_cik": 2230, "shares_held": 100,
                "company_cik": 1800, "shares_outstanding": 1_000_000})
    mc = pd.DataFrame([row, row])          # the same manager reporting the same security twice
    with pytest.raises(ValueError, match="double counts holdings"):
        ownership.write_output(mc, "unit_test")


def test_plausibility_thresholds_bracket_real_companies():
    """A US listed company with 13F holders sits inside the gate; the XBRL unit errors do not."""
    from pipeline.ownership import MAX_SHARES_OUT, MIN_SHARES_OUT

    assert MIN_SHARES_OUT <= 976_414            # Berkshire class A, the smallest real count seen
    assert 8_432_767_307 <= MAX_SHARES_OUT      # Microsoft 2011Q1, the largest real count seen
    assert not (MIN_SHARES_OUT <= 1 <= MAX_SHARES_OUT), "CSX was published with 1 share outstanding"
    assert not (MIN_SHARES_OUT <= 660_578_698_000_000 <= MAX_SHARES_OUT), "Exelon, 660tn shares"


def test_derivative_cusips_are_identified_by_issue_number_nine():
    """Issue number 9 marks a derivative line. 172967903 (Citigroup) passed every old filter."""
    for cusip in ("172967903", "81369Y902", "ZZZ99V928"):
        assert cusip[6] == "9", f"{cusip} should be caught by the position-7 rule"
    for cusip in ("002824100", "00206R102", "594918104"):
        assert cusip[6] != "9", f"{cusip} is an ordinary equity line and must not be excluded"


def test_ownership_ceiling_sits_above_lending_and_below_the_unit_errors():
    """Measured over 67,672 company-quarters: p99 = 118%, p99.5 = 147%, p99.9 = 395%.
    Securities lending double-reports a holding; it does not produce 300%+. The suppressed cases
    are denominators tagged in thousands (Simon Property 8,000 shares, Abercrombie 87,846)."""
    from pipeline.ownership import MAX_OWNERSHIP_PCT

    assert MAX_OWNERSHIP_PCT >= 200, "must not suppress plausible securities-lending cases"
    assert MAX_OWNERSHIP_PCT <= 1000, "must still catch the thousands-scale denominators"
    assert 147 < MAX_OWNERSHIP_PCT, "p99.5 of the real distribution must survive the ceiling"


# ---- cases found by verification on 2026-10-19, each of which shipped wrong data

def test_parenthesis_checkbox_and_singular_holding_are_read():
    """BNY Mellon 2011Q1, accession 0001390777-11-000128: the cover page reads
    "( X ) adds new holding" - parentheses, and "holding" singular. The first version of the
    regex accepted only "[X] adds new holdings", so this amendment defaulted to RESTATEMENT and
    replaced BNY Mellon's entire 20,336-row book with a single row."""
    (path,) = glob.glob(str(FIX / "text_amendment_paren_checkbox_singular_2011__*.txt.gz"))
    raw = gzip.open(path).read().decode("utf-8", "replace")
    p = parse_submission(raw)
    assert p.amendment_type == "NEW HOLDINGS", f"got {p.amendment_type!r}"


def mc_rows(*rows):
    """rows: (manager_cik, cusip, shares_held, accession, filed_date)"""
    return pd.DataFrame([{"manager_cik": m, "cusip": c, "shares_held": sh, "accession": a,
                          "filed_date": fd, "n_rows": 1} for m, c, sh, a, fd in rows])


def test_a_restated_holding_is_replaced_not_added():
    """The Aristotle Capital 2014Q4 failure: the filer labelled a full restatement NEW HOLDINGS,
    the original and the amendment both reported the security, and the two were summed. Published
    376m shares against a corrected book of 194m."""
    from pipeline.ownership import collapse_to_grain

    out, n = collapse_to_grain(mc_rows(
        (1, "037833100", 182_419_878, "orig", "2015-02-13"),
        (1, "037833100", 193_718_101, "amend", "2015-03-20"),
    ))
    assert len(out) == 1
    assert out.iloc[0]["shares_held"] == 193_718_101, "the later report must win, not the sum"
    assert out.iloc[0]["shares_held"] != 182_419_878 + 193_718_101
    assert out.iloc[0]["n_source_filings"] == 2
    assert n == 2


def test_a_genuinely_additive_amendment_still_adds_its_own_securities():
    from pipeline.ownership import collapse_to_grain

    out, _ = collapse_to_grain(mc_rows(
        (1, "037833100", 100, "orig", "2015-02-13"),
        (1, "02079K305", 200, "amend", "2015-03-20"),      # a security only in the amendment
    ))
    assert len(out) == 2
    assert set(out["shares_held"]) == {100, 200}


def test_exact_duplicate_filings_do_not_double_count():
    from pipeline.ownership import collapse_to_grain

    out, _ = collapse_to_grain(mc_rows(
        (1, "003009107", 1_862_160, "a", "2010-10-20"),
        (1, "003009107", 1_862_160, "b", "2010-10-21"),     # byte-identical refiling
    ))
    assert len(out) == 1 and out.iloc[0]["shares_held"] == 1_862_160
