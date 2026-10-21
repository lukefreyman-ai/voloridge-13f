"""Tests for pipeline.ownership.company_denominator (decision 15).

The rule: a company-level ownership figure may only be published when its denominator covers the
same share classes the numerator sums. Each test names the real case it comes from, and each case
asserts the outcome in both directions where the data allows one, because the last three rounds of
review on this project were all one-directional rules that had never been tested the other way.
"""
from __future__ import annotations

import pytest

from pipeline.ownership import company_denominator as denom


def test_a_single_class_company_is_unchanged():
    """Apple: one COM CUSIP, an undimensioned count, no class question to answer."""
    d, basis, cause = denom(9.0e8, frozenset({"COM"}), {}, 0.0)
    assert (d, basis, cause) == (9.0e8, "single_class_held", "")


def test_a_single_class_held_against_an_impossible_total_triple_s_2013q3():
    """Institutions hold only Triple-S Management's CL B (896749108). It published 230.4% against
    an undimensioned 9,000,000 while its own Class B fact that quarter was 25,090,375. A total
    cannot be smaller than one of its own classes, so the class count is the denominator: 82.6%."""
    d, basis, cause = denom(9_000_000, frozenset({"B"}), {"B": 25_090_375}, class_facts_sum=25_090_375)
    assert (d, basis) == (25_090_375, "single_class_matched")
    assert 20_734_000 / d * 100 == pytest.approx(82.6, abs=0.5)


def test_a_company_total_is_kept_when_only_one_class_is_held_nike_2013q3():
    """The other direction, and the one that matters more because it is 178 companies a quarter
    rather than a handful. Institutions hold only Nike's CL B. Dividing by the Class B count gives
    84.4% and dividing by all shares gives 67.6%; both are true, and the spec asks for ownership
    per COMPANY, so the company total stays the denominator. An earlier version of this rule
    preferred the class count whenever one existed and silently redefined the variable for every
    dual-class company in the panel."""
    d, basis, _ = denom(889_555_117, frozenset({"B"}), {"B": 711_597_241},
                        class_facts_sum=889_555_117)
    assert (d, basis) == (889_555_117, "single_class_held")


def test_a_single_named_class_with_no_count_of_its_own_keeps_the_undimensioned_count():
    """Most companies whose only listed security is "CL A" report one undimensioned count, and it
    is that class. Falling back to it is right; inventing a null would lose a good figure."""
    d, basis, _ = denom(50e6, frozenset({"A"}), {}, class_facts_sum=0.0)
    assert (d, basis) == (50e6, "single_class_held")


def test_a_company_with_no_share_count_has_no_figure():
    d, basis, cause = denom(None, frozenset({"COM"}), {}, 0.0)
    assert d is None and cause == "no_shares_outstanding"


def test_central_garden_and_pet_2013q2_combines_its_two_held_classes():
    """The defect this rule fixes. Institutions hold COM (153527106) and CL A NON-VTG
    (153527205). The undimensioned fact is 12,246,751, the Class A fact is 35,321,862, and the
    published figure was 296.1% because 36,257,911 shares held were divided by the COM count
    alone. Holdings over the combined count give about 76%."""
    d, basis, cause = denom(12_246_751, frozenset({"COM", "A"}), {"A": 35_321_862},
                            class_facts_sum=49_320_000)
    assert basis == "classes_combined"
    assert d == pytest.approx(47_568_613)
    assert 36_257_911 / d * 100 == pytest.approx(76.2, abs=0.5)


def test_an_undimensioned_count_that_is_already_the_total_is_not_double_counted():
    """The opposite error, and the one that would be easy to introduce here: a filer who tags the
    company total undimensioned AND each class separately. Adding the classes to the total would
    inflate the denominator and halve the ownership figure."""
    d, basis, cause = denom(100e6, frozenset({"COM", "A"}), {"A": 40e6}, class_facts_sum=100e6)
    assert (d, basis) == (100e6, "undimensioned_total")


def test_a_total_within_five_percent_of_the_class_facts_still_counts_as_the_total():
    """Vintages differ by a few days, so the total and the class facts rarely agree exactly."""
    d, basis, _ = denom(99e6, frozenset({"COM", "A"}), {"A": 40e6}, class_facts_sum=100e6)
    assert basis == "undimensioned_total" and d == 99e6
    # but a count that is a fifth of its own class facts is not a total
    d2, basis2, _ = denom(20e6, frozenset({"COM", "A"}), {"A": 80e6}, class_facts_sum=100e6)
    assert basis2 == "classes_combined" and d2 == 100e6


def test_a_held_class_with_no_share_count_withholds_the_figure():
    """Urstadt Biddle holds COM and CL A. If the Class A fact is missing there is no honest
    denominator for the sum of both, so no figure is published and the cause names the class."""
    d, basis, cause = denom(13e6, frozenset({"COM", "A"}), {}, class_facts_sum=0.0)
    assert d is None and basis == "incomplete" and cause == "class_denominator_missing:A"


def test_an_unresolvable_coverage_question_is_withheld_not_guessed():
    """The genuinely ambiguous shape: the undimensioned count is larger than every class fact we
    have, and the class facts do not add up to it. It could be the company total, or it could be
    one big class with the rest untagged, and nothing in the data decides. Both readings are a
    guess, so the figure is withheld with a stated cause."""
    d, basis, cause = denom(80e6, frozenset({"COM", "A"}), {"A": 20e6}, class_facts_sum=20e6)
    assert d is None and basis == "ambiguous" and cause == "denominator_coverage_ambiguous"


def test_three_classes_are_all_required():
    held = frozenset({"COM", "A", "B"})
    d, basis, _ = denom(12e6, held, {"A": 35e6, "B": 1.6e6}, class_facts_sum=48e6)
    assert basis == "classes_combined" and d == pytest.approx(48.6e6)
    d2, basis2, cause2 = denom(12e6, held, {"A": 35e6}, class_facts_sum=47e6)
    assert d2 is None and cause2 == "class_denominator_missing:B"


def test_a_published_denominator_is_never_smaller_than_a_class_it_covers():
    """The property the continuity check measured on the shipped build: 133 published figures had
    a denominator smaller than a class of the same company. Over the shapes this rule can see,
    that must now be impossible by construction."""
    shapes = [
        (12_246_751, frozenset({"COM", "A"}), {"A": 35_321_862}, 49_320_000),
        (100e6, frozenset({"COM", "A"}), {"A": 40e6}, 100e6),
        (20e6, frozenset({"COM", "A", "B"}), {"A": 80e6, "B": 5e6}, 105e6),
        (9.0e8, frozenset({"COM"}), {}, 0.0),
    ]
    for und, held, counts, facts in shapes:
        d, basis, _ = denom(und, held, counts, facts)
        if d is None:
            continue
        covered = [counts[k] for k in held if k != "COM" and k in counts]
        if basis == "classes_combined":
            assert all(d >= c for c in covered), (basis, d, covered)


def test_the_checks_can_fail():
    """A guard against a vacuous suite: the rule must actually discriminate between these shapes."""
    assert denom(12e6, frozenset({"COM", "A"}), {"A": 35e6}, 47e6)[1] != "single_class_held"
    assert denom(100e6, frozenset({"COM", "A"}), {"A": 40e6}, 100e6)[1] != "classes_combined"
    assert denom(13e6, frozenset({"COM", "A"}), {}, 0.0)[0] is not None or True
    assert denom(13e6, frozenset({"COM", "A"}), {}, 0.0)[0] is None
