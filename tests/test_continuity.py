"""Tests for pipeline/continuity.py.

Two things every test here does. It uses a REAL case from this project's data, named in the test,
so the rule is pinned to something that actually happened. And it asserts both directions: that
the rule fires on the broken series AND that it does not fire on the legitimate one it most
resembles. The project's own history is the reason - of the six denominator fixes reviewed on
2026-10-19, three were wrong, and four of the five defects were rules that had only ever been
checked in the direction their author had in mind.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pipeline import continuity as ct

QUARTERS = pd.period_range("2010Q1", "2014Q4", freq="Q").to_timestamp(how="end").normalize()


def series(values, cik=1, class_axis="", name="TEST CO"):
    """A panel of one series, one value per quarter from 2010Q1."""
    n = len(values)
    return pd.DataFrame({
        "cik": cik, "name": name, "class_axis": class_axis,
        "shares": [float(v) for v in values],
        "label": [f"{q.year}Q{q.quarter}" for q in QUARTERS[:n]],
        "quarter_end": QUARTERS[:n],
        "shares_outstanding_source": "10-Q 0000000000-00-000000 CommonStockSharesOutstanding",
        "shares_outstanding_date": "2013-12-31", "tag": "CommonStockSharesOutstanding",
        "scale_corrected": False,
    })


def labels_of(df):
    return list(ct.classify(df)["continuity_label"])


# --------------------------------------------------------------------------- the quiet case

def test_a_flat_series_is_all_ok():
    """Oracle 2010Q1-2014Q4: ~5.0e9 drifting down to 4.37e9 over 20 quarters, no break anywhere."""
    vals = np.linspace(5.026e9, 4.373e9, 20)
    assert set(labels_of(series(vals))) == {"ok"}


def test_a_single_quarter_series_is_not_judged():
    """One observation cannot be continuous or discontinuous with anything."""
    assert labels_of(series([1.2e8])) == ["no_history"]


# ------------------------------------------------------- scale errors, in BOTH directions

def test_thousands_tagging_is_caught_and_repaired_apple_2014q1():
    """Apple 2014Q1 carried CommonStockSharesOutstanding = 861,745 against a real 861,381,000.
    The value is 1,000x too SMALL. An earlier version of this rule compared the raw factor
    (0.001) against the 100x threshold and so repaired only the too-LARGE direction, which left
    this case - the case the module was written for - labelled unexplained."""
    vals = [9.0e8] * 8 + [861_745.0] + [9.0e8] * 8
    c = ct.classify(series(vals))
    row = c.iloc[8]
    assert row["continuity_label"] == "isolated_scale"
    assert row["shares_repaired"] == pytest.approx(861_745_000.0)
    assert set(c["continuity_label"]) == {"ok", "isolated_scale"}


def test_millions_tagging_is_caught_stryker():
    """Stryker 2010Q1-2011Q2 carries ~380 shares (the fact is tagged in millions) against a real
    ~3.9e8. Below MIN_SHARES_OUT, so it is impossible on its own as well as against the series."""
    vals = [380.5] * 6 + [3.9e8] * 10
    c = ct.classify(series(vals))
    assert set(c["continuity_label"].iloc[:6]) == {"implausible_scale"}
    assert c["shares_repaired"].iloc[0] == pytest.approx(3.805e8)
    assert set(c["continuity_label"].iloc[6:]) == {"ok"}


def test_a_value_a_million_times_too_large_is_caught_pge_2014q4():
    """PG&E 2014Q4 carried 4.759e14 against a real ~4.47e8: above MAX_SHARES_OUT."""
    vals = [4.46e8] * 10 + [4.759e14]
    c = ct.classify(series(vals))
    assert c["continuity_label"].iloc[-1] == "implausible_scale"
    assert c["shares_repaired"].iloc[-1] == pytest.approx(4.759e8)


def test_a_repair_is_never_outside_the_possible_range():
    """Oracle 2012Q2 shipped 4.819e15 once because a cross-check took the larger of two facts
    unconditionally. A repair that lands outside [MIN, MAX] is not a repair."""
    vals = [4.9e9] * 8 + [4.819e15] + [4.9e9] * 8
    c = ct.classify(series(vals))
    rep = c["shares_repaired"].dropna()
    assert ((rep >= ct.MIN_SHARES_OUT) & (rep <= ct.MAX_SHARES_OUT)).all()


# ------------------------------------------------- corporate actions must NOT be repaired

def test_a_seven_for_one_split_is_a_level_shift_not_an_error_apple_2014q2():
    """Apple split 7-for-1 in June 2014: 861m -> 5.99bn, and the series KEEPS the new level."""
    vals = [9.0e8] * 16 + [5.989e9] * 3
    c = ct.classify(series(vals))
    assert c["continuity_label"].iloc[16] == "level_shift"
    assert c["shares_repaired"].isna().all()


def test_a_one_for_five_reverse_split_is_not_repaired_chimera_2014q4():
    """Chimera Investment's 1-for-5 reverse split: 1.0276e9 -> 2.055e8. Exactly at the 5x break
    threshold, and a power of ten does not explain it, so nothing may be corrected."""
    vals = [1.0276e9] * 16 + [2.055e8] * 4
    c = ct.classify(series(vals))
    assert c["shares_repaired"].isna().all()
    assert "isolated_scale" not in set(c["continuity_label"])


def test_a_ten_for_one_reverse_split_is_not_repaired_even_though_ten_is_a_power_of_ten():
    """The hardest case for this module, and the reason MIN_REPAIR_FACTOR is 100 and not 10: a
    1-for-10 reverse split IS a power of ten. Magnitude cannot tell it from a tagging error, so
    only the series' own behaviour can: the new level is kept, so it is a corporate action."""
    vals = [5.0e8] * 10 + [5.0e7] * 10
    c = ct.classify(series(vals))
    assert c["shares_repaired"].isna().all()
    assert c["continuity_label"].iloc[10] == "level_shift"


# ------------------------------------------- the level must be built from possible values only

def test_the_level_ignores_impossible_neighbours_phoenix_companies():
    """The Phoenix Companies carries ~116 shares in most quarters and 116,300,000 in 2011Q3. With
    every neighbour allowed to form the level, the level came out at 116 and the one CORRECT
    quarter was flagged as the break - the rule pointing at the wrong row."""
    vals = [116.0] * 8 + [116_300_000.0] * 3 + [116.0] * 6
    c = ct.classify(series(vals))
    assert set(c["continuity_label"].iloc[8:11]) == {"ok"}
    assert c["level"].iloc[8] > 1e6                      # the level is not 116
    assert set(c["continuity_label"].iloc[:8]) == {"implausible_scale"}
    assert c["shares_repaired"].iloc[0] == pytest.approx(1.16e8)


def test_a_series_with_no_possible_value_anywhere_is_not_judged():
    """A wholly-owned subsidiary registrant reports 1,000 shares held by its parent in every
    quarter. There is no level to be continuous with, and saying "unexplained" would imply the
    data contradicts itself when it does not."""
    c = ct.classify(series([200.0] * 8))
    assert set(c["continuity_label"]) == {"no_usable_level"}


# ----------------------------------------------------------------- the confidence requirement

def test_a_repair_needs_enough_history_behind_it():
    """The 2010 quarters are the reason: XBRL coverage was phasing in, so a series can have one
    usable neighbour. Two observations that are both wrong the same way must not license a repair."""
    thin = ct.classify(series([861_745.0, 9.0e8]))
    assert thin["shares_repaired"].isna().all()
    thick = ct.classify(series([861_745.0] + [9.0e8] * 4))
    assert thick["shares_repaired"].notna().any()


def test_level_confidence_counts_only_possible_quarters():
    c = ct.classify(series([380.5] * 4 + [3.9e8] * 4))
    # the four impossible quarters are not evidence for anything
    assert c["level_confidence"].iloc[0] == 4
    assert (c["level_confidence"] <= 2 * ct.NEIGHBOURS).all()


# --------------------------------------------------------------------- series are independent

def test_classes_of_one_company_are_separate_series_central_garden_and_pet():
    """Central Garden & Pet's common (~12.2m) and Class A (~35.4m) are different series. Treating
    a company as one series would make the smaller class look like a break against the larger."""
    a = series([12.25e6] * 12, cik=887733, class_axis="")
    b = series([35.4e6] * 12, cik=887733, class_axis="ClassOfStock=CommonClassA;")
    c = ct.classify(pd.concat([a, b], ignore_index=True)
                    .sort_values(["cik", "class_axis", "quarter_end"]).reset_index(drop=True))
    assert set(c["continuity_label"]) == {"ok"}


def test_the_shift_column_reports_how_the_level_moved():
    """shift_x is what the over-100% diagnosis needs: Chimera's denominator steps to 0.2x on its
    reverse split while the holdings filed against it are pre-split."""
    c = ct.classify(series([1.0276e9] * 10 + [2.055e8] * 10))
    assert c["shift_x"].iloc[10] == pytest.approx(0.2, rel=0.01)


# ------------------------------------------------------- every check above can actually fail

def test_the_checks_can_fail():
    """Guard against a vacuous suite: each assertion above must be able to come out the other way.
    If classify() stopped labelling anything, every test above would still pass except these."""
    assert ct.classify(series([9.0e8] * 8 + [861_745.0] + [9.0e8] * 8))["continuity_label"].iloc[8] != "ok"
    assert ct.classify(series([380.5] * 6 + [3.9e8] * 10))["shares_repaired"].notna().any()
    assert ct.classify(series([5.0e8] * 10 + [5.0e7] * 10))["continuity_label"].iloc[10] != "ok"
    assert ct.classify(series(np.linspace(5.026e9, 4.373e9, 20)))["shares_repaired"].isna().all()
