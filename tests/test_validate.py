"""The validator must be able to FAIL. A check that cannot fail is decoration.

Each case below injects a defect that actually shipped in this project at least once, and asserts
that pipeline.validate catches it. Written 2026-10-19 after the validator passed 246 checks on its
first run, which is not by itself evidence that it works.

Run: python3 -m pytest tests -q
"""
import pandas as pd
import pytest

from pipeline.validate import Result, check_quarter

GOOD = {
    "quarter_end": "2013-12-31", "company_name": "ABBOTT LABORATORIES", "company_cik": "1800",
    "cusip": "002824100", "manager_cik": "2230", "manager_name": "ADAMS EXPRESS CO",
    "shares_held": "87050", "shares_outstanding": "1557000000",
    "institutional_ownership_pct": "54.0978",
    "form_13f_accession_number": "0000002230-14-000003",
    "shares_outstanding_source": "10-K 0000001800-14-000008 CommonStockSharesOutstanding",
    "shares_outstanding_date": "2013-12-31",
}
EXTRA = ["shares_outstanding_evidence", "cusip_issuer", "map_source", "list_desc",
         "excluded_from_ownership", "class_shares_outstanding", "class_ownership_pct",
         "class_match", "multi_class_flag", "map_conflict", "map_conflict_two_sided",
         "multi_filing_flag", "dup_amendment_flag", "debt_cusip_flag", "adr_flag",
         "over_100_flag", "over_100_cause", "n_rows", "pct_suppressed_cause"]


def write(tmp_path, *rows):
    import os
    os.chdir(tmp_path)
    (tmp_path / "output").mkdir(exist_ok=True)
    df = pd.DataFrame(rows)
    for c in EXTRA:
        df[c] = ""
    df.to_csv(tmp_path / "output/unit_institutional_ownership.csv", index=False)
    r = Result()
    check_quarter("unit", r)
    return {name: ok for _, name, ok, _ in r.rows}


def test_a_clean_file_passes_every_check(tmp_path):
    res = write(tmp_path, GOOD)
    assert all(res.values()), [k for k, v in res.items() if not v]


def test_duplicate_grain_is_caught(tmp_path):
    """9,886 duplicate holdings shipped before 2026-10-18."""
    res = write(tmp_path, GOOD, dict(GOOD))
    assert res["grain unique (quarter, cusip, manager)"] is False


def test_an_impossible_denominator_is_caught(tmp_path):
    """CSX shipped with shares_outstanding = 1, giving 25,208,955,300% ownership."""
    res = write(tmp_path, {**GOOD, "shares_outstanding": "1"})
    assert res[f"shares_outstanding in [1,000, 35,000,000,000]"] is False


def test_a_denominator_a_thousand_times_too_large_is_caught(tmp_path):
    """Pentair shipped 98,419,310,000 shares against a real ~98 million."""
    res = write(tmp_path, {**GOOD, "shares_outstanding": "98419310000"})
    assert res["shares_outstanding in [1,000, 35,000,000,000]"] is False


def test_ownership_above_the_ceiling_is_caught(tmp_path):
    res = write(tmp_path, {**GOOD, "institutional_ownership_pct": "7248.7"})
    assert res["ownership <= 300%"] is False


def test_a_float_formatted_identifier_is_caught(tmp_path):
    """13,566,025 rows shipped with company_cik as '732717.0', breaking every join."""
    res = write(tmp_path, {**GOOD, "company_cik": "1800.0"})
    assert res["identifiers are integers"] is False


def test_a_malformed_accession_is_caught(tmp_path):
    res = write(tmp_path, {**GOOD, "form_13f_accession_number": "not-an-accession"})
    assert res["accession format"] is False


def test_an_invalid_cusip_check_digit_is_caught(tmp_path):
    res = write(tmp_path, {**GOOD, "cusip": "002824109"})
    assert res["CUSIP check digit"] is False


def test_a_holding_larger_than_the_company_is_caught(tmp_path):
    """Microsoft 2011Q1 shipped one manager reporting 111,580,102,484 shares."""
    res = write(tmp_path, {**GOOD, "shares_held": "9999999999999"})
    assert res["no published holding exceeds shares outstanding"] is False


def test_a_denominator_without_a_source_is_caught(tmp_path):
    res = write(tmp_path, {**GOOD, "shares_outstanding_source": ""})
    assert res["denominator has a source"] is False


def test_spec_column_order_is_enforced(tmp_path):
    import os
    os.chdir(tmp_path)
    (tmp_path / "output").mkdir(exist_ok=True)
    df = pd.DataFrame([GOOD])
    for c in EXTRA:
        df[c] = ""
    df[df.columns[::-1]].to_csv(tmp_path / "output/unit_institutional_ownership.csv", index=False)
    r = Result()
    check_quarter("unit", r)
    res = {name: ok for _, name, ok, _ in r.rows}
    assert res["first 12 columns are the spec columns in order"] is False
