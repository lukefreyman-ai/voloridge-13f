"""Decision 11 (2026-10-18): which XBRL share count becomes the denominator.

The cover-page fact (dei:EntityCommonStockSharesOutstanding) is dated near the filing date, a
median 90 days after the quarter end, which inflates ownership for companies that bought back
stock in the gap. The balance-sheet fact (us-gaap:CommonStockSharesOutstanding) is dated at the
period end. Motivating measurement on real 2013Q4 data:
output/problems/pilot_2013Q4/shares_out_tag_study.txt

Run: python3 -m pytest tests -q
"""
import pandas as pd

from pipeline.shares_out import BALANCE_TAG, COVER_TAG, select

QEND = "2013-12-31"


def facts(*rows):
    """rows: (cik, tag, asof, shares, form, adsh)"""
    df = pd.DataFrame(rows, columns=["cik", "tag", "asof", "shares", "form", "adsh"])
    df["asof"] = pd.to_datetime(df["asof"])
    df["filed"] = df["asof"] + pd.Timedelta(days=5)
    df["class_axis"] = ""
    df["name"] = "TEST CO"
    df["source_set"] = "test"
    return df


def test_prefers_the_quarter_end_balance_sheet_fact_over_a_later_cover_fact():
    f = facts(
        (1, COVER_TAG, "2014-02-14", 90_000_000, "10-K", "a"),    # 45 days late, post-buyback
        (1, BALANCE_TAG, "2013-12-31", 100_000_000, "10-K", "b"),  # dated at the quarter end
    )
    pick = select(f, QEND)
    assert len(pick) == 1
    assert pick.iloc[0]["shares"] == 100_000_000
    assert pick.iloc[0]["tag"] == BALANCE_TAG
    assert pick.iloc[0]["gap_days"] == 0
    assert BALANCE_TAG in pick.iloc[0]["shares_outstanding_source"]


def test_falls_back_to_the_cover_fact_when_no_balance_sheet_fact_exists():
    f = facts((2, COVER_TAG, "2014-02-14", 90_000_000, "10-K", "a"))
    pick = select(f, QEND)
    assert pick.iloc[0]["tag"] == COVER_TAG
    assert pick.iloc[0]["shares"] == 90_000_000


def test_closest_as_of_wins_when_neither_is_at_the_quarter_end():
    f = facts(
        (3, BALANCE_TAG, "2013-06-30", 50_000_000, "10-Q", "a"),   # 184 days early
        (3, COVER_TAG, "2014-01-20", 70_000_000, "10-K", "b"),     # 20 days late, closer
    )
    pick = select(f, QEND)
    assert pick.iloc[0]["shares"] == 70_000_000, "the nearer date should win across tags"


def test_balance_sheet_wins_a_tie_on_distance():
    f = facts(
        (4, COVER_TAG, "2014-01-10", 10_000_000, "10-K", "a"),
        (4, BALANCE_TAG, "2014-01-10", 11_000_000, "10-K", "b"),
    )
    pick = select(f, QEND)
    assert pick.iloc[0]["tag"] == BALANCE_TAG


def test_gap_flag_still_marks_stale_denominators():
    f = facts((5, COVER_TAG, "2014-06-30", 10_000_000, "10-K", "a"))   # 181 days
    pick = select(f, QEND)
    assert bool(pick.iloc[0]["gap_flag"]) is True


def test_share_classes_are_kept_separate():
    f = facts(
        (6, BALANCE_TAG, "2013-12-31", 100, "10-K", "a"),
        (6, BALANCE_TAG, "2013-12-31", 200, "10-K", "b"),
    )
    f.loc[1, "class_axis"] = "StatementClassOfStockAxis=CommonClassBMember"
    pick = select(f, QEND)
    assert len(pick) == 2, "one row per (cik, class), never summed"


def test_a_balance_sheet_fact_tagged_in_thousands_is_corrected_from_the_cover_fact():
    """Apple 2014Q1: balance sheet 861,745 (thousands) vs cover 861,381,000 (units).
    Preferring the balance-sheet fact published Apple at 11,687% institutional ownership."""
    f = facts(
        (320193, BALANCE_TAG, "2014-03-31", 861_745, "10-Q", "a"),
        (320193, COVER_TAG, "2014-03-31", 861_381_000, "10-Q", "b"),
    )
    pick = select(f, "2014-03-31")
    assert pick.iloc[0]["shares"] == 861_381_000, "the thousands-scaled fact must not win"
    assert bool(pick.iloc[0]["scale_corrected"]) is True
    assert "scale-corrected" in pick.iloc[0]["shares_outstanding_source"]


def test_a_normal_difference_between_the_two_tags_is_left_alone():
    """Ordinary buyback-sized differences must not trigger the scale correction."""
    f = facts(
        (1, BALANCE_TAG, "2013-12-31", 100_000_000, "10-K", "a"),
        (1, COVER_TAG, "2014-02-14", 98_000_000, "10-K", "b"),
    )
    pick = select(f, QEND)
    assert pick.iloc[0]["shares"] == 100_000_000
    assert bool(pick.iloc[0]["scale_corrected"]) is False
