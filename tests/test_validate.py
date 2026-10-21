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


# --------------------------------------------------------------------------------------------
# The continuity checks (pipeline/validate.check_continuity, added 2026-10-21) must fail too.
# Each case below injects a defect that the continuity rule could plausibly develop, and the
# first one actually did: the repair threshold compared the raw factor against 100x, so the
# too-small direction was never repaired and the check that both directions are represented is
# the one that would have caught it.

def _continuity_files(tmp_path, rows, metrics=None):
    import json
    import os
    os.chdir(tmp_path)
    (tmp_path / "output/problems").mkdir(parents=True, exist_ok=True)
    (tmp_path / "cache/parsed").mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet("cache/parsed/shares_out_continuity.parquet", index=False)
    met = {"quarters": 20}
    met.update(metrics or {})
    json.dump(met, open("output/problems/continuity_metrics.json", "w"))
    pd.DataFrame([{"quarter_end": "2013-12-31", "company_cik": 1800}]).to_csv(
        "output/company_ownership_by_quarter.csv", index=False)
    from pipeline.validate import Result, check_continuity
    r = Result()
    check_continuity(r)
    return {name: ok for _, name, ok, _ in r.rows}


def _row(**kw):
    base = dict(cik=1800, continuity_label="isolated_scale", scale_factor=1000.0,
                shares_repaired=9.0e8, level_confidence=6)
    base.update(kw)
    return base


def test_continuity_clean_input_passes(tmp_path):
    res = _continuity_files(tmp_path, [_row(), _row(scale_factor=0.001, shares_repaired=8.6e8)])
    assert all(res.values()), [k for k, v in res.items() if not v]


def test_continuity_catches_a_repair_outside_the_possible_range(tmp_path):
    res = _continuity_files(tmp_path, [_row(shares_repaired=4.8e15),
                                       _row(scale_factor=0.001, shares_repaired=8.6e8)])
    assert any("every proposed denominator" in k and not v for k, v in res.items())


def test_continuity_catches_a_repaired_corporate_action(tmp_path):
    res = _continuity_files(tmp_path, [_row(continuity_label="level_shift"),
                                       _row(scale_factor=0.001, shares_repaired=8.6e8)])
    assert any("level shift" in k and not v for k, v in res.items())


def test_continuity_catches_a_correction_below_the_threshold(tmp_path):
    res = _continuity_files(tmp_path, [_row(scale_factor=10.0),
                                       _row(scale_factor=0.001, shares_repaired=8.6e8)])
    assert any("at least 100x" in k and not v for k, v in res.items())


def test_continuity_catches_a_one_directional_repair_rule(tmp_path):
    """The defect that shipped: every repair in the same direction means the rule only looks one
    way. Two 1,000x-too-large repairs and not one too-small is the signature."""
    res = _continuity_files(tmp_path, [_row(), _row()])
    assert any("both directions" in k and not v for k, v in res.items())


def test_continuity_catches_a_repair_with_no_history_behind_it(tmp_path):
    res = _continuity_files(tmp_path, [_row(level_confidence=1),
                                       _row(scale_factor=0.001, shares_repaired=8.6e8)])
    assert any("quarters of history" in k and not v for k, v in res.items())


def test_continuity_catches_a_panel_that_does_not_cover_the_quarters(tmp_path):
    res = _continuity_files(tmp_path, [_row(), _row(scale_factor=0.001, shares_repaired=8.6e8)],
                            metrics={"quarters": 12})
    assert any("covers 20 quarters" in k and not v for k, v in res.items())
