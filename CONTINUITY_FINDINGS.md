# Cross-quarter continuity of the denominator — built 2026-10-21

Branch `worktree-shares-out-continuity`, off 7a91f4b. This was the top open item in STATUS.md:
"Cross-quarter continuity is the structurally better fix and is not built. A per-quarter rule
cannot tell a units error from a corporate action; a company's share count across 20 quarters can."

Every number here comes from a file the code wrote. Re-run with:

    python3 -m pipeline.continuity        # about 50 seconds, no network
    python3 -m pipeline.validate --all    # 293 checks (286 before, 7 new)
    python3 -m pytest tests -q            # 97 tests (81 before, 16 new)

## What was built

- `pipeline/continuity.py`. Builds a panel of the denominator pool ownership.py actually publishes
  from (XBRL plus the approved 10-K regex fallback): 168,118 company-quarter-class observations on
  18,508 series across the 20 quarters. Labels every observation against its own company's history
  and proposes a repair only where a power of ten reconciles it.
- `tests/test_continuity.py`, 16 tests. Each one is a real case from this data, and each asserts
  both that the rule fires on the broken series and that it does NOT fire on the legitimate series
  it most resembles (a 7-for-1 split, a 1-for-5 reverse split, a 1-for-10 reverse split).
- 7 new properties in `pipeline/validate.py`, scoped `continuity`. Skipped, not failed, when the
  continuity report has not been run, because the report is a diagnostic and not a deliverable.
- Reports: `output/problems/continuity_shares_out.txt`, `continuity_shares_out.csv` (5,851 flagged
  rows), `continuity_published_over_100.csv` (133 rows), `continuity_metrics.json`.
- Nothing is merged into the published numbers. `pipeline/ownership.py` is untouched, the 20
  quarter files are untouched, and `validate --all` still passes with 0 failures.

## What it labels

| label | observations | meaning |
|---|---|---|
| ok | 158,834 (94.5%) | within 5x of the company's own local level |
| level_shift | 3,239 | the level moved and the series KEPT it: a split, buyback or issuance. Never repaired |
| no_usable_level | 2,798 | no possible value anywhere in the series, so there is no level to be continuous with |
| unexplained | 1,865 | a break no power of ten explains. Reported for a human, never repaired |
| implausible_scale | 356 | impossible value, and a power of ten puts it on the company's own level |
| isolated_scale | 391 | possible value, but the quarters either side disagree by >5x and a power of ten reconciles it |
| no_history | 635 | one quarter only |

747 repairs are proposed on 427 companies. 356 of those are denominators the current build already
drops as implausible, so repairing them would turn missing figures into figures rather than change
any published number.

## The two findings that matter

**1. 133 published figures above 100% rest on a denominator smaller than another share class of
the same company.** 60 companies, 100% to 296%, mostly dual-class names: Urstadt Biddle (15
quarters), Heico (9), Central Garden & Pet (9), Iconix (8), Rent-A-Center (6), Triple-S (4).
Central Garden & Pet 2013Q2 is the clearest: published 296.1% from holdings of 36,257,911 against
a denominator of 12,246,751, while the company's own panel carries a 35,321,862 Class A series in
the same quarter. Holdings span both classes; the denominator is one class. The true figure is
near 76%.

This is decision 13 (share classes summed at company level) with a measured size. The 300% ceiling
suppresses the extreme tail of this problem, 91 company-quarters, and publishes the rest. The test
used here is deliberately the weakest defensible one — a single class of the same company is
materially larger than the denominator used — because summing class series double counts: Central
Garden & Pet's common stock appears three times in the panel (undimensioned, `CommonStock`,
`CommonClassOne`), all at about 12.2m.

**2. 92 published figures have a denominator their own history contradicts by 100x or more**, with
at least 3 possible quarters behind the judgment. These are a different population from finding 1
and mostly 2010-2011, where XBRL coverage was phasing in.

Also added: a `shift_x` column saying how the level itself moved across each quarter. That is what
an over-100% cause label needs in order to be diagnosed rather than assumed — Chimera Investment
2014Q4 steps to 0.2x on a 1-for-5 reverse split while the holdings filed against it are pre-split,
and the current cause label says `multi_cusip_classes_summed`, which is not what happened.

## Two bugs the tests found in my own rule

Both are the pattern already recorded in STATUS.md: a rule about messy data whose assumption was
stated in a comment and never tested in both directions.

1. The repair threshold compared the raw factor against 100x. A value tagged in thousands has a
   factor of 0.001, so it failed the test and only the too-LARGE direction was ever repaired — the
   Apple 2014Q1 case the module was written for came out "unexplained". Repairs went 213 to 551
   when fixed. `validate` now asserts both directions are represented.
2. A break in the first or last quarter of a series was always called unexplained, because the rule
   needed two sides. Every 2010 quarter and every company's final quarter is an edge. A one-sided
   break is now repairable on the same terms, which took repairs from 551 to 747; the 100x floor
   still keeps a 1-for-10 reverse split in a final quarter out of it.

## What is NOT done

- No repair is merged into the denominator. That is a decision, and it changes published numbers.
- The 1,865 unexplained breaks are not diagnosed one by one. The large ones are wholly-owned
  subsidiary registrants reporting 1,000 shares held by a parent, which is a mapping question
  (the 13F holdings belong to the listed parent), not a scale question.
- `continuity_metrics.json` is not yet part of the build-over-build regression baseline, so a
  future change that quietly stops labelling things would pass. Next step if this is kept.

## In plain terms

I built the check STATUS.md called the highest-value remaining work: instead of judging a share
count one quarter at a time, it reads each company's own 20 quarters and asks whether a number fits
its own history. It found 133 published ownership figures between 100% and 296% that are wrong for
a known reason — the denominator is one share class while the holdings cover two — and 92 more
whose denominator its own history contradicts outright. It also found two bugs in my own new rule
before any of it touched the deliverable. Nothing published has been changed, and all 293 checks
and 97 tests pass. The decision for you: whether to repair those denominators and republish, or
document them. My recommendation is to publish both views of the share-class figure, which is also
what decision 13 was waiting on, and to leave the rest reported.

---

## Outcome, 2026-10-21: the finding was acted on, not just documented

Finding 1 (133 published figures whose denominator covered one share class while the numerator
summed two) is fixed at the source, as **decision 15** in `pipeline/ownership.py`. The spec requires
it: "do not assume one company = one CUSIP; handle multiple share classes."
`ownership.company_denominator()` now decides the denominator from the classes actually held, read
from the SEC's 13(f) list description, and records the basis on every row in `denominator_basis`.
Two further rules came out of chasing the rest of the distribution: warrants, dated SPAC units and
preferred leave the numerator (decision 15b), and a company total smaller than the single class
being held cannot be a total (Triple-S Management).

All 20 quarters were rebuilt. Published figures went 67,462 to 69,984, denominator coverage by 13F
value in 2013Q4 went 89.4% to 93.9%, and 4,779 company-quarter figures changed. `validate --all` is
293 checks with 0 failures and the suite is 117 tests.

What this exercise is worth remembering for:

- The continuity check found a defect that four independent reviews of a single quarter had not,
  because it compares a company against itself across time rather than against a threshold.
- Its own tests found two one-directional bugs in it before it was merged.
- The validator then found two more in decision 15 after it was merged but before anything was
  published: class counts bypassed the plausibility range, and the impossible-holding rule was
  still being tested against the company count rather than the class-scoped denominator actually
  published. Both are now properties, so neither can come back quietly.
- One of my own rules was wrong in a way no test would have caught, because it was a definition
  rather than a bug: preferring a class count whenever one existed would have restated Nike as 84.4%
  of its Class B instead of 67.6% of all its shares, for 178 companies a quarter. Checking the
  *direction* of the change on a company I could reason about independently is what caught it.

Finding 2 (92 published figures whose denominator its own history contradicts by 100x) is unchanged
and still a diagnostic. Decision 14, whether to merge the 747 proposed repairs, is still open.

### In plain terms

The check I built overnight found 133 wrong ownership percentages; today they are fixed in the
pipeline, not just written up, and the dataset now publishes 2,522 more figures than it did
yesterday with better coverage of the money. The gate caught two mistakes of mine along the way and
one I caught by sanity-checking a company I know. Nothing is published that fails a property.
